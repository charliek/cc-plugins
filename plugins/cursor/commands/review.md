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

- Invoke the Cursor agent in read-only mode (`--mode plan`) so it cannot edit. **Pass the review prompt via a quoted heredoc on stdin, not as an inline quoted argument** — the prompt contains backticks and `<...>` placeholders, and the quoted heredoc (`<<'CURSOR_REVIEW'`) prevents Bash from expanding them. Name the review target and tell Cursor to inspect the diff itself:

  ```bash
  agent -p --mode plan --model gpt-5.5-high <<'CURSOR_REVIEW'
  Review the local code changes in this repository. Target: <describe scope — e.g. "uncommitted working-tree changes" or "the diff of HEAD against <base>">. Inspect them yourself with git (e.g. `git status --short --untracked-files=all`, `git diff`, or `git diff <base>...HEAD`) and read the surrounding files for context. This is review-only — do not edit anything. Report concrete findings ordered by severity (most serious first), each with the exact file path and line number and a short explanation. Cover correctness, edge cases, security, and likely bugs. If you find nothing significant, say so and note residual risk briefly.
  CURSOR_REVIEW
  ```

  - Use `timeout: 600000` on foreground runs. For `--background`, launch this `Bash` call with `run_in_background: true` and tell the user: "Cursor review started in the background." Do not wait for it in this turn.
  - If the user passed `--model <id>`, use it in place of `gpt-5.5-high`.

Present results:

- Return the Cursor agent's stdout verbatim. Present findings first, ordered by severity, with file paths and line numbers exactly as reported.
- If there are no findings, say so explicitly and keep the residual-risk note brief.
- **CRITICAL — stop before fixing:** After presenting the findings, STOP. Do not make any code changes or fix any issues. You MUST explicitly ask the user which issues, if any, they want fixed before touching a single file. Auto-applying fixes from a review is forbidden, even if a fix is obvious.
