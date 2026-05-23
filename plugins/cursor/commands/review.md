---
description: Run a Cursor agent code review against local git state
argument-hint: '[--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <model>]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(agent:*), Bash(git:*), AskUserQuestion
---

Run a read-only code review of local git changes through the Cursor `agent` CLI.

Raw slash-command arguments:
`$ARGUMENTS`

Default model: `gpt-5.5-high` (override with `--model <id>`; run `agent --list-models` for ids).

Core constraint:

- This command is **review-only**. Do not fix issues, apply patches, edit files, or suggest you are about to make changes.
- Your only job is to run the review and return the Cursor agent's output verbatim.

Determine the review target:

- `--scope working-tree` (or `auto` with no base): uncommitted changes — staged + unstaged + untracked.
- `--scope branch` or `--base <ref>`: the diff of the current branch against `<ref>` (default base `main` when `--scope branch` is given without `--base`).

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

**Feed the diff in — do not ask Cursor to discover the changes itself.** This mirrors how the Codex and CodeRabbit reviewers work (a deterministic layer extracts the diff and hands it to the reviewer) and avoids depending on Cursor's in-sandbox command approval. Build the prompt as a single pipeline: a quoted heredoc carries the review instructions, and `git` streams the actual diff into the same stdin. Because the diff arrives as `git`'s output (not via inline interpolation or `$(…)`), no shell expansion of the diff content can occur.

- **Working-tree scope** (uncommitted: staged + unstaged + untracked):

  ```bash
  {
    cat <<'CURSOR_REVIEW'
  Review the code changes below. They are the uncommitted working-tree changes of this repository, provided inline between the markers. This is review-only — do not edit anything. You MAY read other files in the repo for context, but do not modify anything. Report concrete findings ordered by severity (most serious first), each with the exact file path and line number and a short explanation. Cover correctness, edge cases, security, and likely bugs. Also read any untracked files listed below (their contents are not in the diff). If you find nothing significant, say so and note residual risk briefly.
  CURSOR_REVIEW
    echo; echo "=== changed files ==="; git status --short --untracked-files=all
    echo; echo "=== staged diff ==="; git diff --cached
    echo; echo "=== unstaged diff ==="; git diff
  } | agent -p --mode plan --model gpt-5.5-high
  ```

- **Branch / base scope** (replace `<base>` with the resolved ref, default `main`):

  ```bash
  {
    cat <<'CURSOR_REVIEW'
  Review the code changes below. They are the diff of HEAD against <base> for this repository, provided inline between the markers. This is review-only — do not edit anything. You MAY read other files in the repo for context, but do not modify anything. Report concrete findings ordered by severity (most serious first), each with the exact file path and line number and a short explanation. Cover correctness, edge cases, security, and likely bugs. If you find nothing significant, say so and note residual risk briefly.
  CURSOR_REVIEW
    echo; echo "=== changed files (vs <base>) ==="; git diff --name-status <base>...HEAD
    echo; echo "=== diff (vs <base>) ==="; git diff <base>...HEAD
  } | agent -p --mode plan --model gpt-5.5-high
  ```

  - `--mode plan` keeps Cursor read-only (it analyzes and may read files, but makes no edits).
  - Use `timeout: 600000` on foreground runs. For `--background`, launch this `Bash` pipeline with `run_in_background: true` and tell the user: "Cursor review started in the background." Do not wait for it in this turn.
  - If the user passed `--model <id>`, use it in place of `gpt-5.5-high`.

Present results:

- Return the Cursor agent's stdout verbatim. Present findings first, ordered by severity, with file paths and line numbers exactly as reported.
- If there are no findings, say so explicitly and keep the residual-risk note brief.
- **CRITICAL — stop before fixing:** After presenting the findings, STOP. Do not make any code changes or fix any issues. You MUST explicitly ask the user which issues, if any, they want fixed before touching a single file. Auto-applying fixes from a review is forbidden, even if a fix is obvious.
