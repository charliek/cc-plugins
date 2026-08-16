# codex-cli

Delegate coding tasks and code reviews to the [Codex CLI](https://developers.openai.com/codex/cli) (`codex exec`) from Claude Code.

This plugin drives `codex exec` directly in headless mode — one process per call, no daemon, no broker, no shared state. That makes it safe to run many rescues in parallel across (and within) projects, gives real stderr on failure, and lets Claude Code's own `Bash` timeouts enforce hard caps. Backgrounding uses Claude Code's background tasks, and session continuity uses Codex's native `codex exec resume --last`.

It exists alongside OpenAI's official `codex` plugin, which drives a shared `codex app-server` broker instead: the broker is single-flight per workspace and its failure contract is "return nothing", which flows can't distinguish from "no findings". Use this plugin wherever those properties matter (automated flows, parallel sessions); the official plugin remains useful for `/codex:transfer` and its background job tracking.

## Commands

### `/codex-cli:rescue [--background|--wait] [--resume|--fresh] [--read-only] [--model <id>] [--effort <level>] [task...]`

Hand a substantial coding, debugging, or investigation task to Codex and return its final message verbatim. Defaults to **write-capable** (`codex exec -s workspace-write`), so Codex can edit files and run commands inside its sandbox; changes land in the repo and are reviewable with `git diff`. Use `--read-only` for diagnosis/research without edits (`-s read-only`). `--resume` continues the most recent Codex session in the repo; `--background` runs it as a Claude background task.

The bundled **`codex-rescue`** subagent carries the same forwarding contract, so the main thread can also delegate to Codex autonomously (via `subagent_type: "codex-cli:codex-rescue"`) without the slash command.

### `/codex-cli:review [--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <id>] [--effort <level>]`

Read-only review of local git changes via `codex exec review` (`--uncommitted` or `--base <ref>` — Codex scopes the diff natively and applies its purpose-built review harness; scope flags are mutually exclusive with custom instructions, so this command passes none). Returns findings verbatim, ordered by severity, and **stops to ask before fixing anything** — it never auto-applies changes.

### `/codex-cli:adversarial-review [--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <id>] [--effort <level>] [focus...]`

Like `/codex-cli:review`, but challenges the implementation approach, design choices, tradeoffs, and assumptions rather than just defects. Accepts optional focus text. Because `codex exec review` can't take custom instructions alongside scope flags, this command uses plain `codex exec -s read-only` and streams the extracted diff in on stdin (cursor-plugin style). Also read-only and stops before fixing.

### `/codex-cli:setup`

Check that the `codex` CLI is installed and authenticated, and report a readiness summary.

## Model selection

All commands pin **`gpt-5.6-sol`** at **`model_reasoning_effort="high"`**, stated near the top of each command/subagent file (when bumping the default, update every command file plus this README). They deliberately do NOT inherit `~/.codex/config.toml`'s default, so runs are deterministic across machines. Override per call with `--model <id>` and `--effort none|minimal|low|medium|high|xhigh` (effort maps to `-c model_reasoning_effort="..."`).

## Prerequisites

- The Codex CLI installed: `npm install -g @openai/codex`.
- Authenticated: `codex login`.

Run `/codex-cli:setup` to verify both.
