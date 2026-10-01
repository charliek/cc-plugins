# forge

Cross-harness plan → PR flow for **gx**, **Cursor**, and **Claude Code**. Prefer
forge over `flows` / `planning` when both are installed (`/forge:gauntlet`
instead of `/flows:gauntlet`). Those plugins stay unchanged for Claude Code
sessions that still want them.

## Skills (slash-only)

Model invocation is disabled; run them as slash commands.

### `/forge:ask-panel [--harness gx|cursor|claude] [plan-file-path | scope brief]`

Author a standalone plan (if none exists) and/or run a three-seat panel.
The OpenAI seat is always `gpt-6-astra`: a native subagent on gx, the
codex-cli runner on Claude Code and Cursor. The other seats are Grok 4.7 plus
GLM (gx), Gemini (Cursor), or opencode GLM and CodeRabbit (Claude Code).
Findings are written back into the plan. The file is gauntlet-ready: same
house style and write path. "Panel-reviewed" needs ≥ 2 successful seats.

### `/forge:simplify [scope]`

Three parallel sonnet-class reviewers (quality / performance / reuse) then
one fixer. A judgment call, not a fixed step: it pays off on core interfaces
and lots of new logic, and plans mark which units get it. Never runs on the
fable-class model.

### `/forge:gated-commit [scope notes]`

Per-unit inner loop: repo gate → simplify when it earns its cost → Codex
correctness review, `gpt-6.1-sol` for routine work and `gpt-6-astra` for
complex or high-gravity work (20/25-minute caps, progress checked every 10
minutes), per unit or shared by a batch of small units → dispositions → one
commit. Docs-only diffs skip simplify and the review and say so in the
message; big diffs reach the reviewer as a diff *file*. Does not push.
Details in `references/gated-commit.md`.

### `/forge:gauntlet <scope brief>`

Full plan → panel → **pause** (executor recommendation, kickoff prompt,
merge policy recorded in the plan) → gated milestone units → verification
record → one PR per repo, watched to green. Pass the plan file to resume at
execution. Merges only when the recorded policy says so. Never
release/deploy unless the brief says so.

## Three-tier models

Same rule as `flows:gauntlet`, mapped per harness. The session model
orchestrates; implementation runs in subagents. Fable-class implements only
the single most critical piece, if any.

| Role | Claude Code | gx | Cursor |
|---|---|---|---|
| Fable-class | `fable` | `fireworks/kimi-k3` | `claude-opus-5-thinking-high` |
| Opus-class | `opus` | `grok-4.7` | `grok-4.7-high` |
| Sonnet-class | `sonnet` | `glm-5.3` | `composer-2.5` |
| Review (sol / astra) | codex-cli runner | `gpt-6.1-sol` / `gpt-6-astra` subagent | codex-cli runner |
| Review fallback (one) | `cursor:cursor-rescue` (Grok 4.7), or CodeRabbit CLI if Cursor is unavailable; else self | `grok-4.7`; else self | `grok-4.7-high`; else self |
| Plan panel | runner astra, opencode GLM, CodeRabbit | astra, Grok, GLM subagents | runner astra, Grok, Gemini subagents |

Codex review and the astra panel seat go through the **codex-cli** plugin's
supervised runner (`scripts/codex-run.py`) wherever forge shells out — Claude
Code, Cursor, and stock grok (which has no GPT models). Install codex-cli on
every harness forge runs on. Cursor never gets an OpenAI subagent: OpenAI
models are leaving Cursor and were costly on this plan.

Never auto-select OpenRouter GPT ids (`openrouter/gpt-*`) — they are metered.
Use the ChatGPT-plan ids only, unless the human opts in. Never use Cursor
`…-fast` slugs for subagents.

gx effort is not settable per spawn. Pin it per model in user config, then
restart (`gpt-6.1-sol` needs a gx build with its preset — charliek/grok-build#21;
until then the runner covers the sol seat):

```toml
# ~/.grok/providers.toml
[model."gpt-6.1-sol"]
reasoning_effort = "high"

[model."gpt-6-astra"]
reasoning_effort = "high"
```

## Install

Claude Code:

```
/plugin marketplace add charliek/cc-plugins
/plugin install forge@cc-plugins
```

gx (also accepts `grok plugin …` on stock grok):

```
gx plugin marketplace add charliek/cc-plugins
gx plugin install forge --trust
```

Local checkout:

```
gx plugin install /path/to/cc-plugins/plugins/forge --trust
```

Cursor: install from the cc-plugins marketplace, or for development:

```
ln -s /path/to/cc-plugins/plugins/forge ~/.cursor/plugins/local/forge
```

then reload the window.

## Repo conventions

Same as `flows`: the per-commit gate comes from CLAUDE.md, then AGENTS.md,
then derived tooling. Plans default to `~/.cursor/plans/<repo>/` on Cursor
and `~/.claude/plans/<repo>/` on gx and Claude Code. A repo that documents
an in-repo plans directory wins.

## Cross-plugin dependencies

`gauntlet` uses `git-commands` (`watch-pr`, `merge-pr`) when installed,
falling back to `gh`. Review and the astra panel seat use the `codex-cli`
plugin's runner (and the `codex` CLI); Claude Code's fallback uses `cursor`
(`cursor-rescue`). Missing plugins degrade with a note.
