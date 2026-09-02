---
name: simplify
description: >-
  Simplify scoped code via three parallel read-only reviewers (quality,
  performance, reuse) and one fixer. Use when the user asks for /simplify,
  /forge:simplify, a simplification pass, or cleanup of a diff without a
  full gauntlet.
argument-hint: "[--harness gx|cursor|claude] [scope]"
disable-model-invocation: true
---

# Simplify

If `$ARGUMENTS` appears unsubstituted, the brief is the text typed after the slash command.

1. If the spawn tool is unavailable, stop and tell the parent to run this skill.
2. Resolve and read `references/harness.md`, then `references/simplify.md`.
3. Detect the harness (`--harness` in `$ARGUMENTS` overrides).
4. Execute the simplify procedure. Do not emit another slash command.

`$ARGUMENTS`
