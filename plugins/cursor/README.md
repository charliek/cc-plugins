# cursor

Delegate coding tasks and code reviews to the [Cursor agent CLI](https://cursor.com/cli) (`cursor-agent`, aka `cursor-agent`) from Claude Code.

This plugin drives the `cursor-agent` CLI directly in headless mode (`cursor-agent -p`) — there is no background-job runtime. Backgrounding uses Claude Code's own background tasks, and session continuity uses Cursor's native `cursor-agent --continue`.

## Commands

### `/cursor:rescue [--background|--wait] [--resume|--fresh] [--read-only] [--model <id>] [task...]`

Hand a substantial coding, debugging, or investigation task to the Cursor agent and return its output verbatim. Defaults to **write-capable** (`cursor-agent -p --force --trust`), so Cursor can edit files and run commands; changes land in the repo and are reviewable with `git diff`. Use `--read-only` for diagnosis/research without edits. `--resume` continues the previous Cursor session; `--background` runs it as a Claude background task.

The bundled **`cursor-rescue`** subagent carries the same forwarding contract, so the main thread can also delegate to Cursor autonomously (via `subagent_type`) without the slash command.

### `/cursor:review [--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <id>]`

Read-only review of local git changes. Returns findings verbatim, ordered by severity, and **stops to ask before fixing anything** — it never auto-applies changes.

### `/cursor:adversarial-review [--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <id>] [focus...]`

Like `/cursor:review`, but challenges the implementation approach, design choices, tradeoffs, and assumptions rather than just defects. Accepts optional focus text. Also read-only and stops before fixing.

### `/cursor:setup`

Check that the `cursor-agent` CLI is installed and authenticated, and report a readiness summary.

## Model selection

All commands default to the **`grok-4.7-high`** model, stated near the top of each command/subagent file (when bumping the default, update every command file plus this README). Override per call with `--model <id>`. Cursor encodes reasoning level in the model id (e.g. `grok-4.7-high`, `grok-4.7-xhigh`) — there is no separate effort flag. Run `cursor-agent --list-models` to discover available ids.

This plugin does not route OpenAI models through Cursor: OpenAI models are being removed from Cursor and were expensive on this plan. Use the `codex-cli` plugin for OpenAI models instead.

## Prerequisites

- The [Cursor agent CLI](https://cursor.com/cli) installed (see the official install instructions at https://cursor.com/cli).
- Authenticated: `cursor-agent login`.

Run `/cursor:setup` to verify both.
