# forge

Cross-harness plan → PR flow for **gx**, **Cursor**, and **Claude Code**. Prefer
forge over `flows` / `planning` when both are installed (`/forge:gauntlet`
instead of `/flows:gauntlet`). Those plugins stay unchanged for Claude Code
sessions that still want them.

## Skills (slash-only)

Model invocation is disabled; run them as slash commands.

### `/forge:ask-panel [--harness gx|cursor|claude] [plan-file-path]`

Three-seat plan review. gx and Cursor spawn native `explore` subagents
(Sol + Grok + GLM or Gemini). Claude Code keeps the existing shell-outs
(Codex Sol, opencode GLM, CodeRabbit). Findings are synthesized and written
back into the plan. "Panel-reviewed" needs ≥ 2 successful seats.

### `/forge:simplify [scope]`

Three parallel sonnet-class reviewers (quality / performance / reuse) then
one fixer. Raised bar: skip tiny, deletion, move, config, and docs-only
diffs. Never runs on the fable-class model.

### `/forge:gated-commit [scope notes]`

Per-unit inner loop: repo gate → conditional simplify → Sol-first
correctness review (10-minute cap, then kill) → dispositions → one commit.
Does not push.

### `/forge:gauntlet <scope brief>`

Full plan → panel → standalone gated units → verification record → one PR
per repo, watched to green. Default: leave the PR open. Never release/deploy
unless the brief says so.

## Three-tier models

Same rule as `flows:gauntlet`, mapped per harness. The session model
orchestrates; implementation runs in subagents. Fable-class implements only
the single most critical piece, if any.

| Role | Claude Code | gx | Cursor |
|---|---|---|---|
| Fable-class | `fable` | `fireworks/kimi-k3` | `claude-opus-5-thinking-high` |
| Opus-class | `opus` | `grok-4.6` | `cursor-grok-4.6-high` |
| Sonnet-class | `sonnet` | `glm-5.3` | `composer-2.5` |
| Review (Sol-first) | `codex exec` Sol | `gpt-5.6-sol` subagent | `gpt-5.6-sol-high` subagent |
| Review fallback | `cursor:cursor-rescue` → self-review | `grok-4.6` → self-review | `cursor-grok-4.6-high` → self-review |
| Plan panel | Codex Sol, opencode GLM, CodeRabbit | Sol, Grok, GLM subagents | Sol, Grok, Gemini subagents |

Never auto-select OpenRouter Sol (`openrouter/gpt-5.6-sol` and twins) — those
are metered. Use ChatGPT-plan `gpt-5.6-sol` only, unless the human opts in.
Never use Cursor `…-fast` slugs for subagents.

gx Sol effort is not settable per spawn. Pin it in user config, then restart:

```toml
# ~/.grok/providers.toml
[model."gpt-5.6-sol"]
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
falling back to `gh`. Claude Code review uses `codex` CLI and, on fallback,
`cursor` (`cursor-rescue`). Missing plugins degrade with a note.
