---
description: Full build flow — discovery, panel-reviewed plan, gated commits, verification, PR(s) watched to green
argument-hint: "<scope brief: workstreams, constraints, what done looks like>"
---

# Gauntlet — the full plan → PR flow

Run a substantial piece of work end-to-end: discovery, a written plan
pressure-tested by an AI panel, implementation as small gated commits,
verification beyond the automated tests where needed, and one PR per repo
shepherded to green. Stop before any release/deploy.

`$ARGUMENTS` is the scope brief: the workstreams, constraints, pinned
preferences, and anything the user already knows they want. Treat it as the
requirements document; when it pins a decision, that decision is settled.

The user is typically away. Work autonomously: proceed on your own for
decisions already aligned in the brief or plan, and for choices where one
option is clearly the winner. Stop only for one-way doors, decisions with
large rework potential, or destructive actions that weren't discussed and
aligned on. Deliver a status update at the end.

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
5. Work breakdown — small gated commits (C1..Cn), each independently
   shippable, each naming its gate
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

## Phase 4 — Implementation (gated commits)

- Per changed repo: one feature branch (`feature/plan-NNN-<slug>`), one PR,
  many small commits.
- For each planned commit: implement with a subagent given the plan section
  as its authoritative spec (subagent does NOT commit), then run
  `/flows:gated-commit` for the gate → conditional simplify → capped review
  → commit loop. Review intensity scales with the gravity of the change
  (see gated-commit).
- Verify each commit's user-visible behavior as you go, using the tooling
  the plan's verification section chose (artifacts into the plan's artifact
  folder) — catching a behavior miss at commit time is far cheaper than at
  PR time. Respect any repo-documented tooling gotchas about HOW to drive
  the app (e.g. which automation tool is safe for which pages).
- If the implementer's result deviates from the plan, either fix the code or
  amend the plan — never leave them contradicting each other.

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
4. **Default: leave the PR open** — green, findings reacted to, ready for
   the user's own review and merge decision. Merge yourself
   (`/git-commands:merge-pr`, or `gh pr merge` if that plugin isn't
   installed) ONLY if the scope brief or plan explicitly requested
   auto-merge.
5. **Never release/deploy** unless the brief explicitly says otherwise.

## Final status update

Lead with the outcome (PR links — one per repo — ready-for-review or
merged-if-requested, or blocked). Then per workstream: what shipped and the
decisions made along the way — call out especially any decision made during
the flow that the user wasn't part of. Then process notes: review findings
and dispositions, anything fixed that predated the work, anything
deliberately left untouched, and follow-ups noted as future work.
