# flows

Named end-to-end build flows, so a whole way of working can be invoked by
name instead of re-explained per session.

## Commands

### `/flows:gauntlet <scope brief>`

The full plan → PR lifecycle for substantial work. The scope may span
multiple repos; the unit of delivery is one PR per repo that changes.

1. **Discovery** — parallel read-only exploration; every plan claim gets a
   file:line reference; visual decisions gathered as evidence up front
2. **Plan** — `~/.claude/plans/<repo>/NNN-<slug>.md` in the house style with
   PINNED decisions (plans and verification artifacts stay OUT of the repos;
   a repo CLAUDE.md can explicitly opt in to in-repo conventions instead)
3. **Panel** — `/planning:ask-panel` (Codex on `gpt-6-astra` + GLM +
   CodeRabbit), findings incorporated. Every plan goes through the panel —
   including new or materially revised plans produced mid-run
3b. **Pause** — hand back the plan, the panel's corrections, an opus-vs-fable
   executor recommendation, and a kickoff prompt for a fresh session
   (`/flows:gauntlet <plan-file>` resumes at Phase 4); the merge policy is
   asked once here and recorded in the plan. Skipped when the brief says to
   run straight through
4. **Gated commits** — per repo: one branch, one PR, a handful of milestone
   commits; each runs `/flows:gated-commit` with the plan's `simplify` and
   `review` marks, with behavior verified as it lands. Nothing is pushed
   until every commit is covered by a review
5. **Verification record** — a final "§ Verified" section appended to the
   plan covering what was checked beyond the automated tests (using
   task-appropriate tooling: browser automation, flutter tools, shell
   functional tests), artifacts in the plan's sibling folder
6. **Ship** — per repo: PR (body carries the verification summary + plan in
   a collapsible block, cross-linked to sibling PRs) →
   `/git-commands:watch-pr` → bot findings fixed or replied to (a
   rate-limited CodeRabbit isn't waited on — every commit was already
   reviewed; a whole-PR look, when needed, runs locally through the codex
   runner). Merge follows the policy recorded at the pause: auto-merge with a
   merge commit, or leave the PRs open (the default when nothing was
   recorded). Never release/deploy unless the brief explicitly says
   otherwise.

Execution runs autonomously: proceeds on decisions already aligned or
clearly won, stops only for one-way doors, large-rework decisions, or
undiscussed destructive actions.

Model policy: the session model orchestrates; implementation runs in
sonnet/opus subagents chosen by task criticality. On fable this is a cost
rule (fable itself only touches the most critical/complex piece); on opus
it's good context-preserving practice. Every subagent label is prefixed
with its model — `(opus) Implement C3` — so it's visible what runs where.

### `/flows:gated-commit [scope notes]`

Just the per-commit inner loop, for any change that deserves discipline
without the full flow: repo gate (from CLAUDE.md) → `/simplify` **only where
it earns its cost** (core interfaces, lots of new logic, repeated logic;
sonnet or opus, never the top-tier model) → codex review through the
`codex-cli` runner, **`gpt-6-sol` for routine work and `gpt-6-astra` for
complex or high-gravity work**, 20/25-minute caps with a progress check every
10 minutes, one fallback (Cursor Grok 4.7, or the CodeRabbit CLI if Cursor is unavailable) →
findings dispositioned → one commit. Small consecutive commits may share one
review, closed by the batch's last commit. Docs-only diffs skip simplify and
the external review (and say so in the commit message); big diffs reach the
reviewer as a diff *file*.

## Repo conventions the flows expect

Flows derive repo specifics from the target repo's CLAUDE.md rather than
hardcoding them. A repo is flow-ready when its CLAUDE.md documents:

```markdown
### Lint & test (per-commit gate — run all before committing)
<the exact commands>
```

Without this, the flows derive a gate from the repo tooling and say so.
Plans/verification default to `~/.claude/plans/<repo>/` and never touch the
repo; a CLAUDE.md that explicitly documents in-repo plans or verification
directories overrides that default. CLAUDE.md notes about verification
tooling (which automation tool is safe where, timeout margins) are also
picked up and respected.

## Cross-plugin dependencies

`gauntlet` uses `planning` (ask-panel), `git-commands` (watch-pr, merge-pr),
`codex-cli` (its `scripts/codex-run.py` runner drives every codex review),
and `cursor` (the review fallback) when installed, degrading gracefully with
a note when they aren't. The CodeRabbit CLI (`coderabbit review --agent`),
if on PATH, is the other review route — a complement, not a duplicate.

New flows join this plugin as sibling commands once their shape has been
battle-tested in real sessions.
