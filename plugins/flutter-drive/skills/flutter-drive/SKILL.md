---
name: flutter-drive
description: >-
  Drive, debug, and visually verify any StrideLabs Marionette-instrumented Flutter
  app (macOS/Linux desktop or Android) the way a user would — launch it, tap, type,
  scroll, screenshot, read logs and live state — via the Marionette CLI over the
  Dart VM Service. Use whenever asked to run, launch, drive, operate, or smoke-test
  a StrideLabs Flutter client; to verify a UI change in the real app; to reproduce
  or hunt a client-side bug; to manually test a screen or flow (login/onboarding and
  the app's own features); or to confirm a feature works end to end — even if
  Marionette is not named. No computer-use needed (driven over the Dart VM Service).
  Debug builds only — never works against a release build. This is the generic,
  app-agnostic layer: the per-app `drive-<app>` skill in each repo carries that
  app's key map, preconditions, and canonical journey, and WINS on any specifics.
---

# Drive a StrideLabs Marionette-instrumented Flutter app

Marionette attaches to a **debug** build's Dart VM Service and drives it like a
user. It can *see* a Flutter widget tree but doesn't *understand* any particular
app. This skill is the app-agnostic procedure and contract shared by every
StrideLabs Flutter client (slaudio-mobile, tapper, shed-mobile, …). No
accessibility or computer-use access is required — but the app must be able to
open a window: macOS desktop is the fastest, most reliable target; a Linux GTK
build needs a display (Xvfb or a Wayland session in CI — not a bare headless
container); Android needs the backend reverse-tunnelled to the device.

**The per-app skill wins on specifics.** Each repo ships a `drive-<app>` skill
(e.g. `drive-slaudio-mobile`, `drive-tapper-app`, `drive-shed-mobile`) with that
app's preconditions, `ValueKey` map, MSTATE/MRESULT inventory, and canonical
journey. When one is present, follow it for anything app-specific — this skill is
the shared rules and the bootstrap procedure behind it, not a replacement.

## When to use

- Run / launch / drive / operate / smoke-test a StrideLabs Flutter client.
- Verify a UI change in the real app (not just `flutter test`).
- Reproduce or hunt a client-side bug; manually test a screen or flow.
- Confirm a feature works end to end — even when "Marionette" is not named.

Out of scope for any app: real OAuth browser popups, native permission dialogs,
audio *playback*, and voice/mic paths — Marionette can't drive or perceive those.
Provide a debug bypass (see headless login) and verify such results out-of-band
(RSS/API/logs), not by watching or listening.

## Drive reliably — the rules that actually matter

Marionette reports success when it *dispatches* a command, NOT when the app
reacts. **Always verify the state change via MSTATE / MRESULT /
get-interactive-elements; never assume a tap or text entry worked.** These rules
are universal across every app:

- **Dispatch ≠ reaction.** A `Tapped element …` / `Entered text …` line means the
  command was sent, not that the app did anything. Confirm the effect before the
  next step.
- **Type-then-tap races.** After `enter-text`, the value may not have committed
  before a `tap` fires → the app sees an empty field and silently does nothing.
  After typing into a field, `sleep 1` and verify via
  `get-interactive-elements | grep <field-key>` (read the `text:` value) before
  tapping the submit button.
- **A disabled control is a silent no-op.** Marionette taps the coordinates
  regardless of enabled state. Submit buttons commonly disable while busy or until
  required fields are filled. Confirm the control is enabled (`onPressed` non-null,
  or the relevant MSTATE flag) before tapping — don't fight a button that can't fire.
- **Poll MSTATE, not a fixed sleep**, to know when an async step finished. Read
  `get-logs | grep MSTATE` in a loop; a bare `sleep` either wastes time or races.
- **`get-interactive-elements` returns only *visible* (hit-testable) nodes.** For
  long forms or lists, `scroll-to --key <key>` first, or screenshot to see the true
  visual state. Off-screen and mid-transition content won't appear.
- **hot-reload clears the log buffer** (and keeps the VM URI). Read logs soon after
  the action you care about; after a Dart edit, `hot-reload` then re-drive from a
  known screen — no relaunch or re-register.
- **Bounded loops, always.** Every wait/poll loop MUST have a finite bound (a
  `for i in $(seq 1 N)` cap or an iteration counter), never an unbounded
  `until … do sleep`. If the bound is hit, treat it as a stall and diagnose — do
  not loop forever. Size the bound to the work (a few seconds for a screen
  transition; many minutes for a real backend pipeline).

## Efficiency

- **Register once, drive with `-i <instance>`** — don't pass `--uri` per command.
- **`get-interactive-elements` is verbose.** Call it once after a navigation to
  learn the keys (especially id-suffixed rows like `<screen>-row-<id>`), then drive
  by `--key`. Poll `get-logs | grep MSTATE` in loops, not the element tree.
- **Target by `--key`, not `--text`** — keys are stable; text changes and collides.
- **hot-reload keeps the VM URI** — only a full restart needs `unregister` + a fresh
  `register`.

## The MSTATE / MRESULT contract (from `stridelabs_drive`)

Every StrideLabs Flutter app emits two kinds of structured, **debug-only** log
lines via the shared `stridelabs_drive` package (`logDriveState` / `logDriveResult`,
in `drive_state.dart`). Both are `kDebugMode`-gated and tree-shaken from release
builds, and both are designed to be greppable out of `get-logs`:

- **`MSTATE …`** — non-rendered screen state, emitted from `build()` **only on
  change** (deduped). One concise line per screen exposes state the widget tree
  can't show: an in-flight flag, a selection count, a mode, an id, a derived status.
  Read current state and wait on transitions with `get-logs | grep MSTATE`. Shape
  is app-defined, e.g. `MSTATE screen=<name> …` / `MSTATE layout=… section=…`.
- **`MRESULT <action> ok|error=…`** — the outcome of a create/update/delete/validate
  whose only UI is a transient SnackBar. Emitted once when the action resolves;
  survives the SnackBar auto-dismissing. Confirm mutations with
  `get-logs | grep MRESULT`. Action names follow a `<noun>-<verb>` convention
  (`collection-create`, `feed-validate`, `podcast-generate`, `settings-save`, …).

```bash
marionette -i <instance> get-logs | grep -E 'MSTATE|MRESULT' | tail -1
```

The per-app skill lists that app's exact MSTATE lines and MRESULT action names.

## Headless login (skip the OAuth browser) — the standard pattern

Every app that requires auth exposes a **debug-only dev sign-in** so an agent can
authenticate without a system browser. This is now standard across StrideLabs
Flutter clients and looks the same everywhere:

- A **`login-dev-sign-in`** button renders **only** when
  `kDebugMode && DEV_AUTH && TEST_USER_EMAIL/PASSWORD are set`. Tapping it runs the
  shared `stridelabs_slauth` **`HeadlessLogin`** (Kratos password → PKCE → Hydra
  tokens for the app's OAuth client) — a *real* login minting real tokens, no
  browser. Never tap the real OAuth button (`login-sign-in-button` or similar) — it
  opens a system browser and is not agent-drivable.
- The `TEST_USER_EMAIL` / `TEST_USER_PASSWORD` come from a **gitignored
  `env/dev.local.json`** dart-define file (copy the repo's `dev.local.json.example`
  and fill from the test user in `../slauth/test-users.md`). `DEV_AUTH: true` lives
  in the checked-in `env/dev.json` and gates the button's *visibility*. Both define
  files must be passed at launch, or the dev-login button won't appear.

```bash
M="marionette -i <instance>"
$M tap --key login-dev-sign-in
for i in $(seq 1 30); do $M get-logs | grep -q 'MRESULT login' && break; sleep 1; done
$M get-logs | grep -E 'MRESULT login' | tail -1   # ok → proceed; error=… → diagnose
$M get-logs | grep -E 'MSTATE' | tail -2          # where did we land? (shell vs onboarding)
```

If `login-dev-sign-in` is absent: launched without `env/dev.local.json` (no
`TEST_USER_*`), `DEV_AUTH` off, or not a debug build. If it taps but
`MRESULT login error=…` / a `login-error` widget shows: local slauth isn't running,
the test user lacks a grant for this app, or the creds are wrong.

## Launch + connect

Each repo ships a `scripts/launch-and-connect.sh` (its own copy of the template in
this plugin's `scripts/launch-and-connect-template.sh`). It launches the debug
build with the app's dart-define files, parses the `http://127.0.0.1:PORT/TOKEN/`
"Dart VM Service" line, converts it to `ws://…/ws`, and registers a named instance,
leaving `flutter run` alive for driving.

```bash
.claude/skills/drive-<app>/scripts/launch-and-connect.sh macos    # or: linux | android
```

By hand: `flutter run -d macos --dart-define-from-file=env/dev.json --dart-define-from-file=env/dev.local.json`,
take the "Dart VM Service" line, convert `http://…/` → `ws://…/ws`,
`marionette register <instance> <ws>`.

Every Marionette command/flag is in `references/marionette-commands.md`.

## When something fails

- `marionette doctor` checks connectivity; `marionette unregister <instance>` + a
  fresh `register` recovers a stale instance after a restart.
- `get-interactive-elements` returns 0 → app mid-transition or crashed; screenshot,
  then relaunch (kill the `flutter run` PID, re-run the launch script).
- A long poll loop hits its bound → treat it as a stall, not a pass: screenshot,
  read the latest `MSTATE`/`MRESULT` and the `flutter run` log, and check the
  backend. A backend/pipeline *failure* surfaced in the app (a `Failed` status, a
  keyed error widget) is still a **successful drive** — report it, don't fight it.

Cleanup: kill the `flutter run` PID the script printed, then
`marionette unregister <instance>`.

## Instrumenting new features so they stay drivable

When you add or change UI, make it drivable in the same change: a stable `ValueKey`
on every control, and `logDriveState` / `logDriveResult` (from `stridelabs_drive`)
for state the tree can't show. The full app-neutral checklist is in
**`references/instrumenting-new-features.md`** — read it before adding screens,
dialogs, or stateful flows, and document new keys in the per-app skill's key map.

## Bootstrapping a NEW app's drive skill

To make a fresh StrideLabs Flutter app drivable and give it its own `drive-<app>`
skill, work this checklist:

1. **Adopt the shared packages.** Add `stridelabs_drive` (the `logDriveState` /
   `logDriveResult` helpers + `MSTATE`/`MRESULT` contract) and, if the app has auth,
   `stridelabs_slauth` (the `HeadlessLogin` dev sign-in) to `pubspec.yaml`.
2. **Wire the headless dev login.** Render a `login-dev-sign-in` button gated on
   `kDebugMode && DEV_AUTH && TEST_USER_*`, calling `stridelabs_slauth`'s
   `HeadlessLogin`. Put `DEV_AUTH: true` in `env/dev.json`; put `TEST_USER_EMAIL` /
   `TEST_USER_PASSWORD` in a gitignored `env/dev.local.json` (ship a
   `dev.local.json.example`). Emit `MRESULT login ok|error=…`.
3. **Instrument keys + state per the reference.** Follow
   `references/instrumenting-new-features.md`: `ValueKey` every interactive element,
   emit one `MSTATE` line per screen, and `logDriveResult` every mutation.
4. **Copy the launch-script template.** Copy this plugin's
   `scripts/launch-and-connect-template.sh` into the repo as
   `.claude/skills/drive-<app>/scripts/launch-and-connect.sh` and fill in the
   `APP_DIR`, `INSTANCE`, device list, dart-define files, and (Android) the
   adb-reverse port.
5. **Write the per-app skill.** Create `.claude/skills/drive-<app>/SKILL.md` with
   the app's preconditions (backend/slauth/test-user), its `ValueKey` map + exact
   MSTATE/MRESULT inventory (a `references/<app>-context.md` or `screen-key-map.md`),
   and its canonical journey. Reference this generic layer for the universal rules;
   copy `references/marionette-commands.md` and
   `references/instrumenting-new-features.md` alongside it.
6. **Validate end to end.** Launch, headless-login, drive the canonical journey,
   confirm your new keys appear in `get-interactive-elements` and the flow's
   `MSTATE`/`MRESULT` lines fire, then `flutter analyze` + `flutter test`.
