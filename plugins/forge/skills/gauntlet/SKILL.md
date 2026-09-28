---
name: gauntlet
description: >-
  Full plan → PR flow: discovery, panel-reviewed plan, a pause to pick the
  executor, gated milestone commits, verification, one PR per repo watched to
  green. Pass a panel-reviewed plan file to run just the execution half. Use
  when the user asks for /gauntlet, /forge:gauntlet, or an end-to-end build
  flow. Prefer this over /flows:gauntlet when forge is installed.
argument-hint: "[--harness gx|cursor|claude] <scope brief: workstreams, constraints, what done looks like> | <panel-reviewed plan file>"
disable-model-invocation: true
---

# Gauntlet

Run a substantial piece of work end-to-end. `$ARGUMENTS` is the scope brief
(requirements document; pinned decisions are settled). Strip a leading
`--harness gx|cursor|claude` override before treating the rest as the brief.
If `$ARGUMENTS` appears unsubstituted, the brief is the text typed after the
slash command.

**Resuming from a plan.** If the brief is a single path to an existing plan
that has been through the panel (its header records the panel corrections),
this is the execution half of a paused run: do Phase 0, read the plan, and
start at Phase 4. Anything else in `$ARGUMENTS` is extra direction.

Once execution starts the user is typically away. Proceed on aligned or
clearly-won decisions. Stop only for one-way doors, large-rework decisions,
or undiscussed destructive actions. Deliver a status update at the end.

**Flat orchestration:** the orchestrator (this session) spawns every
subagent itself — implementers, simplify reviewers, the fixer, the Codex
reviewer, the panel seats. gx forbids nested spawns.

**Do not emit slash commands** for panel, simplify, or gated-commit. Read
those procedures from `references/` and run them inline. Follow `harness.md`
spawn availability (gauntlet implementation always needs spawn; stop and tell
the parent if it is missing).

1. Resolve and read `references/harness.md`, then `references/plan.md`,
   `references/panel.md`, `references/simplify.md`, and
   `references/gated-commit.md`.
2. Detect the harness (`--harness` overrides).
3. Execute the phases below.

## Phase 0 — Conventions

Read CLAUDE.md, then AGENTS.md, of every repo in scope. Derive:

- the per-commit gate (lint / test / build)
- verification tooling notes and gotchas

The scope may span **multiple repos** — one PR per repo that changes. One
plan covers the whole effort, stored under the **primary** repo key in
`harness.md` (first repo named in the brief, else cwd).

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

Write the plan (Phase-0 location) using `references/plan.md`. That file is
the house style: required sections, milestone units with their `simplify`
and `review` marks, and write path. Do not duplicate it here. After the file
exists, continue to Phase 3.

## Phase 3 — Panel review

Execute the panel procedure (`references/panel.md`) against the plan file.
Incorporate findings on their merits; where a finding conflicts with a
pinned decision, resolve it in the plan. Record panel corrections in the
header.

**Every plan goes through the panel**, including new or materially revised
plans produced mid-flight, before implementation resumes against them.
Honor `harness.md` panel quorum: 0/3 → stop, do not implement; 1/3 → record
`degraded panel (1/3)` and tell the user before continuing; ≥ 2/3 → proceed.
Do not treat a self-review as a panel pass.

## Phase 3b — Pause for the executor decision

After the panel, **stop and hand back to the user** unless the brief
explicitly says to run straight through. Planning is where top-tier judgment
pays; execution against a pinned, panel-reviewed plan often doesn't need it,
and a fresh session starts with a clean context. Deliver:

- the plan path and a short summary of the panel's corrections,
- a recommendation on who should orchestrate execution — opus-class when the
  plan is pinned tightly enough to follow, fable-class when a remaining piece
  still needs top-tier judgment — and why,
- a ready-to-paste kickoff prompt for a fresh session:
  `/forge:gauntlet <plan-file-path>` plus any run-specific direction.

Before pausing, settle the merge policy while the user is here (unless the
brief already did): ask once with the question tool whether the PRs should
auto-merge once CI is green and findings are handled — with a merge commit,
so each milestone stays visible in history — or be left open for their own
review. Record the answer in the plan header; Phase 6 follows it.

If the brief says to run straight through, record the merge policy it gives
(default: leave open) and continue.

## Phase 4 — Implementation (gated units)

Per changed repo: one feature branch (`feature/plan-NNN-<slug>`), one PR,
a handful of milestone commits.

For each planned unit: spawn an implementer subagent with the plan section
as spec (subagent does NOT commit; writable type). Sequential implementers
edit the branch tree directly (`isolation` omitted). **Never two implementers
in one tree** — parallel ones each need their own, and the way to get one is
per harness:

- **Claude Code:** the spawn tool's `isolation: "worktree"`, and only that. A
  subagent inherits the session's worktree pin and cannot `cd` or `git -C`
  into a worktree you made by hand — it silently falls back to editing the
  shared tree alongside its sibling.
- **gx:** `task` takes `isolation: "worktree"`, or a `cwd` naming a worktree
  you created (the two are mutually exclusive). Worktree creation is
  best-effort — on failure gx drops the child into the shared workspace with
  only a log line — so confirm each implementer really landed in its own tree
  before letting them run at once.
- **Cursor:** no isolation primitive we can verify. Run implementers serial on
  the branch, or create the worktree yourself and launch the sub-agent *in* it
  as its working directory. Never two in a shared tree.

Each isolated implementer hands back a patch, written with two plain
commands — `git add -N .`, then
`git diff HEAD --binary --output='<plan artifact folder>/<unit>.patch'`:
`HEAD` so a file it staged but did not commit is still included, `--binary`
so the patch round-trips, and an absolute path outside the worktree so the
patch never intent-adds itself. No `$(mktemp -d)`, `&&`, or redirect: a
worktree-isolated session refuses git inside a construct it can't verify. The
orchestrator applies it. An isolated worktree branches from
`origin/<default-branch>` unless the harness is configured to branch from
HEAD, so by default use them only for units independent of the branch's
unmerged work. Resolve and verify that base **before spawning**, since the
harness creates the worktree and a repo defaulting to `master`/`develop` (or a
stale ref) fails or mis-bases it: `gh repo view --json defaultBranchRef -q
.defaultBranchRef.name` (or `git symbolic-ref refs/remotes/origin/HEAD`),
`git fetch origin`, then `git rev-parse --verify --quiet origin/<default>`.

Every implementer brief says **"run the gate synchronously, in the
foreground"** — subagents that background a long gate report success before it
finishes — and to **never pipe a gate command** (no `tail`, `grep`, or `head`:
a pipe reports the filter's exit code, not the gate's), and report each
target's exit code.

**A flake in code another active session owns** (a gate or CI failure outside
this plan's scope): diagnose it read-only — a CPU-starvation repro such as
`systemd-run --user --scope -p CPUQuota=5% <test command>` separates starvation
from a real ordering bug — then send the owning session the evidence and two
options: they fix it, or you fix it and they review the diff before you
commit. Don't edit another session's code unasked. If you fix it, the
implementer brief asks for evidence that tells starvation from an ordering
bug: timing clusters, a state dump at the watchdog, and a forced-delay repro
that fails deterministically.

Then run the gated-commit procedure inline with the unit's `simplify` and
`review` marks. Batched units land with `review: pending` and are covered by
their batch's closing review. Verify user-visible behavior as you go
(artifacts into the plan's artifact folder). If the implementer deviates from
the plan, fix the code or amend the plan — never leave them contradicting.

**Nothing is pushed until every commit is covered** by an external review, a
recorded self-review when every route failed, or `review: skipped
(docs-only)` — including fix-up, docs, and CI commits added along the way.

Before the push, per repo:

- **Whole-branch simplify**, if the plan called for one: run the simplify
  procedure against the merge-base with the default branch; its fixes land
  as their own gated commit.
- **Branch-level review** when the PR has three or more commits that touch
  shared surfaces: the codex runner with `--changes-since <merge-base with
  the default branch>`, astra when the units interact subtly, sol otherwise;
  same fallback as gated-commit.

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
   Cross-link sibling PRs.
   GitHub caps a PR body at 65,536 characters, and a panel-hardened plan can
   exceed it: then excerpt what a reviewer needs (problem, acceptance
   criteria, amendments, § Verified) and say where the full plan lives. To
   change the body later, use
   `gh api -X PATCH repos/<owner>/<repo>/pulls/<n> -F body=@<file>` —
   `gh pr edit --body-file` can fail on a repo with classic-Projects metadata
   and leave the body unchanged — and check that the body actually changed.
2. Watch CI until green. If `git-commands` is installed, **read** that
   plugin's `watch-pr` command file and execute its steps inline (do not
   emit `/watch-pr`). If it is missing, `gh pr checks --watch --fail-fast`
   (or poll `gh pr checks` every 30s) and say so — `--fail-fast` exits on the
   first failing check, bot reviews included, so when only a bot check
   tripped it, resume the watch without that flag. Either way the circuit
   breaker counts infrastructure reruns as well as code fixes: after one
   rerun of the same job, a second failure stops the loop and asks the user.
3. Bot reviews: verify the bot actually reviewed (a rate-limited
   CodeRabbit can show as "pass" with no body). Fix each finding or reply
   with the disposition. Never silently ignore. **A rate-limited CodeRabbit
   is not a blocker**: every commit already had an external review, so don't
   wait for it or re-trigger it. If the PR as a whole genuinely needs another
   look (units interact in ways no single review saw), run the branch-level
   Codex review above locally, with the same rules, rather than through
   CodeRabbit. Findings CodeRabbit *did* post still get fixed or answered.
4. **Merge per the plan's recorded policy.** Auto-merge only when the plan
   header or brief says so; otherwise leave the PR open. To auto-merge, read
   `merge-pr` and run its steps inline, answering its merge-strategy
   question from the recorded policy (a merge commit) instead of asking
   again; without that plugin, `gh pr merge --merge --delete-branch`.
5. **Never release/deploy** unless the brief says otherwise.

## Final status update

At the Phase 3b pause, the status update is the handoff described there. At
the end of a run, lead with the outcome (PR links — ready-for-review or merged-if-requested,
or blocked). Then per workstream: what shipped and decisions made along the
way, especially any decision the user was not part of. Then process notes:
review findings and dispositions, pre-existing fixes, deliberately
untouched surfaces, follow-ups.
