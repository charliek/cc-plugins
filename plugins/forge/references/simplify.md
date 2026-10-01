# Simplify procedure

Run after reading `harness.md`. Scope a diff, spawn three sonnet-class read-only reviewers in parallel, aggregate, optionally one fixer, re-run checks, report.

Never run this procedure on the fable-class model.

## 1. Scope

1. Explicit scope in `$ARGUMENTS` (paths, symbols, a diff, or a named area).
2. Else the combined unstaged + staged + untracked working-tree changes (`git diff`, `git diff --cached`, `git status --short --untracked-files=all`).
3. Else files or symbols named in this conversation.
4. Else `git show --stat --patch --no-color HEAD`.

Do not broaden past that scope unless needed to understand existing patterns. Preserve unrelated user changes.

## 2. Bar (skip vs run)

Simplify is good at catching duplication and needless complexity, and it pays off most on changes that introduce core interfaces or abstractions other code will build on, or that land a lot of new logic. It also costs real time and tokens — a median of ~5 minutes, a long tail past 15 — and most small changes give it nothing to find. So it is a judgment call; skipping it is normal.

Inside a gauntlet, the plan's `simplify` mark decides (`plan.md`), adjusted when the diff came out different from planned. Standalone, or when adjusting:

**Good fits** — run when any is true:

- the change introduces a core interface, abstraction, module, or public API that other code will build on
- it lands a lot of new logic
- the same logic appears in several places (in the diff, or the diff repeats something that already exists)
- a whole-branch pass before the PR, when duplication only shows up across several units

**Usually skip** — report "skipped: …" and stop:

- small or mechanical edits, moves and renames, pure deletions
- config-only, docs-only, or test-only changes
- changes that closely follow an existing pattern

Tell the reviewers which decisions are pinned spec (from the plan or `$ARGUMENTS`) so they do not "simplify away" mandated behavior.

## 3. Material to send

Use the same change bundle the review gets: `uv run --script '<runner path>' --changes-since <base> --bundle-only` (`harness.md` §Codex runner; `<base>` is `HEAD` for uncommitted changes, the merge-base with the default branch for a whole-branch pass) prints commits since `<base>`, status, the diff, and untracked file contents — or, once it is big, a file path to read. gx `explore` cannot run `git`, so paste it inline. For an explicit non-diff scope (paths, symbols), send those instead.

## 4. Three parallel reviewers

Spawn three `explore` subagents, sonnet-class `model` from the harness table, `run_in_background: true`, description prefixed `(model) Simplify: quality|performance|reuse`. Batch-wait with a 10-minute cap, then kill — deliberately shorter than the review caps: these are narrow sonnet-class passes that finish well inside it. Empty output is a failed seat.

**Quality:** low-information comments; one-off helpers used once that can be inlined; nullable value proliferation; catch-all try/catch that swallows errors; unnecessary abstraction before reuse; weak type escape hatches (`any`, casts, non-null assertions); duplicated or derived state; dead or compatibility code.

**Performance:** blocking work on hot paths; uncached expensive operations; busy waits; string concatenation in loops; N+1 I/O; chatty logging/telemetry in tight loops.

**Reuse:** existing patterns or helpers elsewhere in the codebase, or already in the diff, that this change should use.

Reviewers only report. They do not edit.

## 5. Fix

Aggregate. Skip issues that need user context or a much larger refactor than the original diff — list those in the summary.

If there is anything to apply, spawn **one** sonnet-class `general-purpose` fixer (`run_in_background: false`, `isolation` omitted) with the pinned decisions and the accepted findings. Re-run the relevant gate subset after fixes.

## 6. Report

What was fixed, what was skipped and why, which reviewer seats failed.
