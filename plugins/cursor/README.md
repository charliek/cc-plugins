# cursor

Delegate coding tasks and code reviews to the [Cursor agent CLI](https://cursor.com/cli) (`agent`, aka `cursor-agent`) from Claude Code.

This plugin drives the `agent` CLI directly in headless mode (`agent -p`) — there is no background-job runtime. Backgrounding uses Claude Code's own background tasks, and session continuity uses Cursor's native `agent --continue`.

## Commands

### `/cursor:rescue [--background|--wait] [--resume|--fresh] [--read-only] [--model <id>] [task...]`

Hand a substantial coding, debugging, or investigation task to the Cursor agent via the thin `cursor-rescue` subagent, which returns Cursor's output verbatim. Defaults to **write-capable** (`agent -p --force`), so Cursor can edit files and run commands; changes land in the repo and are reviewable with `git diff`. Use `--read-only` for diagnosis/research without edits. `--resume` continues the previous Cursor session; `--background` runs it as a Claude background task.

### `/cursor:review [--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <id>]`

Read-only review of local git changes. Returns findings verbatim, ordered by severity, and **stops to ask before fixing anything** — it never auto-applies changes.

### `/cursor:adversarial-review [--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <id>] [focus...]`

Like `/cursor:review`, but challenges the implementation approach, design choices, tradeoffs, and assumptions rather than just defects. Accepts optional focus text. Also read-only and stops before fixing.

### `/cursor:setup`

Check that the `agent` CLI is installed and authenticated, and report a readiness summary.

## Model selection

All commands default to the **`gpt-5.5-high`** model, set as a constant near the top of each command/subagent file (change it in one place). Override per call with `--model <id>`. Cursor encodes reasoning level in the model id (e.g. `gpt-5.5-high`, `claude-opus-4-7-high`) — there is no separate effort flag. Run `agent --list-models` to discover available ids.

## Prerequisites

- The [Cursor agent CLI](https://cursor.com/cli) installed (`curl https://cursor.com/install -fsS | bash`).
- Authenticated: `agent login`.

Run `/cursor:setup` to verify both.
