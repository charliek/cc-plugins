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
| [flutter-drive](plugins/flutter-drive/) | Skill | `flutter-drive:flutter-drive` — drive/debug/verify any StrideLabs Marionette-instrumented Flutter app over the Dart VM Service |
| [flows](plugins/flows/) | Commands | `/flows:gauntlet` and `/flows:gated-commit` for end-to-end build flows (plan → panel review → gated commits → PR) |

## Installation

```
/plugin marketplace add charliek/cc-plugins
/plugin install git-commands@cc-plugins
/plugin install release-workflows@cc-plugins
/plugin install deploy@cc-plugins
/plugin install planning@cc-plugins
/plugin install cursor@cc-plugins
/plugin install flutter-drive@cc-plugins
/plugin install flows@cc-plugins
```

## Adding new plugins

1. Create a directory under `plugins/<name>/`
2. Add `.claude-plugin/plugin.json` with name, description, and author
3. Add `commands/` for slash commands or `skills/` for model-invoked skills
4. Register in `.claude-plugin/marketplace.json`
