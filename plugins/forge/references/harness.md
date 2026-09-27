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

If the spawn tool (`task` / `Task` / `Agent` / `spawn_subagent`) is unavailable
(typically because this skill was invoked inside a subagent):

Detect the harness first (`--harness` override, then Detection below). Tool
names and the question-tool identity remain usable even when spawn is blocked.

- **gx and Cursor:** stop and tell the parent to run the skill. Never attempt
  those harnesses without subagents. gx forbids nested spawns.
- **Claude Code:** the shell-only parts still work — the codex runner (the
  gated-commit review and the astra panel seat) and `opencode run` (the GLM
  seat). The CodeRabbit
  panel seat and the `cursor-rescue` review fallback are subagents: skip
  them and say so. Stop if the work needs implementers or simplify.
- **Uncertain:** fail closed. Do not infer Claude Code from `codex` or
  `opencode` on PATH — gx and Cursor sessions often have those CLIs too. Ask
  once, or require `--harness claude`.

## Detection (in order)

`--harness gx|cursor|claude` in the arguments overrides this list.

1. **Cursor** — `subagent_type` values include camelCase `generalPurpose`, and/or the question tool is `AskQuestion` (not `AskUserQuestion`).
2. **gx** — built-in types include kebab `general-purpose` **and** kebab `plan`, and/or the spawn tool's aliases include `spawn_subagent`. The advertised name may be `task` or `Task`; do not treat `Task` alone as Cursor. Stock `grok` detects the same way; the one difference that matters is that it never has GPT models, so its Codex seats go through the runner (see the tables).
3. **Claude Code** — the spawn tool is `Agent`, and/or the question tool is `AskUserQuestion`.

If none match, ask once via the question tool, then proceed.

## Three-tier execution (from `flows:gauntlet`)

Fable-class orchestrates and implements only the single most critical/complex piece, if any. Opus-class does complex/subtle units. Sonnet-class does routine/mechanical work and simplify. Never put simplify on the fable-class model. Never use a Cursor `…-fast` slug for any subagent.

| Role | Claude Code | gx | Cursor |
|---|---|---|---|
| Fable-class — orchestrator; implements only the single most critical piece | `fable` | `fireworks/kimi-k3` | `claude-opus-5-thinking-high` |
| Opus-class — complex/subtle implementation | `opus` | `grok-4.7` | `grok-4.7-high` |
| Sonnet-class — routine implementation, explore, simplify reviewers + fixer | `sonnet` | `glm-5.3` | `composer-2.5` |
| Codex reviewer (read-only; `sol` or `astra` per unit) | codex runner `--model sol\|astra` | `gpt-6-sol` / `gpt-6-astra` explore subagent (stock grok: the runner) | codex runner, from the orchestrator's shell |
| Reviewer fallback (one) | `cursor:cursor-rescue` read-only (Grok 4.7), or the CodeRabbit CLI if Cursor is unavailable; else self-review | `grok-4.7` explore; else self-review | `grok-4.7-high` explore; else self-review |
| Plan panel seats | codex runner `--model astra`, `opencode run` (GLM), `coderabbit:code-reviewer` | `gpt-6-astra`, `grok-4.7`, `glm-5.3` subagents (stock grok: runner for the astra seat) | codex runner `--model astra` (shell), `grok-4.7-high`, `gemini-3.7-flash-high` subagents |

This table is the user's direct request for per-role models — always pass `model` on spawn. Prefix each subagent `description` with the model actually used, e.g. `(grok-4.7) Implement U2`; label runner calls the same way, e.g. `(gpt-6-sol) Review U2`.

Cursor never gets an OpenAI model as a subagent: OpenAI models are leaving Cursor and were costly on this plan. Its Codex seats run through the codex CLI on the ChatGPT plan instead, the same way Claude Code's do.

## Spawn recipes

**Writable** (implementers, simplify fixer): type `general-purpose` / `generalPurpose`. Omit `isolation` for sequential work (shared workspace; parent must see the edits). Parallel implementers are the exception — never two in one tree; gauntlet Phase 4 has the per-harness isolation rule.

**Read-only** (reviewers, panel seats): type `explore`. Paste the material to review inline in the prompt (full plan text; the `--bundle-only` change bundle from §Codex runner). A large bundle comes back from `--bundle-only` as a file path plus reading instructions — pass that through as-is: `explore` has read tools, and pasting tens of thousands of diff lines is exactly what the file form avoids. Only if the reviewer's read tool cannot reach that path, paste the file's contents instead. gx `explore` has read/list/search only — no shell — so never ask it to discover the diff itself.

**Sequential** (implementer, fixer): `run_in_background: false`, or spawn then immediately wait on the task-output tool. Do not proceed until it finishes. **Reviewers** are sequential too — nothing proceeds until the review is back — but spawn them with `run_in_background: true` and wait in 10-minute slices, so the progress checks and caps below can happen; launch a runner call in the background for the same reason (it also outlives one shell call).

**Parallel** (panel seats, simplify reviewers): `run_in_background: true`, then batch-wait with the task-output tool (`get_task_output` / `get_command_or_subagent_output` / `AwaitShell` equivalent) before synthesis.

**Reviewer caps: 20 minutes, 25 for astra, with a progress check every 10.** The codex runner enforces this itself. For reviewer and panel-seat *subagents*, do it by hand: at each 10-minute mark, confirm the subagent is still producing (new tool calls or output since the last check); kill a flat one early rather than waiting out the cap, and kill at the cap regardless, via `kill_task` / `kill_command_or_subagent` / `TaskStop` (or the harness equivalent). A killed or empty review is a failure, never "no findings", and triggers the fallback.

**gx `run_in_background` defaults true.** Always set it explicitly.

**If Cursor `Task` rejects a slug** (including `grok-4.7-high`): do not retry with `…-fast`. Report the spawn failure and use the next role fallback (self-review for a reviewer; stop and ask for an implementer).

## Codex runner

`scripts/codex-run.py` in the **codex-cli** plugin is the one way forge shells out to Codex (Claude Code, Cursor, and stock grok; gx too when its native GPT-6 seat is unavailable). It is read-only; caps sol at 20 minutes and astra at 25; checks every 10 minutes that Codex's output is still growing and kills a flat run early; kills the whole process tree on every exit path; and with `--changes-since <ref>` appends the change bundle itself (commits since `<ref>`, status, diff, untracked files — a diff *file* past ~900 lines). Install the codex-cli plugin on every harness forge runs on — even gx uses it, for `--bundle-only` and as the fallback route. 

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

Exit `0` prints the review on stdout. Anything else is "no review": `3` failed, `4` empty, `5` stalled, `6` capped, `7` usage limit / rate limit / capacity (never retry codex — same quota), `8` auth, `9` codex missing.

`--changes-since <ref> --bundle-only` prints the same change bundle without running codex, for reviewers that aren't codex (native subagents, fallbacks, simplify); `<ref>` is `HEAD` for uncommitted changes. If codex-cli isn't installed, say so and build the bundle by hand from the repo root with plain commands: `git log --oneline <ref>..HEAD`, `git status --short --untracked-files=all`, `git diff-index -p -M --textconv <ref>`, and the untracked files' contents — as a file once it passes ~900 lines.

## Codex-first review contract

Correctness review is Codex-first, not Codex-only, and tiered like implementation: **`gpt-6-sol`** for routine units, **`gpt-6-astra`** for units that are complex or subtle (the opus/fable bar) or touch concurrency/ordering, data integrity, auth/security, money, migrations, or wire protocols. The plan's `review` mark decides; `plan.md` defines it. Fall back only when the Codex route fails (non-zero runner exit, spawn/auth failure, empty, stalled, or capped) — **one** fallback per review, per the table. Record the reviewer that actually ran in the commit message, e.g. `review: gpt-6-sol`, `review: gpt-6-astra (covers U3–U5)`, or `review: grok-4.7 (codex usage limit)`. If every route fails, self-review, say so in the commit message, and surface it in the final status — never commit silently unreviewed.

**OpenRouter GPT models are never auto-selected.** `openrouter/gpt-*` ids (any `gpt-6-*` or `gpt-5.6-*` twin) are metered. On gx, spawn only the ChatGPT-plan `gpt-6-sol` / `gpt-6-astra`; use an OpenRouter id only when the human explicitly says it is OK for this run.

**gx native seats.** gx cannot set reasoning effort per spawn, so pin it per model in `~/.grok/providers.toml` and restart gx:

```toml
[model."gpt-6-sol"]
reasoning_effort = "high"

[model."gpt-6-astra"]
reasoning_effort = "high"
```

gx ships a `gpt-6-astra` preset; `gpt-6-sol` arrives with charliek/grok-build#21. Until a gx build lists it, or on stock grok (no GPT models at all), a rejected `gpt-6-*` spawn is not a failed review: run the same review through the codex runner from the orchestrator's shell instead.

## Plans directory

**Write:** Cursor `~/.cursor/plans/<repo>/NNN-<slug>.md`; gx and Claude Code
`~/.claude/plans/<repo>/NNN-<slug>.md`. Next free `NNN`. Artifacts in the sibling
`NNN-<slug>/`. A repo CLAUDE.md or AGENTS.md in-repo convention overrides this.

**Multi-repo key:** one plan file, not one per repo. Write it under the
**primary** repo: the first repo named in the brief, else the current working
directory's repo. All workstreams and per-repo breakdowns live in that file;
artifacts stay in that plan's sibling folder. Resume and ask-panel look up that
same path. Each PR body links it.

**Read** (ask-panel, gauntlet resume): explicit path first; otherwise search both
trees that are readable and take the newest match, reporting which.

## Panel quorum

"Panel-reviewed" requires ≥ 2 successful seats. A failed seat is reported with
reason, never retried on the same quota, never silently dropped.

- **0/3** seats ran or succeeded: the plan is **not** panel-reviewed. Do not
  substitute a self-review as a pass. Stop before implementation (gauntlet) or
  report failure (`ask-panel`).
- **1/3:** record `degraded panel (1/3)` in the plan header and tell the user
  before implementation proceeds.
- **≥ 2/3:** panel-reviewed.
