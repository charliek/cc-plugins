# Gated-commit procedure

Run after reading `harness.md` (and `simplify.md` when a simplify pass is due). Take the current uncommitted working-tree changes through gate → simplify (when it earns its cost) → Codex review (per commit or per batch) → dispositions → one commit. Do not push unless the caller says to.

`$ARGUMENTS` describes what the commit is — inside a gauntlet, the plan section plus the unit's `simplify` and `review` marks (`plan.md`). If empty, derive it from the diff.

## 1. Discover the gate

Read CLAUDE.md, then AGENTS.md, for the per-commit gate (lint / test / build). If neither defines one, derive it from Makefile / package.json / CI and say which commands you chose. Typical shape: `make lint && make test && <frontend build if present>`.

Read CI even when CLAUDE.md defines a gate: grep the workflow for build/test invocations the documented targets don't cover (feature-gated or per-crate/per-package steps especially) and add the ones covering the code you touched. A CI-only feature build caught an exhaustive-match break the whole local gate missed.

## 2. Run the gate

All gate commands must pass before anything else. Fix failures in the diff's own code; do not weaken tests to pass them. Run each gate command unpiped: `make test | tail` reports `tail`'s exit code, not the tests'.

Test-bearing diffs: rebuild before running (a stale binary passes vacuously), and give every new or converted functional test a negative control — break the expectation, watch it fail on that exact line, restore. An assertion never seen red is not evidence.

## 3. Simplify — when it earns its cost

Inside a gauntlet the plan's `simplify` mark decides; adjust when the diff came out different from the plan (bigger or more structural → add a pass; smaller → drop it) and say why in the commit message. Standalone, judge the diff against the bar in `simplify.md`. When a pass is due, run the simplify procedure inline (do not emit `/forge:simplify`) — sonnet-class, never fable-class — then re-run the relevant gate subset. Simplify output is ordinary code: it goes through the review below.

## 4. Scope the review: one commit or one batch

Every commit is covered by an external correctness review before the branch is pushed, but coverage can be shared:

- **Per commit** is the default standalone.
- **Batch**: small consecutive units may share one review of their combined diff when that is more efficient. The plan's `review` mark names the batch (`sol, batch U3–U5`); regroup at runtime if units came out different, and say so. Commit the earlier units after their gate with `review: pending (batch U3–U5)`. The batch **closes** on its last unit: before committing it, review everything since the batch's base commit, fix findings in any of the batch's units in that closing commit, and record `review: <model> (covers U3–U5)`.
- **Astra-tier units are reviewed alone.**

A batch that stalls or hits the cap is too big for one pass: split it into two narrower reviews rather than re-running it whole.

## 5. Codex review (read-only)

**Tier** — from the unit's `review` mark, or standalone from the diff: `gpt-6-sol` for routine work; `gpt-6-astra` when the unit is complex or subtle (the opus/fable bar) or touches concurrency/ordering, data integrity, auth/security, money, migrations, or wire protocols.

**Prompt** — CORRECTNESS bugs, not style (simplify owns that). Sol gets a straightforward correctness pass; astra gets an explicitly adversarial one (assume the diff is wrong; hunt for the exploit or corruption path) plus the plan's panel findings as a hunt list when a plan exists. Always include:

- the spec/context (plan section or `$ARGUMENTS`)
- specific failure modes tailored to the diff
- a fixed per-item verdict format: `no issue — why, file:line`, or a finding with `file:line` plus the concrete failure scenario; plus the list of files + line ranges the reviewer actually read
- review-only: do not edit anything

**Changes** — every route reviews the same bundle: commits since the scope's base, status, the diff against it, and untracked file contents. The codex runner builds it itself with `--changes-since <base>` (`HEAD` for one uncommitted unit, the batch's base commit for a batch). For any other reviewer, produce the identical text with `uv run --script '<runner path>' --changes-since <base> --bundle-only` and paste it inline — gx `explore` has no shell. (`<runner path>` is the absolute path from `harness.md` §Codex runner, step 1; that section also gives the plain-git fallback when codex-cli is not installed.) Past ~900 lines or ~100 KB the bundle is a file path plus instructions to read only what is needed; a reviewer left to discover a big diff itself dumps tens of thousands of lines and reaches the cap with no verdict.

Skip this review entirely for docs-only diffs and record `review: skipped (docs-only)` in the commit message — there is no correctness surface to find, and that line is the commit's coverage.

### Claude Code, Cursor, and stock grok — the codex runner

Follow `harness.md` §Codex runner — three plain commands: locate the runner, write the prompt with the file-writing tool, then launch it from the orchestrator's shell **in the background** and wait for its exit:

```bash
uv run --script '<runner path>' --model sol --changes-since HEAD --prompt-file '<prompt file>'
# astra: --model astra.  Batch-closing review: --changes-since <batch base commit>.
```

Inside a gauntlet, add `--out '<plan artifact folder>/reviews/<unit>.md'` to keep each review with the plan (the background task's output has it too). Exit `0` prints the review. Any other exit is "no review" — take the fallback.

**Fallback (one):**

- **Claude Code:** `cursor:cursor-rescue` with the same prompt and changes — the failed run's `<run-dir>/prompt.txt` is exactly what codex got (the runner keeps its run directory on failure and names it in its second line); `--bundle-only` rebuilds the bundle from the tree as it is now — stated as a **read-only review — make no edits** (that is what switches it to Cursor's `--mode plan`; it has no `--read-only` flag). It runs Grok 4.7 through Cursor; its foreground shell call is capped at 10 minutes, so hand it the file form for anything big. Tell it **not** to retry with a `…-fast` model — forge never uses fast slugs. If Cursor is unavailable, the CodeRabbit CLI instead — `coderabbit review --agent --uncommitted --include-untracked -c <instructions>.md` for one uncommitted unit, `--base-commit <batch base> --include-untracked` in place of `--uncommitted` for a batch (older CLIs spell the uncommitted scope `-t uncommitted`; check `coderabbit review --help`) — bounded by the shell tool's 600000 timeout; a killed run is "no review". CodeRabbit found a contract bug (a counter bumped only on the success path) that Codex and self-review both missed, so it is a real complement, not a formality.
- **Cursor:** spawn `explore` with `model: grok-4.7-high` and the failed run's `<run-dir>/prompt.txt` (or the prompt plus a fresh `--bundle-only`). Never `…-fast`, never an OpenAI slug.
- **Stock grok:** spawn `explore` with `model: grok-4.7` and the failed run's `<run-dir>/prompt.txt` (or the prompt plus a fresh `--bundle-only`).
- After exit `7` (usage limit / rate limit / capacity), never retry codex — the retry hits the same quota.
- If the fallback also fails, self-review and say so in the commit message.

### gx — native GPT-6 subagent

Spawn `explore` with `model: gpt-6-sol` or `model: gpt-6-astra`, `run_in_background: true`, description `(gpt-6-sol) Review …`, and the prompt plus the `--bundle-only` text inline. Then wait on its task output in 10-minute slices up to the cap (20 minutes; 25 for astra): after each slice, check it is still producing and kill a flat one early. A foreground spawn would block you from doing either. Never spawn an `openrouter/gpt-*` id unless the human opted in.

If gx rejects the `gpt-6-*` slug (a build without the preset — see `harness.md`), that is not a failed review: run the codex runner from the orchestrator's shell instead, as above. On auth/credit/rate-limit, empty output, a flat subagent, or a cap kill: **one** fallback — `grok-4.7` explore with the same prompt — then self-review.

## 6. Disposition

For each finding: fix it, or record WHY it is skipped (pre-existing, deliberate house pattern, plan-pinned). Never drop a finding silently. Re-run the gate after fixes.

Check a proposed fix against the plan's pinned decisions before applying it — reviewers routinely "fix" a deliberate choice back to the default. A reviewer's "no issue" does not close an item you already flagged: record both views; the disagreement is the disposition.

Before deleting or renaming a public name in a test helper or shared module, grep for importers (`from X import`, `use crate::…`). A sibling module importing a deleted name breaks collection for every lane — including one that only *deselects* that module, since `-m 'not marker'` still imports it.

If every review route failed and there is no recorded self-review, **do not commit**.

## 7. Commit

One commit. Message = what changed and why, plus one line per notable finding and its disposition, plus `review: <model-or-self> [(covers U…)]` — or `review: pending (batch U3–U5)` for a unit its batch will cover — and a `simplify:` line when a pass ran or a planned one was dropped. Follow the repo's commit conventions. Do not push unless the calling flow or user says to.

Do not apply linter `--unsafe` autofixes.
