---
description: Run one change through the hardened per-commit loop — gate, conditional simplify, capped codex review, commit
argument-hint: "[what this commit is / scope notes]"
---

# Gated Commit — the hardened per-commit inner loop

Take the current uncommitted working-tree changes through the full quality
loop and land them as ONE commit. This is the inner loop of `/flows:gauntlet`,
usable standalone for any change that deserves discipline without a full flow.

`$ARGUMENTS` describes what the commit is (scope notes, plan section
reference). If empty, derive it from the diff.

## Steps

1. **Discover the repo's gate.** Read the repo's CLAUDE.md for its per-commit
   gate (lint/test/build commands). If CLAUDE.md doesn't define one, derive it
   from the repo's tooling (Makefile, package.json scripts, CI workflow) and
   say which commands you chose. Typical shape:
   `make lint && make test && <frontend build if present>`.

2. **Run the gate.** All gate commands must pass before anything else. Fix
   failures in the diff's own code; do not weaken tests to pass them.

3. **Conditional simplify pass.** Run `/simplify` in a subagent scoped to the
   uncommitted diff. Model choice follows the diff's difficulty: sonnet for
   routine/mechanical diffs, opus for complex or subtle ones — NEVER the
   top-tier (fable-class) model for simplify. Run it ONLY when the diff
   matches one of these profiles — empirically the passes that pay for
   themselves:
   - the commit introduces new files/components/modules, OR
   - it touches the same pattern at 2+ call sites (dedup/helper opportunities)

   Prefix the subagent's description with its model — `(opus) Simplify …` —
   as with every subagent in these flows.

   SKIP simplify for small single-file diffs, mechanical moves, and
   net-deletion diffs — those passes historically return nothing.
   Tell the simplify subagent which decisions are pinned spec (from the plan
   or from `$ARGUMENTS`) so it doesn't "simplify away" mandated behavior.
   Re-run the relevant gate subset after any applied fix.

4. **Capped external review.** Run a review of the uncommitted diff with the
   `codex-cli:codex-rescue` agent (or `/codex-cli:rescue --read-only`),
   prompted for CORRECTNESS bugs (not style — simplify owns that). Scale the review's adversarialness
   to the gravity of the change: routine commits get a straightforward
   correctness pass; changes touching data integrity, auth/security, money,
   migrations, or concurrency get an explicitly adversarial prompt (assume
   the diff is wrong, hunt for the exploit/corruption path). The prompt must
   include:
   - the spec/context for the change (plan section or `$ARGUMENTS`),
   - specific failure modes to hunt for, tailored to the diff,
   - a **HARD CAP of 10 minutes** — instruct the agent to kill codex and
     report partial output if it stalls past the cap. NEVER wait unbounded.
     (10 minutes matches the Bash tool's maximum timeout, so the cap is
     actually enforceable.)

   If codex is unavailable, rate-limited, or stalls past the cap, fall back
   to `cursor:cursor-rescue` with the same prompt — do NOT retry codex on a
   rate limit (the retry hits the same quota). If neither is installed, do a
   careful self-review pass and note that in the commit message.

5. **Disposition every finding.** For each review finding: fix it, or record
   WHY it's skipped (pre-existing scope, deliberate house pattern, plan-pinned
   decision). Findings must never be silently dropped. Re-run the gate after
   fixes.

6. **Commit.** One commit, message = what changed and why, plus one line per
   notable review finding and its disposition ("codex review finding" /
   "skipped: pre-existing, plan §9"). Follow the repo's commit conventions.
   Do NOT push unless the calling flow or user says to.

## Knowledge baked in (learned the hard way)

- **Codex stall guard**: the 10-minute cap with a cursor fallback is
  mandatory, and the cap goes INSIDE the reviewer subagent's prompt so the
  subagent enforces it. It was 12 minutes historically, but the Bash tool's
  maximum timeout is 10 — a longer cap silently wasn't enforceable. The `codex-cli` plugin drives `codex exec` directly
  (no shared broker), which eliminated the silent stalls seen with the
  official codex plugin's app-server broker — the cap stays because a big
  diff can still legitimately run long. An empty review result is a
  FAILURE, not "no findings" — fall back, never treat it as a pass.
- **Simplify is complementary to the external review, not redundant**: in
  practice their finding sets don't overlap — the review finds bugs,
  simplify finds structure. That's why both stay, and why simplify is
  conditional.
- **Don't `--unsafe` autofix**: linter unsafe fixes have broken deliberate
  patterns (renamed load-bearing identifiers). Apply safe fixes only; make
  cosmetic changes by hand.
- Time-sensitive tests: respect any repo-documented timeout margins rather
  than tightening or "fixing" them.
