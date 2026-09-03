# codex-cli

Delegate coding tasks and code reviews to the [Codex CLI](https://developers.openai.com/codex/cli) (`codex exec`) from Claude Code.

This plugin drives `codex exec` directly in headless mode — one process per call, no daemon, no broker, no shared state. That makes it safe to run many **fresh** rescues in parallel across (and within) projects, gives real stderr on failure, and lets Claude Code's own `Bash` timeouts enforce hard caps. (Resumed runs are the exception: `--resume` selects the newest session in the repo, so use `--fresh` whenever concurrent tasks are possible.) Backgrounding uses Claude Code's background tasks, and session continuity uses Codex's native `codex exec resume --last`.

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

## Knowledge baked in (learned the hard way)

- **Never let Codex derive a big diff itself.** Past ~900 changed lines, a
  Codex told to review "the current changes" runs `git diff` at
  `--unified=999999`, dumps ~30k lines, and hits the 10-minute cap without a
  verdict. Write the diff to a file first (`git diff > /tmp/x.diff`; `git add -N`
  for new files so they appear), and tell it: read this file first, do NOT run
  `git diff`, then read only the named functions with narrow line ranges.
- **Budget the run in the prompt**: "at most N minutes and M file reads; print
  the report and stop." Pair it with a fixed per-item verdict format — either
  `no issue — why, file:line` or a finding with `file:line` plus the concrete
  failure scenario — and require it to list the files + line ranges it read.
  Unbudgeted big reviews return prose and no verdicts.
- **A missing or empty `-o` file is "no review", never "no findings".** An
  interrupted or killed run writes nothing; treat it as a failed route and
  fall back.
- **A killed run leaves the thread locked.** The `codex exec` process outlives
  the cap kill and keeps the thread, so `codex exec resume <id>` then fails
  with `thread already has an active writer`. Kill the leftover process (match
  the run's own `$tmpdir` in the command line, not every `codex exec`) and
  rerun a fresh, narrowed prompt — that beat resuming every time.
- **Long or generated prompts go in as a file**: `codex exec … -o /tmp/out.txt - < prompt.txt`
  is as expansion-safe as a quoted heredoc and survives command guards that
  reject heredocs. It needs a file-writing tool, so the rescue command and
  subagent (Bash-only) keep the heredoc form.
- **CodeRabbit's CLI complements Codex rather than duplicating it**:
  `coderabbit review --agent --uncommitted --include-untracked -c instructions.md`
  caught a contract bug (a counter bumped only on the success path) that both
  Codex and self-review missed. Reach for it when Codex stalls or is
  rate-limited.

## Prerequisites

- The Codex CLI installed: `npm install -g @openai/codex`.
- Authenticated: `codex login`.

Run `/codex-cli:setup` to verify both.
