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

   **Derive from CI too, not just the Makefile.** Grep the CI workflow for
   build/test invocations its documented targets don't cover — feature-gated
   or per-crate/per-package steps especially — and add the ones covering the
   code you touched. A CI-only feature build caught an exhaustive-match break
   the whole local gate missed.

2. **Run the gate.** All gate commands must pass before anything else. Fix
   failures in the diff's own code; do not weaken tests to pass them.

   **Test-bearing diffs**: rebuild before running — a stale binary passes
   vacuously — and give every new or converted functional test a negative
   control: break the expectation, watch it fail on that exact line, restore.
   An assertion never seen red is not evidence.

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

   SKIP simplify for small single-file diffs, mechanical moves,
   net-deletion diffs, and docs-only diffs — those passes historically return
   nothing.
   Tell the simplify subagent which decisions are pinned spec (from the plan
   or from `$ARGUMENTS`) so it doesn't "simplify away" mandated behavior.
   Re-run the relevant gate subset after any applied fix.

4. **Capped external review.** Run a review of the uncommitted diff with the
   `codex-cli:codex-rescue` agent (or `/codex-cli:rescue --read-only`),
   prompted for CORRECTNESS bugs (not style — simplify owns that). The
   review must run **read-only**: the rescue agent defaults to
   write-capable, so the prompt must include `--read-only` (or explicitly
   demand `-s read-only`) — a reviewer must never touch the diff it is
   reviewing. Scale the review's adversarialness
   to the gravity of the change: routine commits get a straightforward
   correctness pass; changes touching data integrity, auth/security, money,
   migrations, or concurrency get an explicitly adversarial prompt (assume
   the diff is wrong, hunt for the exploit/corruption path). The prompt must
   include:
   - the spec/context for the change (plan section or `$ARGUMENTS`),
   - specific failure modes to hunt for, tailored to the diff,
   - a **HARD CAP of 10 minutes** — instruct the agent to kill the
     reviewer CLI and report partial output if it stalls past the cap
     (phrased engine-neutrally so it applies to the cursor fallback too).
     NEVER wait unbounded.
     (10 minutes matches the Bash tool's maximum timeout, so the cap is
     actually enforceable.)

   For diffs past ~900 lines, **hand the reviewer a diff file** rather than
   letting it derive the diff: `git add -N .` (intent-to-add, so new files
   appear) then `git diff HEAD > "$(mktemp -d)/x.diff"` — `HEAD` captures
   staged and unstaged together, so a partially staged tree isn't half
   reviewed, and the `mktemp -d` path is per-invocation so parallel reviews
   never overwrite each other. Instruct it to read that file first, never
   run `git diff` itself, then read only the named files, sections, symbols,
   or line ranges, within a stated read budget. Require a fixed per-item
   verdict — "no issue — why, file:line", or a finding with file:line plus
   the concrete failure scenario — plus the list of files/ranges it read. A
   reviewer left to discover a big diff dumps tens of thousands of lines and
   reaches the cap with no verdict.

   SKIP the external review for docs-only diffs (and say so in the commit
   message) — there is no correctness surface for it to find.

   If codex is unavailable, rate-limited, or stalls past the cap, fall back
   to `cursor:cursor-rescue` with the same prompt — do NOT retry codex on a
   rate limit (the retry hits the same quota). CodeRabbit's CLI
   (`coderabbit review --agent --uncommitted --include-untracked -c <instructions>.md`
   — older CLIs spell the scope `-t uncommitted`; check `coderabbit review
   --help`) is the other strong route, and a genuine complement: it found a
   contract bug (a counter bumped only on the success path) that both codex
   and self-review missed. Prefer it when a sandboxed CLI reviewer can't start
   at all. It has no timeout flag of its own, so bound it the same way as
   codex — run it under the shell tool's timeout (600000, the maximum) and
   treat a killed run as "no review", not "no findings", and fall through.
   If no external reviewer is available, do a careful self-review pass and
   note that in the commit message.

5. **Disposition every finding.** For each review finding: fix it, or record
   WHY it's skipped (pre-existing scope, deliberate house pattern, plan-pinned
   decision). Findings must never be silently dropped. Re-run the gate after
   fixes.

   Check a proposed fix against the plan's pinned decisions before applying
   it — reviewers routinely "fix" a deliberate choice back to the default.
   And a reviewer's "no issue" does not close an item you already flagged:
   record both views; the disagreement is itself the disposition.

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
- **Grep for importers before deleting or renaming a public name** in a test
  helper or shared module (`from X import`, `use crate::…`). A sibling module
  importing a deleted name breaks collection for every lane — including one
  that only *deselects* that module, since `-m 'not marker'` still imports it.
- **Don't `--unsafe` autofix**: linter unsafe fixes have broken deliberate
  patterns (renamed load-bearing identifiers). Apply safe fixes only; make
  cosmetic changes by hand.
- Time-sensitive tests: respect any repo-documented timeout margins rather
  than tightening or "fixing" them.
