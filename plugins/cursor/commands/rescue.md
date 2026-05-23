---
description: Delegate investigation, an explicit fix request, or follow-up work to the Cursor agent rescue subagent
argument-hint: "[--background|--wait] [--resume|--fresh] [--read-only] [--model <model>] [what Cursor should investigate, solve, or continue]"
context: fork
allowed-tools: AskUserQuestion
---

Route this request to the `cursor:cursor-rescue` subagent.
The final user-visible response must be the Cursor agent's output verbatim.

Raw user request:
$ARGUMENTS

Execution mode:

- If the request includes `--background`, run the `cursor:cursor-rescue` subagent in the background (launch the Agent tool with `run_in_background: true`).
- If the request includes `--wait`, run the `cursor:cursor-rescue` subagent in the foreground.
- If neither flag is present, default to foreground for a small, clearly bounded request. If the task looks complicated, open-ended, multi-step, or likely to keep Cursor running for a long time, prefer background.
- `--background` and `--wait` are execution controls for Claude Code. Do not forward them to the `agent` CLI, and do not treat them as part of the task text.

Routing flags (leave these in the request you hand to the subagent — it strips and applies them when building the `agent` command):

- `--resume` / `--fresh`: continue the previous Cursor session vs. start clean. If the user clearly gave a follow-up instruction ("continue", "keep going", "resume", "apply the top fix", "dig deeper"), the subagent will continue automatically; pass `--fresh` only to force a new session.
- `--read-only`: the subagent runs Cursor in read-only `--mode plan` (no edits) instead of the default write-capable `--force`.
- `--model <id>`: a specific Cursor model id, replacing the default `gpt-5.5-high`. There is no `--effort` flag — reasoning level is part of the model id. Run `agent --list-models` to discover ids.

Operating rules:

- The subagent is a thin forwarder only. It uses one `Bash` call to invoke `agent -p ...` and returns that command's stdout as-is.
- Return the Cursor agent's stdout verbatim to the user. Do not paraphrase, summarize, rewrite, or add commentary before or after it.
- Do not ask the subagent to inspect files, monitor progress, summarize output, or do follow-up work of its own.
- By default the rescue is write-capable (`--force`), so Cursor may edit files and run commands. Changes land in the current git repo and are reviewable via `git diff`.
- If the user did not supply a request, ask what Cursor should investigate or fix before routing.
