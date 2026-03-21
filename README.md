# claude-plugins

Shared Claude Code plugins for development workflows.

## Plugins

| Plugin | Type | Description |
|--------|------|-------------|
| [git-commands](plugins/git-commands/) | Commands | `/watch-pr` and `/merge-pr` for PR CI monitoring and merging |
| [prox](plugins/prox/) | Skill | Guidance for the prox process manager — process management, logs, proxy routing |

## Installation

```bash
# Add as a marketplace
claude plugins marketplace add github:<owner>/claude-plugins

# Install individual plugins
claude plugins install git-commands
claude plugins install prox
```

## Adding new plugins

1. Create a directory under `plugins/<name>/`
2. Add `.claude-plugin/plugin.json` with name, description, and author
3. Add `commands/` for slash commands or `skills/` for model-invoked skills
4. Register in `.claude-plugin/marketplace.json`
