---
name: gauntlet
description: >-
  Full plan → PR flow: discovery, panel-reviewed plan, standalone gated
  commits, verification, one PR per repo watched to green. Use when the user
  asks for /gauntlet, /forge:gauntlet, or an end-to-end build flow. Prefer this
  over /flows:gauntlet when forge is installed.
argument-hint: "[--harness gx|cursor|claude] <scope brief: workstreams, constraints, what done looks like>"
disable-model-invocation: true
---

# Gauntlet

Run a substantial piece of work end-to-end. `$ARGUMENTS` is the scope brief
(requirements document; pinned decisions are settled). Strip a leading
`--harness gx|cursor|claude` override before treating the rest as the brief.
If `$ARGUMENTS` appears unsubstituted, the brief is the text typed after the
slash command.

The user is typically away. Proceed on aligned or clearly-won decisions.
Stop only for one-way doors, large-rework decisions, or undiscussed
destructive actions. Deliver a status update at the end.

**Flat orchestration:** the orchestrator (this session) spawns every
subagent itself — implementers, simplify reviewers, the fixer, the Sol
reviewer, the panel seats. gx forbids nested spawns.

**Do not emit slash commands** for panel, simplify, or gated-commit. Read
those procedures from `references/` and run them inline. If the spawn tool is
unavailable, stop and tell the parent to run this skill.

1. Resolve and read `references/harness.md`, then `references/panel.md`,
   `references/simplify.md`, and `references/gated-commit.md`.
2. Detect the harness (`--harness` overrides).
3. Execute the phases below.

## Phase 0 — Conventions

Read CLAUDE.md, then AGENTS.md, of every repo in scope. Derive:

- the per-commit gate (lint / test / build)
- verification tooling notes and gotchas

The scope may span **multiple repos** — one PR per repo that changes. One
plan covers the whole effort.

Plans and verification artifacts live **outside** the repos (see
`harness.md` plans directory). Exception: honor an explicit in-repo
convention. Because the plan is not in the repo, each PR body must carry its
substance (Phase 6).

**Model policy:** fable-class orchestrates; implementation in opus-class /
sonnet-class subagents by criticality (table in `harness.md`). Fable-class
touches implementation only for the single most critical piece, if any.
Simplify never uses fable-class. Prefix every subagent description with its
model.

If the brief rates workstreams by criticality, use those ratings; otherwise
rate them and note assignments in the plan.

## Phase 1 — Discovery (read-only)

Fan out parallel `explore` subagents (sonnet-class), one per workstream.
Read load-bearing files yourself. Every plan claim needs a file:line
reference. Verify cheap external facts with real requests. If a visual
decision is in scope, gather evidence now.

## Phase 2 — Plan

Write the plan (Phase-0 location) in this shape:

1. Problem / motivation
2. Current state — verified this session, file:line refs
3. Design decisions — PINNED; alternatives considered and why they lost
4. Deviations / non-goals
5. Work breakdown — **standalone units (U1..Un)**: each a complete vertical
   slice (code + tests + docs) that builds and passes the gate alone.
   Size guide for code: ~≤400 changed lines / ~≤10 files (not for
   prose-only units). Merge boundaries that would yield scaffolding-only
   or non-building intermediates. Each unit names its implementer tier
   (sonnet-class default; opus-class if complex/subtle; fable-class only
   for the single most critical piece) and its gate.
6. File map
7. Acceptance criteria — measurable, 1:1 with workstreams
8. Verification plan
9. Risks / open items / explicit future work

For multi-repo scopes, group the work breakdown and acceptance criteria
per repo.

## Phase 3 — Panel review

Execute the panel procedure (`references/panel.md`) against the plan file.
Incorporate findings on their merits; where a finding conflicts with a
pinned decision, resolve it in the plan. Record panel corrections in the
header.

**Every plan goes through the panel**, including new or materially revised
plans produced mid-flight, before implementation resumes against them.

If the panel cannot run, self-review against the Phase-2 checklist and say
the panel was skipped.

## Phase 4 — Implementation (gated units)

Per changed repo: one feature branch (`feature/plan-NNN-<slug>`), one PR,
many standalone commits.

For each planned unit: spawn an implementer subagent with the plan section
as spec (subagent does NOT commit; writable type; `isolation` omitted).
Then run the gated-commit procedure inline. Verify user-visible behavior as
you go (artifacts into the plan's artifact folder). If the implementer
deviates from the plan, fix the code or amend the plan — never leave them
contradicting.

When n ≥ 3 and units touch shared surfaces, run a branch-level Sol-first
review of `git diff <base>...HEAD` before opening the PR (same reviewer
table and fallback as gated-commit).

## Phase 5 — Verification record

Append **"§ Verified"** to the plan: what was checked beyond the automated
tests, artifact names, and known-unexercised paths. Honest about coverage
limits. Nothing verification-related is committed to a repo unless
CLAUDE.md/AGENTS.md documents an in-repo convention.

## Phase 6 — Ship

Per repo that changed:

1. Push; open the PR. Body is the durable public record: what changed per
   workstream, verification summary, dependency/privacy/secret impact,
   accepted risks — and the plan in a collapsible `<details>` block.
   Cross-link sibling PRs. Recommend a **merge commit** (not squash) when
   units are meaningful standalone slices; `merge-pr` still asks the user.
2. Watch CI until green. If `git-commands` is installed, **read** that
   plugin's `watch-pr` command file and execute its steps inline (do not
   emit `/watch-pr`). If it is missing, `gh pr checks --watch --fail-fast`
   (or poll `gh pr checks` every 30s) and say so.
3. Bot reviews: verify the bot actually reviewed (a rate-limited
   CodeRabbit can show as "pass" with no body). Fix each finding or reply
   with the disposition. Never silently ignore.
4. **Default: leave the PR open.** Merge by reading `merge-pr` and running
   its steps inline (`gh pr merge`, or that plugin's procedure) ONLY if the
   brief or plan explicitly requested auto-merge.
5. **Never release/deploy** unless the brief says otherwise.

## Final status update

Lead with the outcome (PR links — ready-for-review or merged-if-requested,
or blocked). Then per workstream: what shipped and decisions made along the
way, especially any decision the user was not part of. Then process notes:
review findings and dispositions, pre-existing fixes, deliberately
untouched surfaces, follow-ups.
