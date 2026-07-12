# flutter-drive

The generic, app-agnostic layer for driving StrideLabs Marionette-instrumented
Flutter apps. Extracted from the per-app `drive-<app>` skills cloned across
slaudio-mobile, tapper, and shed-mobile.

## Skill

### `flutter-drive:flutter-drive`

Model-invoked skill for driving, debugging, and visually verifying any StrideLabs
Flutter client over the Dart VM Service via the Marionette CLI — no computer-use.
Triggers whenever you ask to run, launch, drive, operate, smoke-test, verify a UI
change in, or hunt a bug in a StrideLabs Flutter app, even when "Marionette" isn't
named.

It carries the parts that are the same across every app:

- The universal driving rules (dispatch ≠ reaction, type-then-tap races, disabled
  controls, poll MSTATE not sleeps, visible-only `get-interactive-elements`,
  hot-reload clears logs, bounded loops always).
- The `MSTATE` / `MRESULT` contract from the shared `stridelabs_drive` package.
- The standard headless dev-login pattern (`stridelabs_slauth` `HeadlessLogin` +
  `TEST_USER_*` defines from a gitignored `env/dev.local.json`).
- A checklist for bootstrapping a brand-new app's `drive-<app>` skill.

Bundled references and template:

- `references/marionette-commands.md` — the full Marionette CLI reference.
- `references/instrumenting-new-features.md` — the five app-neutral rules for
  keeping new UI drivable.
- `scripts/launch-and-connect-template.sh` — a parameterized launch-and-register
  script to copy into an app repo (edit only its CONFIG block).

## Relationship to per-app skills

Each Flutter repo still ships its own `drive-<app>` skill with that app's
preconditions, `ValueKey` map, `MSTATE`/`MRESULT` inventory, and canonical journey.
**The per-app skill wins on specifics** — this plugin is the shared rules and the
bootstrap procedure behind it, not a replacement.

## Installation

```
/plugin marketplace add charliek/cc-plugins
/plugin install flutter-drive@cc-plugins
```
