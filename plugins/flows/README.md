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
3. **Panel** — `/planning:ask-panel` (Codex + GLM + CodeRabbit), findings
   incorporated. Every plan goes through the panel — including new or
   materially revised plans produced mid-run
4. **Gated commits** — per repo: one branch, one PR; each commit runs
   `/flows:gated-commit`, with behavior verified as it lands
5. **Verification record** — a final "§ Verified" section appended to the
   plan covering what was checked beyond the automated tests (using
   task-appropriate tooling: browser automation, flutter tools, shell
   functional tests), artifacts in the plan's sibling folder
6. **Ship** — per repo: PR (body carries the verification summary + plan in
   a collapsible block, cross-linked to sibling PRs) →
   `/git-commands:watch-pr` → bot findings fixed or replied to.
   **Default: leave the PRs open for the user's merge decision**; auto-merge
   only when the scope brief explicitly requests it. Never release/deploy
   unless the brief explicitly says otherwise.

Runs autonomously: proceeds on decisions already aligned or clearly won,
stops only for one-way doors, large-rework decisions, or undiscussed
destructive actions.

Model policy: the session model orchestrates; implementation runs in
sonnet/opus subagents chosen by task criticality. On fable this is a cost
rule (fable itself only touches the most critical/complex piece); on opus
it's good context-preserving practice. Every subagent label is prefixed
with its model — `(opus) Implement C3` — so it's visible what runs where.

### `/flows:gated-commit [scope notes]`

Just the per-commit inner loop, for any change that deserves discipline
without the full flow: repo gate (from CLAUDE.md) → **conditional**
`/simplify` (only for new-file or multi-call-site diffs; sonnet or opus by
diff difficulty, never the top-tier model) → codex review with a **hard
10-minute cap** and cursor fallback, adversarialness scaled to the gravity
of the change → findings dispositioned → one commit.

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
and `codex-cli`/`cursor` (review agents) when installed, degrading gracefully
with a note when they aren't.

New flows join this plugin as sibling commands once their shape has been
battle-tested in real sessions.
