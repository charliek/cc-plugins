---
description: Run one change through the hardened per-commit loop — gate, simplify when it earns its cost, tiered codex review (per commit or per batch), commit
argument-hint: "[what this commit is / scope notes / batch notes]"
---

# Gated Commit — the hardened per-commit inner loop

Take the current uncommitted working-tree changes through the quality loop
and land them as ONE commit. This is the inner loop of `/flows:gauntlet`,
usable standalone for any change that deserves discipline without a full flow.

`$ARGUMENTS` describes what the commit is (scope notes, plan section
reference, and — inside a gauntlet — the unit's `simplify` and `review`
marks from the plan's work breakdown). If empty, derive it from the diff.

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

3. **Simplify — only where it earns its cost.** `/simplify` is good at
   catching duplication and needless complexity, and it pays off most when a
   change introduces core interfaces or abstractions other code will build
   on, or lands a lot of new logic. It also costs real time and tokens (a
   median of ~5 minutes, a long tail past 15), and most small commits give it
   nothing to find — so it is a judgment call, and skipping it is normal.

   - **Inside a gauntlet, the plan decides**: each unit is marked
     `simplify: yes/no` with a reason. Follow it, but adjust when the diff
     came out different from the plan — add a pass if the unit grew bigger or
     more structural than planned, drop it if it came out small — and say why
     in the commit message.
   - **Standalone**, judge the diff. Good fits: new core interfaces, modules,
     or public APIs; a lot of new logic; the same logic appearing in several
     places. Usually skip: small or mechanical edits, moves and renames,
     deletions, config, docs, test-only changes, and changes that closely
     follow an existing pattern.

   Run it in a subagent scoped to the uncommitted diff — sonnet for routine
   diffs, opus for complex or subtle ones, never the top-tier (fable-class)
   model — prefixed with its model (`(opus) Simplify …`) like every subagent
   in these flows. Tell it which decisions are pinned spec (from the plan or
   `$ARGUMENTS`) so it doesn't "simplify away" mandated behavior. Its output
   is code like any other: re-run the relevant gate subset after it, and it
   goes through the review below — simplify passes have introduced bugs that
   the review then caught.

4. **External review — tiered, supervised, one commit or one batch.**
   Every commit is covered by an external correctness review before the
   branch is pushed, but coverage can be shared:

   - **Per commit** is the default standalone.
   - **Batching**: small consecutive units may share one review of their
     combined diff when that is more efficient — a gauntlet that runs for
     hours shouldn't pay a full review per tiny commit. A batch *closes* on
     its last unit: commit the earlier units after their gate with
     `review: pending (batch C3–C5)`, and when the closing unit is ready
     (still uncommitted), review everything since the batch's base commit.
     Fix findings in any of the batch's units in that closing commit, and
     record `review: <model> (covers C3–C5)`. Inside a gauntlet the plan's
     `review` column names the batches; you may regroup at runtime if units
     came out different from planned, and say so.
   - **Astra-tier units are reviewed alone**, never batched.

   **Pick the model by complexity** — the same way the gauntlet picks
   implementers: **`gpt-6-sol`** for routine work; **`gpt-6-astra`** when the
   unit is complex or subtle (the bar that puts its implementation on opus or
   fable) or touches concurrency/ordering, data integrity, auth/security,
   money, migrations, or wire protocols. The plan's `review` column decides
   inside a gauntlet; standalone, decide from the diff. Astra reviews get an
   explicitly adversarial prompt (assume the diff is wrong; hunt for the
   exploit or corruption path) and, when a plan exists, its panel findings as
   a hunt list. Sol reviews get a straightforward correctness pass.

   The prompt carries: the spec/context (plan section or `$ARGUMENTS`),
   specific failure modes to hunt for, tailored to the diff, and a fixed
   per-item verdict — "no issue — why, file:line", or a finding with file:line
   plus the concrete failure scenario — plus the list of files/ranges read.
   Ask for CORRECTNESS bugs, not style (simplify owns that).

   **Run it through the codex-cli plugin's runner** (`scripts/codex-run.py`),
   launched by you with `run_in_background: true` — not through the
   `codex-rescue` agent, whose single foreground shell call can't outlast 10
   minutes. The runner is read-only, caps sol at 20 minutes and astra at 25,
   checks every 10 minutes that Codex's output is still growing (and kills a
   stalled run rather than waiting out the cap), kills the whole process tree
   on any exit, and appends the change bundle itself — including a diff file
   in place of an inline diff past ~900 lines. You are notified when it exits;
   there is nothing to poll.

   ```bash
   runner=${CODEX_RUN:-$(find ~/.claude/plugins ~/.cursor/plugins ~/.grok/installed-plugins ~/.grok/plugins \
     -path '*codex-cli*/scripts/codex-run.py' 2>/dev/null | xargs -r ls -t 2>/dev/null | head -n1)}
   [ -f "$runner" ] || { echo "codex-run.py not found: install the codex-cli plugin (or set CODEX_RUN)"; exit 9; }
   uv run --script "$runner" --model sol --changes-since HEAD --prompt-file "<prompt file you wrote>"
   # astra: --model astra.  Batch-closing review: --changes-since <batch base commit>.
   ```

   Shell variables don't survive between tool calls: resolve the runner once,
   note its absolute path, and use that path in any later call (the
   fallback's `--bundle-only` below included). It needs `uv`; `python3
   "$runner"` works the same where `uv` is missing.

   Exit `0` prints the review. **Anything else is "no review", never "no
   findings"**: `3` failed, `4` empty, `5` stalled, `6` capped, `7` usage
   limit / rate limit / capacity, `8` auth, `9` codex missing. Then run **one**
   fallback, not several — reviewer cost adds up and their findings overlap:

   1. `cursor:cursor-rescue` with the same prompt, stated as a **read-only
      review — make no edits** (that is what switches it to Cursor's
      `--mode plan`; it has no `--read-only` flag), and the same changes:
      `uv run --script "$runner" --changes-since <ref> --bundle-only` prints
      the exact bundle codex got, as a file path once it is big. It runs Grok
      4.7 through Cursor, and its foreground shell call is capped at 10
      minutes. Do not retry codex after a `7` — the retry hits the same quota.
   2. If Cursor is unavailable: the CodeRabbit CLI —
      `coderabbit review --agent --uncommitted --include-untracked -c <instructions>.md`
      for one uncommitted commit, `--base-commit <batch base>
      --include-untracked` in place of `--uncommitted` for a batch (older CLIs
      spell the uncommitted scope `-t uncommitted`; check
      `coderabbit review --help`) — bounded by the shell tool's 600000
      timeout; a killed run is "no review".
   3. If nothing external ran: a careful self-review, noted in the commit
      message.

   A batch that stalls or hits the cap is too big for one pass: split it into
   two narrower reviews rather than re-running it whole.

   SKIP the external review for docs-only diffs and record
   `review: skipped (docs-only)` in the commit message — there is no
   correctness surface for it to find, and that line is the commit's
   coverage.

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
   "skipped: pre-existing, plan §9"), a `review:` line naming the model that
   actually ran and what it covered (`review: gpt-6-sol`,
   `review: gpt-6-astra`, `review: pending (batch C3–C5)`,
   `review: grok-4.7-high via cursor (codex usage limit)`), and a
   `simplify:` line when a pass ran or a planned one was dropped. Follow the
   repo's commit conventions. Do NOT push unless the calling flow or user
   says to.

## Knowledge baked in (learned the hard way)

- **Why the runner and not a recipe**: reviews legitimately run past 10
  minutes (the shell tool's per-call ceiling), a stalled codex looks exactly
  like a slow one until something checks its output, and a killed
  `codex exec` that outlives its caller keeps its thread locked. The runner
  handles all three in one place; an empty or killed result is a FAILURE,
  never a pass.
- **Simplify is complementary to the external review, not redundant**: in
  practice their finding sets don't overlap — the review finds bugs,
  simplify finds structure. That's why both exist, and why simplify is a
  judgment call rather than a fixed step.
- **Grep for importers before deleting or renaming a public name** in a test
  helper or shared module (`from X import`, `use crate::…`). A sibling module
  importing a deleted name breaks collection for every lane — including one
  that only *deselects* that module, since `-m 'not marker'` still imports it.
- **Don't `--unsafe` autofix**: linter unsafe fixes have broken deliberate
  patterns (renamed load-bearing identifiers). Apply safe fixes only; make
  cosmetic changes by hand.
- Time-sensitive tests: respect any repo-documented timeout margins rather
  than tightening or "fixing" them.
