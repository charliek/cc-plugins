---
name: ask-panel
description: >-
  Run a three-model panel review of an implementation plan, synthesize findings,
  and incorporate improvements. Use when the user asks for /ask-panel, /forge:ask-panel,
  a plan panel, or a multi-model review of a plan file.
argument-hint: "[--harness gx|cursor|claude] [plan-file-path]"
disable-model-invocation: true
---

# Ask panel

Three-seat plan review for gx, Cursor, and Claude Code.

If `$ARGUMENTS` appears unsubstituted, the brief is the text typed after the slash command.

1. If the spawn tool is unavailable, stop and tell the parent to run this skill.
2. Resolve and read `references/harness.md`, then `references/panel.md` (resolution order is in `harness.md`; if `${CLAUDE_PLUGIN_ROOT}` is unsubstituted, skip it).
3. Detect the harness (`--harness` in `$ARGUMENTS` overrides).
4. Execute the panel procedure. Do not emit another slash command.

`$ARGUMENTS`
