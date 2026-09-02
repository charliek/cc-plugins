# Plan house style

Shared by `ask-panel` (standalone planning + panel) and `gauntlet` (Phase 2).
A plan written to this shape is executable later by gauntlet without rewriting.
Read `harness.md` first for write/read paths and model tiers.

## When to write vs review

- **Review** if the user pointed at an existing plan file, or one is already
  active in this conversation.
- **Write, then panel** if the user asked to make a plan (including "in the
  style of /ask-panel") and no plan file exists yet. Use the user's brief as
  the requirements document; pinned decisions in the brief are settled.

Do not ask for a path and stop when the user clearly wants a new plan.

## Write location

Per `harness.md`: Cursor `~/.cursor/plans/<repo>/NNN-<slug>.md`; gx and
Claude Code `~/.claude/plans/<repo>/NNN-<slug>.md`. Multi-repo scopes use the
primary-repo key in `harness.md`. Next free `NNN`. Artifacts
in the sibling `NNN-<slug>/`. Honor an in-repo convention if CLAUDE.md or
AGENTS.md documents one. The plan stays out of git unless that convention
says otherwise.

## Discovery before writing

Read CLAUDE.md, then AGENTS.md. Fan out sonnet-class `explore` subagents as
needed. Every claim that will enter the plan needs a file:line reference.
Verify cheap external facts with real requests. Gather visual evidence now
if a visual decision is in scope.

## Required sections

1. Problem / motivation
2. Current state — verified this session, with file:line refs
3. Design decisions — PINNED; one subsection per workstream; alternatives
   considered and why they lost. Avoid "decide at implementation" for
   anything user-visible or test-shaping
4. Deviations / non-goals
5. Work breakdown — standalone units (see below)
6. File map (indicative)
7. Acceptance criteria — measurable, mapped 1:1 to workstreams
8. Verification plan — what to check beyond automated tests, and with what
   tooling. If tests fully cover the change, say so
9. Risks / open items / explicit future work

For multi-repo scopes, group the work breakdown and acceptance criteria per
repo (one PR per repo that changes).

The readiness checklist in `panel.md` must be true before seats launch.
Standalone: a later session (or gauntlet) can execute this plan with no
chat history.

## Standalone units

A unit is one independently shippable slice: it builds, passes the per-commit
gate, and can be reviewed on its own. Name them U1..Un in suggested order.
Each unit names its implementer tier (sonnet-class default; opus-class if
complex/subtle; fable-class only for the single most critical piece, if any)
and its gate.

**Prefer fewer units.** Split only when keeping the work together would make
the slice too large to review, or would force a commit that does not build
or that is scaffolding with no user-visible or testable value. Combining
tightly coupled edits into one unit is the default.

The ~400 changed lines / ~10 files figure is an **upper bound for code**,
not a target and not a reason to split. It does not apply to prose-only
work. Numbered items in a breakdown are an order of operations, not a
required commit count.

## After the file exists

Run the panel procedure (`panel.md`). Record panel corrections in the plan
header. "Panel-reviewed" needs ≥ 2 successful seats; degraded quorum is
called out before anyone implements.
