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

**Skip** (report "skipped: …" and stop) when the scoped diff is:

- a pure deletion, move/rename, config-only, or docs-only change, or
- a small single-file mechanical edit that matches none of the triggers below.

**Run** when any one is true:

- ≥ ~150 changed lines (adds + deletes) of non-excluded files, or
- a new module/file with real logic, or
- the same pattern at ≥ 3 sites, or
- the orchestrator judges complexity/risk worth a pass.

Tell the reviewers which decisions are pinned spec (from the plan or `$ARGUMENTS`) so they do not "simplify away" mandated behavior.

## 3. Material to send

Build the review bundle the same way `cursor:review` does: status, staged diff, unstaged diff, and contents of listed untracked files. gx `explore` cannot run `git`, so this bundle must be inline.

## 4. Three parallel reviewers

Spawn three `explore` subagents, sonnet-class `model` from the harness table, `run_in_background: true`, description prefixed `(model) Simplify: quality|performance|reuse`. Batch-wait (10-minute cap, then kill). Empty output is a failed seat.

**Quality:** low-information comments; one-off helpers used once that can be inlined; nullable value proliferation; catch-all try/catch that swallows errors; unnecessary abstraction before reuse; weak type escape hatches (`any`, casts, non-null assertions); duplicated or derived state; dead or compatibility code.

**Performance:** blocking work on hot paths; uncached expensive operations; busy waits; string concatenation in loops; N+1 I/O; chatty logging/telemetry in tight loops.

**Reuse:** existing patterns or helpers elsewhere in the codebase, or already in the diff, that this change should use.

Reviewers only report. They do not edit.

## 5. Fix

Aggregate. Skip issues that need user context or a much larger refactor than the original diff — list those in the summary.

If there is anything to apply, spawn **one** sonnet-class `general-purpose` fixer (`run_in_background: false`, `isolation` omitted) with the pinned decisions and the accepted findings. Re-run the relevant gate subset after fixes.

## 6. Report

What was fixed, what was skipped and why, which reviewer seats failed.
