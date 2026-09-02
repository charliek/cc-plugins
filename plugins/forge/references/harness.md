# Forge harness table

Shared by every forge skill. Read this before spawning anything.

## Reference resolution

When a skill says "read `references/<file>`", resolve in this order and stop at the first hit:

1. `${CLAUDE_PLUGIN_ROOT}/references/<file>` if that variable was substituted
2. `../../references/<file>` relative to the SKILL.md's own absolute path
3. Search `~/.cursor/plugins/{local,cache}/**/forge/references/<file>`,
   `~/.grok/plugins/**/forge/references/<file>`,
   `~/.claude/plugins/**/forge/references/<file>`

If unresolvable, stop and report. If `${CLAUDE_PLUGIN_ROOT}` appears unsubstituted, ignore it and continue the list.

## Arguments

`$ARGUMENTS` is the text after the slash command. If that token appears unsubstituted, treat the text the user typed after the slash command as the brief. `--harness gx|cursor|claude` in the arguments overrides detection.

## Spawn availability

If the spawn tool (`task` / `Task` / `Agent` / `spawn_subagent`) is unavailable — typically because this skill was invoked inside a subagent — stop and tell the parent to run the skill. Never attempt the flow without subagents. gx forbids nested spawns.

## Detection (in order)

1. **Cursor** — spawn tool is `Task` and `subagent_type` values are camelCase (`generalPurpose`, `explore`) and/or the question tool is `AskQuestion`.
2. **gx** — spawn tool is `task` or `spawn_subagent` with kebab types (`general-purpose`, `explore`, `plan`) and `run_in_background` defaults true.
3. **Claude Code** — spawn tool is `Agent` (or `Task`) with `general-purpose` and the question tool is `AskUserQuestion`.

If none match, ask once via the question tool, then proceed.

## Three-tier execution (from `flows:gauntlet`)

Fable-class orchestrates and implements only the single most critical/complex piece, if any. Opus-class does complex/subtle units. Sonnet-class does routine/mechanical work and simplify. Never put simplify on the fable-class model. Never use a Cursor `…-fast` slug for any subagent.

| Role | Claude Code | gx | Cursor |
|---|---|---|---|
| Fable-class — orchestrator; implements only the single most critical piece | `fable` | `fireworks/kimi-k3` | `claude-opus-5-thinking-high` |
| Opus-class — complex/subtle implementation | `opus` | `grok-4.6` | `cursor-grok-4.6-high` |
| Sonnet-class — routine implementation, explore, simplify reviewers + fixer | `sonnet` | `glm-5.3` | `composer-2.5` |
| Correctness reviewer (Sol-first, read-only) | `codex exec -m gpt-5.6-sol -c model_reasoning_effort=high -s read-only` | `gpt-5.6-sol` explore subagent | `gpt-5.6-sol-high` explore subagent |
| Reviewer fallback | `cursor:cursor-rescue` read-only → self-review | `grok-4.6` → self-review | `cursor-grok-4.6-high` → self-review |
| Plan panel seats | `codex exec` (Sol), `opencode run` (GLM), `coderabbit:code-reviewer` | `gpt-5.6-sol`, `grok-4.6`, `glm-5.3` subagents | `gpt-5.6-sol-high`, `cursor-grok-4.6-high`, `gemini-3.7-flash-high` |

This table is the user's direct request for per-role models — always pass `model` on spawn. Prefix each subagent `description` with the model actually used, e.g. `(grok-4.6) Implement U2`.

## Spawn recipes

**Writable** (implementers, simplify fixer): type `general-purpose` / `generalPurpose`. Omit `isolation` (shared workspace; parent must see the edits).

**Read-only** (reviewers, panel seats): type `explore`. Paste the material to review inline in the prompt (full plan text; `git diff` / `git diff --cached` / untracked file contents). gx `explore` has read/list/search only — no shell — so never ask it to discover the diff itself.

**Sequential** (implementer, fixer, Sol reviewer): `run_in_background: false`, or spawn then immediately wait on the task-output tool. Do not proceed until it finishes.

**Parallel** (panel seats, simplify reviewers): `run_in_background: true`, then batch-wait with the task-output tool (`get_task_output` / `get_command_or_subagent_output` / `AwaitShell` equivalent) before synthesis.

**10-minute reviewer cap:** wait up to 10 minutes, then kill via `kill_task` / `kill_command_or_subagent` / `TaskStop` (or the harness equivalent). A killed or empty review is a failure, never "no findings", and triggers the fallback.

**gx `run_in_background` defaults true.** Always set it explicitly.

**If Cursor `Task` rejects a slug** (including `cursor-grok-4.6-high`): do not retry with `…-fast`. Report the spawn failure and use the next role fallback (self-review for a reviewer; stop and ask for an implementer).

## Sol-first contract

Correctness review is Sol-first, not Sol-only. Fallbacks only on auth failure, credit/rate limit, empty output, or cap kill. Record the reviewer that actually ran in the commit message, e.g. `review: gpt-5.6-sol` or `review: grok-4.6 (Sol 401)`. If every route fails, self-review, say so in the commit message, and surface it in the final status — never commit silently unreviewed.

**OpenRouter Sol is never auto-selected.** `openrouter/gpt-5.6-sol` (and terra/luna twins) are metered. ChatGPT-plan `gpt-5.6-sol` is the only Sol gx may spawn. Use an OpenRouter Sol id only when the human explicitly says it is OK for this run.

gx Sol effort is not settable per spawn. Recommend `[model."gpt-5.6-sol"].reasoning_effort = "high"` in `~/.grok/providers.toml`, then restart gx.

## Plans directory

**Write:** Cursor `~/.cursor/plans/<repo>/NNN-<slug>.md`; gx and Claude Code `~/.claude/plans/<repo>/NNN-<slug>.md`. Artifacts in the sibling `NNN-<slug>/`. A repo CLAUDE.md or AGENTS.md in-repo convention overrides this.

**Read** (ask-panel, gauntlet resume): explicit path first; otherwise search both trees that are readable and take the newest match, reporting which.

## Panel quorum

"Panel-reviewed" requires ≥ 2 successful seats. With 1, record `degraded panel (1/3)` in the plan header and tell the user before implementation proceeds. A failed seat is reported with reason, never retried on the same quota, never silently dropped.
