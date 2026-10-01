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

OpenAI's GPT-6 lineup has three tiers: **`gpt-6-astra`** (frontier, fable/opus-class), **`gpt-6.1-sol`** (the workhorse, between opus and sonnet; the 6.1 refresh replaced `gpt-6-sol`), and **`gpt-6-luna`** (fast and cheap). `rescue` and `review` pin **`gpt-6.1-sol`**; `adversarial-review` pins **`gpt-6-astra`**, because a challenge review is where the deeper model pays off. All run at **`model_reasoning_effort="high"`**, stated near the top of each command/subagent file (when bumping a default, update every command file, `scripts/codex-run.py`, and this README). They deliberately do NOT inherit `~/.codex/config.toml`'s default — that is often `gpt-6-astra`, so an unflagged call would silently put a routine task on the expensive model. Override per call with `--model sol|astra|luna|<id>` and `--effort none|minimal|low|medium|high|xhigh|max|ultra` (effort maps to `-c model_reasoning_effort="..."`).

## Supervised runner: `scripts/codex-run.py`

The engine for **scripted** Codex calls — the gated-commit and branch reviews in `flows` and `forge`, and the plan-panel seats in `planning` and `forge`. The commands above stay interactive tools with their own recipes; automated flows call the runner instead of pasting a shell recipe, because a flow needs three things a recipe does badly:

- **Runs longer than one shell call.** Reviews get 20 minutes on sol and 25 on astra, past the 10-minute ceiling of a single foreground call. Launch the runner in the background; the caller is told when it exits.
- **Progress checks.** Every 10 minutes it checks that Codex's log is still growing and kills a run that has gone flat, instead of waiting out the cap. It kills the whole process group, so no leftover `codex exec` keeps the thread locked — including when the caller kills the runner.
- **An honest outcome.** A distinct exit code per outcome: `0` ok, `2` usage, `3` failed, `4` empty, `5` stalled, `6` capped, `7` limited (usage limit, rate limit, or capacity — go straight to the fallback, don't retry codex), `8` auth, `9` codex missing. Anything but `0` is "no review", never "no findings". On failure it keeps its run directory (named in its second output line): `prompt.txt` there is exactly what codex got, ready to hand to a fallback reviewer.

On Python builds without `os.waitid` — macOS before Python 3.13 — the runner can't tell that codex exited without reaping it, and a reaped leader's process-group id may be reused. So on that path a codex that exits on its own is not followed by a group sweep: a descendant that outlives it is left running rather than risk killing an unrelated group. Kills (stall, cap, a signal to the runner) still sweep the whole group, while codex is still unreaped.

It always runs read-only, reads the prompt from `--prompt-file` (or stdin), and with `--changes-since <ref>` appends the change bundle itself — commits since `<ref>`, `git status`, `git diff <ref>`, and untracked file contents — without touching the index. `HEAD` means "uncommitted only"; a batch's base commit covers several commits at once. Past ~900 lines it writes the bundle to a file and tells Codex to read only what it needs, instead of inlining it.

Standard-library Python 3.9+; invoke it with `uv run --script` (no dependence on the file's executable bit surviving a plugin install).

Call it as **three plain shell commands**, never one compound command. A session pinned to a worktree (every gauntlet run with its own) refuses compound shell — variables, `$(…)`, `||` guards, heredocs — as too complex to verify, and shell variables don't survive between tool calls anyway.

1. **Locate it.** `printenv CODEX_RUN` first: point it at a checkout's `codex-run.py` to use changes that aren't installed yet (a branch before merge). If that prints nothing:

   ```bash
   find ~/.claude/plugins ~/.cursor/plugins ~/.grok/installed-plugins ~/.grok/plugins -path '*codex-cli*/scripts/codex-run.py' 2>/dev/null | xargs -r ls -t 2>/dev/null | head -n1
   ```

   Note the absolute path it prints and write it literally in the later commands (`<runner path>`). Nothing printed means codex-cli isn't installed: say so and take the fallback.
2. **Write the prompt** with the file-writing tool, to a file outside the repo — the plan's artifact folder in a gauntlet, otherwise the session's scratch directory. Not a heredoc: guards refuse them, and an unquoted one expands backticks.
3. **Run it in the background** (`run_in_background: true` or the harness equivalent), with single-quoted absolute paths:

   ```bash
   uv run --script '<runner path>' --model sol --changes-since HEAD --prompt-file '<prompt file>'
   ```

   `--prompt-file` repeats and joins in order, so a plan-panel seat passes its brief and then the plan file itself. `python3 '<runner path>'` works the same where `uv` is missing.

Tests: `python3 -m unittest discover -s plugins/codex-cli/scripts/tests -v`.

## Knowledge baked in (learned the hard way)

- **Never let Codex derive a big diff itself.** Past ~900 changed lines, a
  Codex told to review "the current changes" runs `git diff` at
  `--unified=999999`, dumps ~30k lines, and hits the 10-minute cap without a
  verdict. Write the diff to a file first — `git add -N .` (intent-to-add, so
  new files appear) then `git diff HEAD > "$(mktemp -d)/x.diff"`, which puts
  staged, unstaged, and new files in one file at a per-invocation path
  (parallel rescues are the norm here; a predictable shared `/tmp/x.diff` gets
  clobbered mid-run). Then tell it: read this file first, do NOT run
  `git diff`, then read only the named files, sections, symbols, or line
  ranges you need.
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
  the run's own `$tmpdir` in the command line, not every `codex exec`, so
  concurrent rescues survive) and rerun a fresh, narrowed prompt — that beat
  resuming every time. `echo "$tmpdir"` **before** launching `codex exec`: on a
  timeout the partial output is all you get, and without it you never learn the
  value to match.
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
- [`uv`](https://docs.astral.sh/uv/) for the runner's `uv run --script` invocation (or call it with `python3` 3.9+ instead).

Run `/codex-cli:setup` to verify both.
