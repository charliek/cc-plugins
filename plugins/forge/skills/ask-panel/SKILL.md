---
name: ask-panel
description: >-
  Author a standalone implementation plan in the house style (if none exists)
  and/or run a three-model panel review, synthesize findings, and incorporate
  improvements. Use when the user asks for /ask-panel, /forge:ask-panel, a
  plan in the style of ask-panel, a plan panel, or a multi-model review of a
  plan file. The resulting plan is executable later by /forge:gauntlet.
argument-hint: "[--harness gx|cursor|claude] [plan-file-path | scope brief]"
disable-model-invocation: true
---

# Ask panel

Author and/or panel-review a plan. Works without gauntlet; gauntlet later
consumes the same file.

If `$ARGUMENTS` appears unsubstituted, the brief is the text typed after the slash command.

1. If the spawn tool is unavailable, stop and tell the parent to run this skill.
2. Resolve and read `references/harness.md`, then `references/plan.md` and
   `references/panel.md`.
3. Detect the harness (`--harness` in `$ARGUMENTS` overrides).
4. Follow `plan.md` (write vs review). Then run the panel procedure. Do not
   emit another slash command.

`$ARGUMENTS`
