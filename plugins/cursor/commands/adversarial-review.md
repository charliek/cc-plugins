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

**Feed the diff in — do not ask Cursor to discover the changes itself** (same approach as `/cursor:review`, mirroring how Codex and CodeRabbit extract the diff before handing it to the reviewer). Build the prompt as a single pipeline: a quoted heredoc carries the adversarial instructions (and any focus text), and `git` streams the diff into the same stdin. The quoted heredoc means focus text and diff content are never shell-expanded.

- **Working-tree scope:**

  ```bash
  {
    cat <<'CURSOR_REVIEW'
  Adversarially review the code changes below — the uncommitted working-tree changes of this repository, provided inline between the "=== BEGIN CHANGES ===" and "=== END CHANGES ===" markers. This is review-only — do not edit anything. You MAY read other files in the repo for context, but do not modify anything. Challenge the approach itself: question the design choices, tradeoffs, and assumptions; identify where this could fail under real-world conditions (scale, concurrency, failure modes, edge cases, maintainability); and propose stronger alternatives where the chosen approach is weak. <If focus text was provided, append: "Focus especially on: <focus text>."> Order findings by severity, each with exact file path and line number where applicable and a short rationale.
  CURSOR_REVIEW
    echo "=== BEGIN CHANGES ==="
    echo; echo "--- changed files ---"; git status --short --untracked-files=all
    echo; echo "--- staged diff ---"; git diff --cached
    echo; echo "--- unstaged diff ---"; git diff
    echo "=== END CHANGES ==="
  } | agent -p --mode plan --model gpt-5.5-high
  ```

- **Branch / base scope** (replace `<base>` with the resolved ref, default `main`): use the same pipeline but stream `git diff --name-status <base>...HEAD` and `git diff <base>...HEAD`, and word the heredoc as "the diff of HEAD against <base>".

  - **Pick a collision-free delimiter.** The heredoc body here includes user-controlled focus text. If that text contains a line exactly equal to `CURSOR_REVIEW`, the heredoc would close early. If the focus text could contain such a line, use a unique delimiter (e.g. `CURSOR_REVIEW_a1b2c3d4`) for both the opener and closer. (The streamed diff cannot collide — it arrives after the heredoc closes.)
  - `--mode plan` keeps Cursor read-only. Use `timeout: 600000` on foreground runs. For `--background`, launch the pipeline with `run_in_background: true` and tell the user: "Cursor adversarial review started in the background." Do not wait for it in this turn.
  - If the user passed `--model <id>`, use it in place of `gpt-5.5-high`.

Present results:

- Return the Cursor agent's stdout verbatim, findings first, ordered by severity, with file paths and line numbers exactly as reported.
- **CRITICAL — stop before fixing:** After presenting the findings, STOP. Do not make any code changes or fix any issues. You MUST explicitly ask the user which issues, if any, they want addressed before touching a single file.
