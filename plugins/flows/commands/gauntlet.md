---
description: Full build flow — discovery, panel-reviewed plan, executor pause, gated milestone commits, verification, PR(s) watched to green
argument-hint: "<scope brief: workstreams, constraints, what done looks like> | <panel-reviewed plan file to execute>"
---

# Gauntlet — the full plan → PR flow

Run a substantial piece of work end-to-end: discovery, a written plan
pressure-tested by an AI panel, a pause for the user to pick the executor,
implementation as gated milestone commits, verification beyond the automated
tests where needed, and one PR per repo shepherded to green. Stop before any
release/deploy.

`$ARGUMENTS` is the scope brief: the workstreams, constraints, pinned
preferences, and anything the user already knows they want. Treat it as the
requirements document; when it pins a decision, that decision is settled.

**Resuming from a plan.** If `$ARGUMENTS` names an existing plan file that
has been through the panel (its header records the panel corrections), this
is the execution half of a paused run: read the plan, do Phase 0, and start
at Phase 4. The plan is the requirements document now; anything else in
`$ARGUMENTS` is extra direction for the run.

Once execution starts the user is typically away. Work autonomously: proceed
on your own for decisions already aligned in the brief or plan, and for
choices where one option is clearly the winner. Stop only for one-way doors,
decisions with large rework potential, or destructive actions that weren't
discussed and aligned on. Deliver a status update at the end.

## Phase 0 — Conventions

Read the CLAUDE.md of every repo in scope first. The flow needs, and should
derive from it:
- the per-commit gate commands (lint / test / build),
- any verification tooling notes and known gotchas (which tools are safe to
  drive the app with, timeout margins, etc.).

The scope may span **multiple repos** — the unit of delivery is one PR per
repo that changes. One plan covers the whole effort; it names each repo
touched and which workstreams land where.

**Plans and verification artifacts live OUTSIDE the repos** so they never
pile up in project history: the plan goes to
`~/.claude/plans/<repo-name>/NNN-<slug>.md` (primary repo's folder, next free
number) and verification artifacts to the sibling folder
`~/.claude/plans/<repo-name>/NNN-<slug>/`. Exception: if a repo's CLAUDE.md
explicitly documents an in-repo plans/verification convention, honor that
instead. Because the plan isn't in the repo, each PR body must carry its
substance (see Phase 6).

Model policy: the main loop orchestrates; implementation happens in
subagents. Pick each subagent's model by how critical/complex its task is:
**sonnet** for routine or mechanical work, **opus** for complex or subtle
work. When the session runs on a top-tier (fable-class) model this is a
cost rule, not a suggestion — fable orchestrates and touches implementation
directly only for the single most critical or complex piece, if any;
everything else goes to opus/sonnet subagents. `/simplify` in particular
always runs in an opus (or sonnet) subagent, never on fable. On an opus
session the same delegate-to-subagents pattern is still good practice — it
preserves the orchestrator's context — just less critical.

If the scope brief rates workstreams or commits by criticality, use those
ratings for model assignment; otherwise rate them yourself and note the
assignments in the plan's work breakdown.

Prefix every subagent's description/label with its model in parentheses —
`(opus) Implement C3: settings panel`, `(sonnet) Explore auth surface` — so
the user can see at a glance what is running where.

## Phase 1 — Discovery (read-only)

- Fan out parallel Explore subagents, one per workstream/surface named in the
  brief; read the most load-bearing files directly yourself.
- Every claim that will enter the plan needs a file:line reference. Verify
  external facts (API endpoints, style URLs, library options) with real
  requests where cheap.
- If a visual/design decision is in scope, gather the evidence NOW (e.g.
  side-by-side screenshots via a throwaway harness) so the plan can pin it
  instead of deferring it.

## Phase 2 — Plan

Write the plan (at the Phase-0 location) in the house style:

1. Problem / motivation
2. Current state — **verified this session**, with file:line refs
3. Design decisions — PINNED, one subsection per workstream; record
   alternatives considered and why they lost; avoid "decide at
   implementation" for anything user-visible or test-shaping
4. Deviations / non-goals
5. Work breakdown — milestone commits (C1..Cn), each naming its gate,
   implementer model, `simplify` mark, and `review` mark (see below)
6. File map (indicative)
7. Acceptance criteria — measurable, mapped 1:1 to workstreams
8. Verification plan — what needs checking beyond the automated tests, and
   with what tooling. Repo- and task-appropriate: browser automation
   (Chrome MCP, Playwright CLI) for web UI, flutter tooling for Flutter,
   shell/functional tests for CLIs and services. If the automated tests
   fully cover the change, say so and plan nothing extra.
9. Risks / open items / explicit future work

For multi-repo scopes, the work breakdown and acceptance criteria are
grouped per repo, since each repo becomes its own PR.

**Commit size.** Each commit is a standalone milestone: a coherent piece of
work that builds, passes the gate, updates its tests alongside the code, and
is worth reviewing on its own. Prefer fewer, meaningful milestones over many
small steps — a long run of tiny commits multiplies gate, review, and
bookkeeping time without making any of them better. Split only when a unit
would be too large to review well, or when keeping it together would leave a
commit that doesn't build. Numbered steps inside a milestone are an order of
operations, not a commit count.

**Simplify marks.** `/simplify` catches duplication and needless complexity
and pays off most on changes that introduce core interfaces or abstractions
other code will build on, or that land a lot of new logic. It costs real time
and tokens, so decide it here, per commit, with a one-line reason
(`simplify: yes — new storage interface` / `simplify: no — follows the
existing handler pattern`); the panel can challenge it. Also say whether one
pass over the whole branch before the PR is worth it — that catches
duplication that only shows up across several commits. Skipping it is
normal; a plan with no simplify passes is fine when nothing warrants one.

**Review marks.** Every commit gets an external review before the branch is
pushed; the plan says how. Name each commit's reviewer tier — `sol`
(`gpt-6-sol`) for routine work, `astra` (`gpt-6-astra`) when the commit is
complex or subtle (the bar that puts implementation on opus or fable) or
touches concurrency/ordering, data integrity, auth/security, money,
migrations, or wire protocols — and group small consecutive sol commits into
batches that share one review where that is more efficient
(`review: sol, batch C3–C5`). Astra commits stand alone.

## Phase 3 — Panel review

- Run `/planning:ask-panel <plan-file>` (Codex + GLM + CodeRabbit).
- Incorporate findings on their merits; where a finding conflicts with a
  pinned decision, resolve it explicitly in the plan (adopt, adapt, or
  document why not). Record the panel corrections in the plan's header.
- **This applies to every plan, not just the first**: if the run later
  produces a new plan or materially revises this one (scope discovered
  mid-flight, a workstream re-planned), that plan goes through the panel
  too before implementation resumes against it.
- If the planning plugin isn't installed, do a self-review against the
  §Phase-2 checklist and say the panel was skipped.

## Phase 3b — Pause for the executor decision

After the panel, **stop and hand back to the user** unless the brief
explicitly says to run straight through. Planning is where top-tier judgment
pays; execution against a pinned, panel-reviewed plan often doesn't need it,
and a fresh session starts with a clean context. Deliver:

- the plan path and a short summary of the panel's corrections,
- a recommendation on who should orchestrate execution — opus when the plan
  is pinned tightly enough to follow, fable when a remaining piece still
  needs top-tier judgment — and why,
- a ready-to-paste kickoff prompt for a fresh session:
  `/flows:gauntlet <plan-file-path>` plus any run-specific direction.

Before pausing, settle the merge policy while the user is here (unless the
brief already did): ask once, with the question tool, whether the PRs should
auto-merge once CI is green and review findings are handled — with a merge
commit, so each milestone stays visible in history — or be left open for
their own review. Record the answer in the plan header; Phase 6 follows it.

If the brief says to run straight through, record the merge policy it gives
(default: leave open) and continue to Phase 4.

## Phase 4 — Implementation (gated commits)

- Per changed repo: one feature branch (`feature/plan-NNN-<slug>`), one PR,
  a handful of milestone commits.
- For each planned commit: implement with a subagent given the plan section
  as its authoritative spec (subagent does NOT commit), then run
  `/flows:gated-commit` for the gate → simplify (if marked) → review →
  commit loop, passing the commit's `simplify` and `review` marks. Batched
  commits land with `review: pending` and are covered by the batch's closing
  review (see gated-commit).
- **Nothing is pushed until every commit is covered** by an external review,
  a recorded self-review when every reviewer route failed, or
  `review: skipped (docs-only)` — including fix-up, docs, and CI commits
  added along the way.
- Every implementer brief says **"run the gate synchronously, in the
  foreground"** — subagents that background a long gate report success before
  it has finished.
- **Never two implementers in one tree.** Sequential implementers edit the
  branch tree directly (no isolation). Parallel ones each need the `Agent`
  tool's `isolation: "worktree"` and hand back a patch
  (`git add -N . && git diff HEAD --binary > "$(mktemp -d)/x.patch"` — `HEAD`
  so a file the implementer staged but did not commit is still in the patch,
  `--binary` so it round-trips, and a `mktemp -d` path so the patch lives
  outside the worktree and never intent-adds itself) for the orchestrator to
  apply and commit. A subagent inherits the session's worktree pin, so it
  cannot `cd` or `git -C` into a worktree you made by hand — it will silently
  fall back to editing the shared tree alongside its sibling. An isolated
  worktree branches from `origin/<default-branch>` unless the harness is
  configured to branch from HEAD, so by default use them only for commits
  independent of the branch's unmerged work. Resolve and verify that base
  **before spawning** — the harness creates the worktree, and a repo whose
  default is `master`/`develop`, or a stale ref, fails the creation or bases
  it wrong: `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`
  (or `git symbolic-ref refs/remotes/origin/HEAD`), then `git fetch origin`,
  then `git rev-parse --verify --quiet origin/<default-branch>`.
- Verify each commit's user-visible behavior as you go, using the tooling
  the plan's verification section chose (artifacts into the plan's artifact
  folder) — catching a behavior miss at commit time is far cheaper than at
  PR time. Respect any repo-documented tooling gotchas about HOW to drive
  the app (e.g. which automation tool is safe for which pages).
- If the implementer's result deviates from the plan, either fix the code or
  amend the plan — never leave them contradicting each other.
- Before the push, per repo: run the **whole-branch simplify** pass if the
  plan called for one (scoped to the merge-base with the default branch; its
  fixes land as their own gated commit), and a **branch-level review** when
  the PR has three or more commits that touch shared surfaces — the codex
  runner with `--changes-since <merge-base with the default branch>`, astra
  when the commits interact subtly, sol otherwise, same fallback as
  gated-commit.

## Phase 5 — Verification record

Append a final **"§ Verified"** section to the plan file summarizing what was
verified beyond the automated tests and how (naming the artifacts in the
plan's artifact folder), plus any known-unexercised paths — be honest about
coverage limits, including "automated tests covered this fully, nothing
extra was run" when that's the truth. Nothing verification-related is
committed to a repo unless its CLAUDE.md documents an in-repo convention.

## Phase 6 — Ship

Per repo that changed:

1. Push the branch; open the PR. Since the plan file is not in the repo, the
   PR body is its durable public record: what changed per workstream, the
   verification summary (test counts, e2e, manual checks), dependency/
   privacy/secret impact, any accepted risks the plan dispositioned — and
   the relevant plan text in a collapsible `<details>` block at the bottom.
   Cross-link the sibling PRs when the plan spans repos.
2. Run `/git-commands:watch-pr` until CI is green. If the `git-commands`
   plugin isn't installed, watch CI directly (`gh pr checks`) and say so.
3. Bot reviews: **verify the bot actually reviewed** (a rate-limited
   CodeRabbit can show as "pass" with no review body). For each finding:
   fix it, or reply on the thread with the disposition rationale and note
   accepted risks in the PR body. Never silently ignore a finding.
   **A rate-limited CodeRabbit is not a blocker.** Every commit already had
   an external review, so if CodeRabbit on the PR is rate-limited, don't wait
   for it or re-trigger it. If the PR as a whole genuinely needs another look
   (commits interact in ways no single review saw), run the branch-level
   review from Phase 4 locally, with the same rules, rather than through
   CodeRabbit.
   Findings CodeRabbit *did* post still get fixed or answered.
4. **Merge per the plan's recorded policy.** Auto-merge only when the plan
   header or brief says so: `/git-commands:merge-pr`, answering its
   merge-strategy question from the recorded policy (a merge commit) instead
   of asking again — or `gh pr merge --merge --delete-branch` if that plugin
   isn't installed. Otherwise leave the PR open — green, findings reacted
   to, ready for the user's own review and merge decision.
5. **Never release/deploy** unless the brief explicitly says otherwise.

## Final status update

At the Phase 3b pause, the status update is the handoff described there. At
the end of a run, lead with the outcome (PR links — one per repo —
ready-for-review or merged-if-requested, or blocked). Then per workstream:
what shipped and the decisions made along the way — call out especially any
decision made during the flow that the user wasn't part of. Then process
notes: review findings and dispositions, anything fixed that predated the
work, anything deliberately left untouched, and follow-ups noted as future
work.
