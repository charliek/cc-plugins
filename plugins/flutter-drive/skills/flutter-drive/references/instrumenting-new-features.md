# Instrumenting new features so they stay agent-drivable

When you add or change UI, make it drivable in the *same* change. Marionette (and
CI integration tests later) can only drive what's targetable and verifiable. Five
rules, in priority order. This is the app-neutral checklist — the per-app skill's
key map is where you record the concrete keys you add.

## 1. Key every interactive element

Add a `ValueKey('<screen>-<element>')` (kebab-case) to anything an agent taps,
types into, or selects: buttons, text fields, list rows, chips, toggles,
switches, checkboxes, dropdowns, dialog actions, sheet items, menu items.
Id-suffix anything that repeats: `<screen>-row-<id>`, `<list>-item-<id>`,
`<action>-chip-<i>`, `<thing>-option-<name>`.

- **Built-in Material widgets** (`FilledButton`, `ElevatedButton`, `OutlinedButton`,
  `TextButton`, `IconButton`, `FloatingActionButton`, `TextField`, `Switch`,
  `Checkbox`, `Radio`, `ChoiceChip`, `FilterChip`, `InputChip`,
  `DropdownButtonFormField`, `SegmentedButton`, `Slider`, `Text`) are auto-detected
  by Marionette — but **add a key anyway** when more than one of the same type is on
  screen (two unkeyed `IconButton`s are indistinguishable) or matching by text/type
  is ambiguous.
- **Custom interactive widgets** are invisible to Marionette unless they wrap a
  built-in or carry a key. Key them.
- **Dialog / sheet buttons** with generic labels ("Cancel", "Save", "Delete", "Add")
  repeat across dialogs — key each (`<dialog>-cancel`, `<dialog>-save`) so they're
  unambiguous even though only one dialog shows at a time.
- **Dropdown menu items and modal-sheet rows**: key the trigger and, where
  practical, the rows (`<field>-option-<name>`). Where items are data-driven and
  unkeyed, the agent selects by `--text` — so keep the visible label stable and
  unique.

Document new keys in the per-app skill's key map.

## 2. Make outcomes readable — never rely only on a SnackBar

An agent must be able to confirm an action worked. A transient `SnackBar` may
auto-dismiss before it's read and isn't keyed, so it is **not** a reliable signal.
For any create/update/delete/validate, do one of:

- Emit a structured log: `logDriveResult('<noun>-<verb>', ok: true)` (from
  `stridelabs_drive`, `drive_state.dart`) → an agent reads `get-logs | grep MRESULT`.
  Preferred — works headless and survives the SnackBar dismissing. Follow the
  existing `<noun>-<verb>` action-name convention. The mutation providers/services
  are the canonical place to emit these.
- Or render a durable, **keyed** result/error widget (like a keyed `login-error` /
  `<screen>-error`), not just a SnackBar.

## 3. Expose non-rendered state via MSTATE

If a new screen has state an agent needs but that isn't shown as plain text — an
in-flight flag, a selection count, a mode, an id, a derived status — emit it from
`build()` with `logDriveState('screen=<name> …')` (from `stridelabs_drive`). It logs
`MSTATE …` only on change, so an agent can read current state and wait on
transitions via `get-logs | grep MSTATE`. Keep it to one concise line per screen.
Both helpers are `kDebugMode`-gated and tree-shaken from release. Match the style of
the app's existing lines (`screen=<name> …`, `layout=… section=…`).

## 4. Don't create driving traps

- **A disabled control is a silent no-op.** Submit buttons that disable while busy
  or until required fields are satisfied must make the disabled state *readable*: a
  key plus either `onPressed: null` (so the agent can see it's disabled) or an MSTATE
  flag that gates the tap. Don't hide the button entirely — the agent can't tell
  "not there yet" from "gone".
- **Disabling a text field drops focus** and silently swallows the next input. If
  you disable a field while busy, restore focus when it re-enables
  (`didUpdateWidget`) — otherwise the next `enter-text` goes nowhere.
- **Auto-scroll / visibility:** `get-interactive-elements` returns only *visible*
  nodes. Long forms and lists have content below the fold — the agent must
  `scroll-to --key <key>`; keep every field keyed so it can, and auto-scroll new
  content into view. Don't put a required control somewhere it can never scroll to.
- **Avoid hard-to-drive surfaces** for anything needing automated coverage: real
  OAuth browser popups, native permission dialogs, and audio/voice paths can't be
  driven by Marionette. Provide a debug bypass (like `login-dev-sign-in`) for flows
  gated behind them, and verify such results out-of-band (RSS/API/logs), not by
  watching or listening.

## 5. Validate it's drivable before you're done

After the change, drive it once: `hot-reload`, `get-interactive-elements` to confirm
your new keys appear, exercise the flow, and check the outcome via
`get-logs | grep -E 'MSTATE|MRESULT'` / a screenshot. If you can't drive it from the
keys + logs alone, an agent (or a CI test) can't either — fix the instrumentation,
not the test. Then run `flutter analyze` and `flutter test`.
