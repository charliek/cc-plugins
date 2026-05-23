---
description: Run a Cursor agent review that challenges the implementation approach and design choices
argument-hint: '[--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <model>] [focus ...]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(agent:*), Bash(git:*), AskUserQuestion
---

Run an adversarial code review through the Cursor `agent` CLI. Frame it as a **challenge review** that questions the chosen implementation, design choices, tradeoffs, and assumptions — not just a stricter pass over implementation defects.

Raw slash-command arguments:
`$ARGUMENTS`

Default model: `gpt-5.5-high` (override with `--model <id>`; run `agent --list-models` for ids).

Core constraint:

- This command is **review-only**. Do not fix issues, apply patches, edit files, or suggest you are about to make changes.
- Your only job is to run the review and return the Cursor agent's output verbatim.
- Keep the framing on whether the current approach is the right one, what assumptions it depends on, and where the design could fail under real-world conditions.

Determine the review target and execution mode exactly as in `/cursor:review`:

- `--scope working-tree`/`auto` → uncommitted changes; `--scope branch`/`--base <ref>` → branch diff against `<ref>` (default base `main`).
- `--wait` → foreground, `--background` → Claude background task, neither → size the change (`git status --short --untracked-files=all`, `git diff --shortstat [--cached]`, or `git diff --shortstat <base>...HEAD`) and ask once via `AskUserQuestion` (`Wait for results` / `Run in background`), recommending background unless the change is clearly tiny.
- Unlike `/cursor:review`, any trailing text after the flags is **focus text** — preserve it and steer the review toward it.

Run the review:

- **Pass the prompt via a quoted heredoc on stdin, not as an inline quoted argument** (it contains backticks, `<...>` placeholders, and user focus text that must not be shell-expanded):

  ```bash
  agent -p --mode plan --model gpt-5.5-high <<'CURSOR_REVIEW'
  Adversarially review the local code changes in this repository. Target: <describe scope>. Inspect them yourself with git (e.g. `git status --short --untracked-files=all`, `git diff`, or `git diff <base>...HEAD`) and read surrounding files for context. This is review-only — do not edit anything. Challenge the approach itself: question the design choices, tradeoffs, and assumptions; identify where this could fail under real-world conditions (scale, concurrency, failure modes, edge cases, maintainability); and propose stronger alternatives where the chosen approach is weak. <If focus text was provided: "Focus especially on: <focus text>.">  Order findings by severity, each with exact file path and line number where applicable and a short rationale.
  CURSOR_REVIEW
  ```

  - Use `timeout: 600000` on foreground runs. For `--background`, launch this `Bash` call with `run_in_background: true` and tell the user: "Cursor adversarial review started in the background." Do not wait for it in this turn.
  - If the user passed `--model <id>`, use it in place of `gpt-5.5-high`.

Present results:

- Return the Cursor agent's stdout verbatim, findings first, ordered by severity, with file paths and line numbers exactly as reported.
- **CRITICAL — stop before fixing:** After presenting the findings, STOP. Do not make any code changes or fix any issues. You MUST explicitly ask the user which issues, if any, they want addressed before touching a single file.
