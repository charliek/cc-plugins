# cc-plugins

Shared Claude Code plugins for development workflows.

## Plugins

| Plugin | Type | Description |
|--------|------|-------------|
| [git-commands](plugins/git-commands/) | Commands | `/watch-pr` and `/merge-pr` for PR CI monitoring and merging |
| [release-workflows](plugins/release-workflows/) | Commands | `/release-workflows:release` and `/release-workflows:setup` for convention-based semver releases (update-version.sh, release.yml, release-bot App) |
| [deploy](plugins/deploy/) | Commands | `/deploy:build` for date-based releases that trigger Docker builds |
| [planning](plugins/planning/) | Commands | `/planning:ask-codex`, `/planning:ask-glm`, `/planning:ask-coderabbit`, `/planning:ask-panel` for AI-powered plan review |
| [cursor](plugins/cursor/) | Commands | `/cursor:rescue`, `/cursor:review`, `/cursor:adversarial-review` — delegate coding tasks and reviews to the Cursor agent CLI |
| [codex-cli](plugins/codex-cli/) | Commands | `/codex-cli:rescue`, `/codex-cli:review`, `/codex-cli:adversarial-review` — delegate coding tasks and reviews directly to `codex exec` (brokerless, parallel-safe) |
| [grok](plugins/grok/) | Commands | `/grok:rescue` — delegate coding tasks to the Grok CLI (`grok -p`, brokerless, parallel-safe) |
| [flutter-drive](plugins/flutter-drive/) | Skill | `flutter-drive:flutter-drive` — drive/debug/verify any StrideLabs Marionette-instrumented Flutter app over the Dart VM Service |
| [flows](plugins/flows/) | Commands | `/flows:gauntlet` and `/flows:gated-commit` for end-to-end build flows (plan → panel review → gated commits → PR) |
| [docs-workflows](plugins/docs-workflows/) | Skills | `docs-workflows:docs-setup` and `docs-workflows:docs-migrate` — stand up a Zensical docs site, or port one from Material for MkDocs |
| [forge](plugins/forge/) | Skills (slash-only) | `/forge:gauntlet`, `/forge:gated-commit`, `/forge:simplify`, `/forge:ask-panel` — plan → PR flow for gx, Cursor, and Claude Code |

## Installation

```
/plugin marketplace add charliek/cc-plugins
/plugin install git-commands@cc-plugins
/plugin install release-workflows@cc-plugins
/plugin install deploy@cc-plugins
/plugin install planning@cc-plugins
/plugin install cursor@cc-plugins
/plugin install codex-cli@cc-plugins
/plugin install grok@cc-plugins
/plugin install flutter-drive@cc-plugins
/plugin install flows@cc-plugins
/plugin install docs-workflows@cc-plugins
/plugin install forge@cc-plugins
```

gx:

```
gx plugin marketplace add charliek/cc-plugins
gx plugin install forge --trust
```

Cursor: install `forge` from the cc-plugins marketplace, or symlink
`plugins/forge` to `~/.cursor/plugins/local/forge` and reload.

## Adding new plugins

1. Create a directory under `plugins/<name>/`
2. Add `.claude-plugin/plugin.json` with name, description, and author
3. Add `commands/` for slash commands or `skills/` for skills. Skills may be
   slash-only (`disable-model-invocation: true`); they are not required to be
   model-invoked.
4. Register in `.claude-plugin/marketplace.json`
