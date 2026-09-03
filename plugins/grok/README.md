# grok

Delegate coding tasks to the [Grok CLI](https://x.ai/cli) (`grok -p`) from Claude Code.

This plugin drives `grok` directly in headless mode — one process per call, no ACP stdio client, no leader, no shared broker. That makes it safe to run many **fresh** rescues in parallel across (and within) projects, gives real stderr on failure, and lets Claude Code's own `Bash` timeouts enforce hard caps. (Resumed runs are the exception: `-c` / `--continue` selects the newest session in this working directory, so pass an explicit `--resume <uuid>` or use `--fresh` whenever concurrent tasks are possible.) Backgrounding uses Claude Code's own background tasks.

Review commands, plan-panel review, and gauntlet integration are intentionally not in this first cut. The bundled **`grok-rescue`** subagent is the hook those will call later (`subagent_type: "grok:grok-rescue"`).

## Commands

### `/grok:rescue [--background|--wait] [--resume|--fresh] [--read-only] [--model <id>] [--effort <level>] [task...]`

Hand a substantial coding, debugging, or investigation task to Grok and return its final message verbatim. Defaults to **write-capable** (`grok --always-approve`), so Grok can edit files and run commands; changes land in the repo and are reviewable with `git diff`. Use `--read-only` for diagnosis/research without edits (`--sandbox read-only`). `--resume` continues a prior Grok session (see below); `--background` runs it as a Claude background task.

The bundled **`grok-rescue`** subagent carries the same forwarding contract, so the main thread can also delegate to Grok autonomously (via `subagent_type: "grok:grok-rescue"`) without the slash command.

### `/grok:setup`

Check that the `grok` CLI is installed and authenticated, and report a readiness summary.

## Model selection

All commands pin **`grok-4.6`** at **`--effort high`**, stated near the top of each command/subagent file (when bumping the default, update every command file plus this README). They deliberately do NOT inherit `~/.grok/config.toml`'s default, so runs are deterministic across machines.

Override per call with `--model <id>` and `--effort low|medium|high|xhigh`. Fast mode is `--effort low` (Grok has no Cursor-style `…-fast` serving-pool sibling — do not treat a lower effort as a retry backup). `xhigh` is available on `grok-4.6` only.

List ids with `grok models`.

## Session resume

Each headless run returns a `sessionId` in `--output-format json` (the plugin prints `GROK_SESSION_ID=…` on stderr). Prefer that UUID on the next call:

- `--resume <uuid>`: continue that exact session (`grok --resume <uuid>`).
- `--resume` with no UUID: `grok -c` (newest session in this working directory). **Races** if another Grok run is in flight here — use `--fresh` or restated context instead.
- `--fresh`: always start a new session, even if the request sounds like a follow-up.

## Known gotchas

- `--sandbox read-only` needs a container runtime, and Grok refuses to start
  when `/var/run/docker.sock` is a **symlink** (the Docker Desktop layout on
  macOS). When that bites, a read-only Grok run is unavailable — use another
  reviewer rather than dropping the read-only requirement.

## Prerequisites

- The Grok CLI installed: `curl -fsSL https://x.ai/cli/install.sh | bash`.
- Authenticated: `grok login`.

Run `/grok:setup` to verify both.
