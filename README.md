# cc-plugins

Shared Claude Code plugins for development workflows.

## Plugins

| Plugin | Type | Description |
|--------|------|-------------|
| [git-commands](plugins/git-commands/) | Commands | `/watch-pr` and `/merge-pr` for PR CI monitoring and merging |
| [prox](plugins/prox/) | Skill | Guidance for the prox process manager — process management, logs, proxy routing |
| [release](plugins/release/) | Commands | `/release:release` for semver software releases with GoReleaser |
| [deploy](plugins/deploy/) | Commands | `/deploy:build` for date-based releases that trigger Docker builds |

## Installation

```
/plugin marketplace add charliek/cc-plugins
/plugin install git-commands@cc-plugins
/plugin install prox@cc-plugins
/plugin install release@cc-plugins
/plugin install deploy@cc-plugins
```

## Adding new plugins

1. Create a directory under `plugins/<name>/`
2. Add `.claude-plugin/plugin.json` with name, description, and author
3. Add `commands/` for slash commands or `skills/` for model-invoked skills
4. Register in `.claude-plugin/marketplace.json`
