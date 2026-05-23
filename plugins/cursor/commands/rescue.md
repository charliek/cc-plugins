---
description: Delegate investigation, an explicit fix request, or follow-up work to the Cursor agent CLI
argument-hint: "[--background|--wait] [--resume|--fresh] [--read-only] [--model <model>] [what Cursor should investigate, solve, or continue]"
context: fork
allowed-tools: Bash(agent:*), AskUserQuestion
---

Hand this request to the Cursor `agent` CLI and return its output verbatim.

Raw user request:
$ARGUMENTS

Default model: `gpt-5.5-high` (override with `--model <id>`; run `agent --list-models` for ids).

Build a single `agent` invocation. **Pass the task text via a quoted heredoc on stdin, never as an inline quoted argument** — this prevents `$(...)`, backticks, `$VAR`, quotes, and newlines in the task from being expanded by Bash. `agent -p` reads the prompt from stdin when no prompt argument is given.

**Always use a per-invocation random delimiter** — append fresh random hex to the base token (shown below as `CURSOR_TASK_9f3a2b1c`) and never use the bare `CURSOR_TASK`. Because the suffix is unpredictable and unique per call, the task text can never match the delimiter and terminate the heredoc early, even though it is inserted verbatim. Use the same token for the opener and closer; generate a new one each invocation.

Write-capable run (the default):

```bash
agent -p --force --model gpt-5.5-high <<'CURSOR_TASK_9f3a2b1c'
<task text exactly as the user gave it, with routing flags stripped>
CURSOR_TASK_9f3a2b1c
```

Read-only run (when `--read-only` is present, or the user only wants review/diagnosis/research without edits) — replace `--force` with `--mode plan`:

```bash
agent -p --mode plan --model gpt-5.5-high <<'CURSOR_TASK_9f3a2b1c'
<task text>
CURSOR_TASK_9f3a2b1c
```

Flag handling (strip these from the task text before placing it in the heredoc body — they are controls, not part of the prompt):

- `--background`: run the `Bash` call with `run_in_background: true` and tell the user the Cursor task started in the background. Do not wait for it this turn.
- `--wait` (or neither): run in the foreground with `timeout: 600000` (the maximum; Cursor tasks can run several minutes).
- `--read-only`: use `--mode plan` instead of `--force`.
- `--model <id>`: use it in place of `gpt-5.5-high`. There is no `--effort` flag — reasoning level is part of the model id.
- `--resume`: add `--continue` (continue the previous Cursor session). `--fresh`: do not. If neither is given and the user is clearly continuing prior Cursor work ("continue", "keep going", "apply the top fix", "dig deeper"), add `--continue`; otherwise run fresh.
- If a run stalls on a workspace-trust prompt, add `--trust`.

Output:

- Return the Cursor agent's stdout verbatim. Do not paraphrase, summarize, rewrite, or add commentary before or after it.
- By default the run is write-capable (`--force`), so Cursor may edit files and run commands. Changes land in the current git repo and are reviewable via `git diff`.
- On failure, do **not** fabricate a substitute answer. If the call fails or `agent` cannot be invoked, report the failure concisely (most actionable stderr lines); if `agent` looks missing or unauthenticated, direct the user to `/cursor:setup`.
- If the user did not supply a request, ask what Cursor should investigate or fix before running.
