---
name: gated-commit
description: >-
  Run uncommitted changes through the per-commit loop: repo gate, conditional
  simplify, Sol-first correctness review, dispositions, one commit. Use when
  the user asks for /gated-commit, /forge:gated-commit, or a hardened commit
  without a full gauntlet.
argument-hint: "[--harness gx|cursor|claude] [what this commit is / scope notes]"
disable-model-invocation: true
---

# Gated commit

If `$ARGUMENTS` appears unsubstituted, the brief is the text typed after the slash command.

1. If the spawn tool is unavailable, stop and tell the parent to run this skill.
2. Resolve and read `references/harness.md`, then `references/gated-commit.md` (and `references/simplify.md` if the simplify bar may fire).
3. Detect the harness (`--harness` in `$ARGUMENTS` overrides).
4. Execute the gated-commit procedure inline. Do not emit another slash command. Do not push unless asked.

`$ARGUMENTS`
