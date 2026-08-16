---
description: Run a Codex code review against local git state via codex exec review
argument-hint: '[--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <model>] [--effort <level>]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(codex:*), Bash(git:*), AskUserQuestion
---

Run a read-only code review of local git changes through `codex exec review`.

Raw slash-command arguments:
`$ARGUMENTS`

Default model: `gpt-5.6-sol` at `model_reasoning_effort="high"` (override with `--model <id>` and/or `--effort <level>`).

Core constraint:

- This command is **review-only**. Do not fix issues, apply patches, edit files, or suggest you are about to make changes.
- Your only job is to run the review and return Codex's output verbatim.

Determine the review target:

- `--scope working-tree` (or `auto` with no base): uncommitted changes — staged + unstaged + untracked → `codex exec review --uncommitted`.
- `--scope branch` or `--base <ref>`: the diff of the current branch against `<ref>` → `codex exec review --base <ref>` (default base `main` when `--scope branch` is given without `--base`).

Estimate size, then choose execution mode:

- If the arguments include `--wait`, run in the foreground. If they include `--background`, run as a Claude background task. Do not ask in either case.
- Otherwise size the change first:
  - Working-tree: `git status --short --untracked-files=all`, plus `git diff --shortstat --cached` and `git diff --shortstat`.
  - Branch/base: `git diff --shortstat <base>...HEAD`.
  - Treat untracked files as reviewable even when `git diff --shortstat` is empty.
  - Only conclude there is nothing to review when the relevant scope is genuinely empty.
- Then use `AskUserQuestion` exactly once with two options, recommended option first and suffixed `(Recommended)`:
  - `Wait for results`
  - `Run in background`
  - Recommend waiting only when the change is clearly tiny (~1-2 files, no directory-sized change); otherwise recommend background.

Run the review:

`codex exec review` scopes the diff itself and applies Codex's purpose-built review harness. **Do not pass custom review instructions** — the scope flags (`--uncommitted`, `--base`) are mutually exclusive with a prompt argument (the CLI exits with a usage error). For a custom-framed review, use `/codex-cli:adversarial-review` instead, which trades the native harness for custom instructions.

- **Working-tree scope** (uncommitted: staged + unstaged + untracked):

  ```bash
  tmpdir=$(mktemp -d)
  trap 'rm -rf "$tmpdir"' EXIT
  codex exec -s read-only review --uncommitted -m gpt-5.6-sol -c model_reasoning_effort="high" \
    -o "$tmpdir/review.txt" >"$tmpdir/stdout.txt" 2>"$tmpdir/stderr.txt"
  status=$?
  if [ $status -ne 0 ] || [ ! -s "$tmpdir/review.txt" ]; then
    echo "codex exec review failed (exit $status). Last stderr/stdout:"
    tail -n 40 "$tmpdir/stderr.txt" "$tmpdir/stdout.txt"
    exit 1
  fi
  cat "$tmpdir/review.txt"
  ```

- **Branch / base scope** (replace `<base>` with the resolved ref, default `main`): same pipeline with `--base <base>` in place of `--uncommitted`. Validate the ref first with `git rev-parse --verify --quiet "<base>"` and stop with an error if it doesn't resolve.

- `-s read-only` sits at the `exec` level (before `review` — the subcommand rejects it) and pins the sandbox regardless of project/user config.

- Use `timeout: 600000` on foreground runs. For `--background`, launch this `Bash` pipeline with `run_in_background: true` and tell the user: "Codex review started in the background." Do not wait for it in this turn.
- If the user passed `--model <id>`, use it in place of `gpt-5.6-sol`; if `--effort <level>`, use it in place of `high`.

Present results:

- Return Codex's review output verbatim. Present findings first, ordered by severity, with file paths and line numbers exactly as reported.
- If there are no findings, say so explicitly. A failed or empty run is NOT "no findings" — report it as a failure.
- **CRITICAL — stop before fixing:** After presenting the findings, STOP. Do not make any code changes or fix any issues. You MUST explicitly ask the user which issues, if any, they want fixed before touching a single file. Auto-applying fixes from a review is forbidden, even if a fix is obvious.
