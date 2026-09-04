# Gated-commit procedure

Run after reading `harness.md` (and `simplify.md` when the simplify bar fires). Take the current uncommitted working-tree changes through gate → conditional simplify → Sol-first review → dispositions → one commit. Do not push unless the caller says to.

`$ARGUMENTS` describes what the commit is. If empty, derive it from the diff.

## 1. Discover the gate

Read CLAUDE.md, then AGENTS.md, for the per-commit gate (lint / test / build). If neither defines one, derive it from Makefile / package.json / CI and say which commands you chose. Typical shape: `make lint && make test && <frontend build if present>`.

Read CI even when CLAUDE.md defines a gate: grep the workflow for build/test invocations the documented targets don't cover (feature-gated or per-crate/per-package steps especially) and add the ones covering the code you touched. A CI-only feature build caught an exhaustive-match break the whole local gate missed.

## 2. Run the gate

All gate commands must pass before anything else. Fix failures in the diff's own code; do not weaken tests to pass them.

Test-bearing diffs: rebuild before running (a stale binary passes vacuously), and give every new or converted functional test a negative control — break the expectation, watch it fail on that exact line, restore. An assertion never seen red is not evidence.

## 3. Conditional simplify

Run the simplify procedure (read `simplify.md`, execute inline — do not emit `/forge:simplify`) only when its bar fires. Sonnet-class reviewers and fixer; never fable-class. Re-run the relevant gate subset after applied fixes.

## 4. Stream the diff

Build the review bundle (status, staged, unstaged, untracked contents) and paste it into the reviewer prompt. gx `explore` has no shell.

Past ~900 changed lines, do not paste the diff: write it to a file and name that path in the prompt, for any reviewer that can read files. Prepare it with `git add -N . && git diff HEAD > "$(mktemp -d)/x.diff"` — the intent-to-add pulls in new files, `HEAD` captures staged and unstaged together so a partially staged tree isn't half reviewed, and the `mktemp -d` path is per-invocation so parallel reviews never clobber each other. Either way the prompt says: do NOT run `git diff` or re-derive the changes; read only the named files, sections, symbols, or line ranges; stay inside a stated read budget. A reviewer left to discover a big diff dumps tens of thousands of lines and hits the cap with no verdict.

## 5. Sol-first correctness review (read-only)

Prompt for CORRECTNESS bugs, not style (simplify owns that). Scale adversarialness to gravity: routine commits get a straightforward pass; changes touching data integrity, auth/security, money, migrations, or concurrency get an explicitly adversarial prompt (assume the diff is wrong; hunt for the exploit/corruption path). Include:

- the spec/context (plan section or `$ARGUMENTS`)
- specific failure modes tailored to the diff
- a **HARD CAP of 10 minutes** — wait then kill; never wait unbounded
- empty output is a FAILURE, not "no findings"
- a fixed per-item verdict format: `no issue — why, file:line`, or a finding with `file:line` plus the concrete failure scenario; plus the list of files + line ranges the reviewer actually read

Skip this review entirely for docs-only diffs and record `review: skipped (docs-only)` in the commit message — there is no correctness surface to find.

On any harness whose orchestrator has a shell, the CodeRabbit CLI is a complementary route rather than a duplicate of the Sol pass — invocation, the `-t uncommitted` spelling on older CLIs, and the process cap are in the Claude Code subsection below, and they apply verbatim wherever you can run it.

### gx

Spawn `explore` with `model: gpt-5.6-sol`, `run_in_background: false` (or wait immediately). Description `(gpt-5.6-sol) Review …`. On auth/credit/rate-limit, empty output, or cap kill: `grok-4.6` explore, then self-review. Never spawn `openrouter/gpt-5.6-sol` unless the human opted in.

### Cursor

Spawn `explore` with `model: gpt-5.6-sol-high`. On auth/credit/rate-limit, empty, or cap kill: `cursor-grok-4.6-high` explore, then self-review. Never use `…-fast`.

### Claude Code

Direct `codex exec` (not the `codex-cli` agent). One Bash command; set the
shell-tool timeout to 600000 **and** wrap the process so a hang is killed at
600s (portable: `perl -e 'alarm 600; exec @ARGV' --`; `timeout 600` if that
binary exists — macOS ships neither `timeout` nor `gtimeout`). A timeout is a
failed review route.

If a command guard also rejects heredocs, build the prompt + bundle into a
file and redirect it instead — `codex exec … -o "$tmpdir/review.txt" - < "$tmpdir/prompt.txt"`
is equally expansion-safe. If a guard rejects the wrapper shape (`perl -e … exec`,
`bash -c`), drop it: the shell tool's own 600000 timeout is the cap, and on overrun kill
the run by matching its unique `$tmpdir` in the command line — never a blanket
`pkill -f 'codex exec'`, which also kills concurrent rescues. `echo "$tmpdir"`
before launching, or a timeout leaves you without the value to match. Kill it
you must: the leftover process keeps holding the thread, so `codex exec resume`
then fails with `thread already has an active writer`. Rerun fresh and
narrowed rather than resuming.

The trailing `-` makes Codex read the piped bundle as the prompt. Put spec /
`$ARGUMENTS`, tailored failure modes, and the 10-minute cap **in the bundle**
(same context gx/Cursor reviewers get). Because that text is user-controlled,
use a per-invocation random heredoc delimiter (shown as `REVIEW_9f3a2b1c`).
Stream git output after the heredoc — do not interpolate the diff into the
shell command.

```bash
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
echo "$tmpdir"
run_codex() { perl -e 'alarm 600; exec @ARGV' -- "$@"; }
{
  cat <<'REVIEW_9f3a2b1c'
Review the uncommitted working-tree changes below for CORRECTNESS bugs (not style). This is review-only — do not edit anything. HARD CAP: 10 minutes; return partial findings rather than hanging. Empty output is a failure, not "no findings." Spec/context for this commit:
REVIEW_9f3a2b1c
  # Agent: append the plan section or $ARGUMENTS and specific failure modes here
  # (cat a file you wrote, or a second quoted heredoc with a fresh random delimiter).
  echo "=== BEGIN CHANGES ==="
  echo; echo "--- changed files ---"; git status --short --untracked-files=all
  echo; echo "--- staged diff ---"; git diff --cached
  echo; echo "--- unstaged diff ---"; git diff
  echo; echo "--- untracked file contents ---"
  git ls-files --others --exclude-standard | while IFS= read -r f; do
    echo "===== $f ====="
    cat -- "$f"
  done
  echo "=== END CHANGES ==="
} | run_codex codex exec -s read-only -m gpt-5.6-sol -c model_reasoning_effort="high" \
  -o "$tmpdir/review.txt" - >"$tmpdir/stdout.txt" 2>"$tmpdir/stderr.txt"
status=$?
if [ $status -ne 0 ] || [ ! -s "$tmpdir/review.txt" ]; then
  echo "codex exec review failed (exit $status). Last stderr/stdout:"
  tail -n 40 "$tmpdir/stderr.txt" "$tmpdir/stdout.txt"
  exit 1
fi
cat "$tmpdir/review.txt"
```

If codex is unavailable, rate-limited, empty, or past the cap: fall back to
`cursor:cursor-rescue` with `--read-only` and the same prompt. Instruct that
agent **not** to retry with a `…-fast` model (forge never uses fast slugs);
one empty or failed run → self-review. Do not retry codex on a rate limit.
CodeRabbit's CLI, if installed, is the other route and a real complement —
`coderabbit review --agent --uncommitted --include-untracked -c <instructions>.md`
(older CLIs spell the scope `-t uncommitted`; check `coderabbit review --help`)
found a contract bug (a counter bumped only on the success path) that codex
and self-review both missed; prefer it when a sandboxed CLI reviewer refuses
to start at all. It has no cap flag of its own, so bound the process the same
way as codex — the same 600 s wrapper, or the harness's own reviewer cap — and
treat a killed run as "no review", never "no findings", and fall through. If
no external reviewer runs, self-review and say so in the commit message.

## 6. Disposition

For each finding: fix it, or record WHY it is skipped (pre-existing, deliberate house pattern, plan-pinned). Never drop a finding silently. Re-run the gate after fixes.

Check a proposed fix against the plan's pinned decisions before applying it — reviewers routinely "fix" a deliberate choice back to the default. A reviewer's "no issue" does not close an item you already flagged: record both views; the disagreement is the disposition.

Before deleting or renaming a public name in a test helper or shared module, grep for importers (`from X import`, `use crate::…`). A sibling module importing a deleted name breaks collection for every lane — including one that only *deselects* that module, since `-m 'not marker'` still imports it.

If every review route failed and there is no recorded self-review, **do not commit**.

## 7. Commit

One commit. Message = what changed and why, plus one line per notable finding and its disposition, plus `review: <model-or-self>`. Follow the repo's commit conventions. Do not push unless the calling flow or user says to.

Do not apply linter `--unsafe` autofixes.
