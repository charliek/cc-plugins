# Issue conventions

A **designed go-forward standard**, not a description of current practice.
Existing issues predate it, are inconsistent between repos, and are **not
retrofitted** — apply this to new issues and to any issue you substantially
rewrite. Where an old issue conflicts, the old issue is simply old.

## Who these repos are for

These repos are public but are **not seeking contributors**. There is no
triage queue, no onboarding funnel, and no contributor-recruitment
labelling. Do not create or apply `good first issue`, `help wanted`, or
anything similar, and do not word an issue as an invitation. Issues here
are working notes for the maintainer and the agents working alongside
them.

## 1. The title states a finding, not a topic

A title is a one-line claim, not a label for an area of concern. It should
survive being read on its own in a list of eighty.

**Defects** — state what IS wrong and what it costs. Present tense, no
imperative:

```
shed-server restart leaves running sheds credential-broken, and nothing says so
Extraction list queries have no ORDER BY tiebreaker — rows can be omitted or duplicated across pages
```

**Changes** — state what should become true, and for whom:

```
roost: a vt payload kind, so a third-party client can attach without matching libghostty
shed-mobile: confirm before removing a host, matching shed delete
```

Shape: `<area>: <the claim>, <the consequence>`. The area prefix is
optional, lowercase after the colon, and used when a repo has real
subsystems (`CI:`, `macOS:`, `Host sessions:`). The consequence clause is
what stops a title being a topic — do not drop it to save characters.

Banned: bare imperatives (`Fix the host agent`), topic labels
(`Namespace bug`), vague improvement (`Improve error handling`).

## 2. Acceptance is required for anything an agent will work

The rule that matters most here, because a session builds directly against
it and will otherwise invent its own.

An issue is **ready to be worked** when it has a `type/` label, a filled
Acceptance section, and no `status/needs-triage`. Anything else is a
report, not a task — which is fine, but do not hand it to a session.

Write acceptance as checkable statements, not intentions:

```markdown
## Acceptance
- [ ] `roostctl host status` prints `retry.reason` in human output
- [ ] a test asserts the reason survives a reconnect
- [ ] the JSON output is unchanged
```

Bad: `- [ ] error handling is better`.

## 3. Bodies are short, evidence-first, and honest about uncertainty

Four headings, in this order. Drop any that would be padded — two real
sections beat four hedged ones. Acceptance is the one that is not optional
(rule 2).

```markdown
## What
The observable behavior, one paragraph.

## Why it matters
Who hits it, what breaks, what it silently hides. If you cannot write
this, consider whether the issue should exist.

## Evidence
A log line, `file.rs:120`, a failing test name, a command and its output.
Real output beats description.

## Acceptance
- [ ] checkable statements
```

**Uncertainty is labelled, never smuggled.** An unverified cause is written
as `Hypothesis: …`, not stated as fact. An agent filing an issue must
separate what it observed from what it inferred — a confident wrong cause
sends the next session down a dead end, which is the most damaging thing
an agent-filed issue can do.

Never include secrets, tokens, or customer data. Refer to people by role.

## 4. Three label axes, slash-delimited, applied by tooling

Labels are the one part of this that is genuinely broken today. Nine repos
carry four competing schemes and most issues carry no label at all: `shed`
grew `type:`/`priority:`/`area:`, `tapper` grew `effort/`+`value/`, `prox`
grew `severity:`+`complexity:`, `stridelabs-rust` has only dependabot's,
and the rest have nothing but GitHub's stock set.

Three of those repos independently reached for the same two ideas — **how
big is it** and **how much does it matter** — so the standard keeps both
rather than collapsing them into one priority field.

| Axis | Values | Required |
|---|---|---|
| `type/` | `bug`, `enhancement`, `docs`, `chore`, `ci` | **yes** |
| `priority/` | `high`, `medium`, `low` | no — absence honestly means unprioritised |
| `effort/` | `small`, `medium`, `large` | no — but it is what lets a session pick work it can finish |
| `status/` | `needs-triage`, `blocked` | no — absence means understood and unblocked |
| `area/` | repo-specific, lowercase | no |

**Slash, not colon.** `type/bug` needs no shell quoting on the `gh` calls
that create it; `"type: bug"` does, on every single one. It also matches
the broad OSS convention (`kind/bug`, `area/kubelet`).

The axis is named `type` rather than `kind` so it migrates cleanly if
GitHub's native Issue Types — an organization feature today, and these
repos are user-owned — ever reach user accounts.

### `status/needs-triage` — the one state that is not derivable

Everything else about an issue can be read off its contents. This cannot:
a report can be perfectly well written and still be waiting on a human to
decide **whether it should be done at all**, or **which release it belongs
to**. Apply it when either is true:

- the report is incomplete — a symptom with no reproduction, someone
  else's bug report, a hunch worth keeping but not yet understood; or
- it is understood, but nobody has decided to do it, or when.

It comes **off** when the issue is understood, accepted, and has
acceptance criteria. If triage decides against it, do not remove the
label — close the issue with a resolution marker and a reason.

An agent filing an issue from an incomplete report should apply it rather
than inventing the missing detail. An agent must never remove it: that is
a decision, not a task.

`status/blocked` is the sibling — waiting on something external, paired
with a comment naming the blocker.

### Resolution markers

**`duplicate`**, **`invalid`**, **`wontfix`** — resolution, not type.
Apply one when closing by hand (rule 5).

Because most issues today are unlabelled, the convention only holds if
labelling is free: `/issue-workflows:file` applies `type/`, `effort/` and — where the report
warrants it — `status/needs-triage` without being asked, and that is the
intended enforcement mechanism.

Everything else in GitHub's stock set is dropped. `bug`, `enhancement` and
`documentation` duplicate the `type/` axis with worse precision; `question`
has no use here; `good first issue` and `help wanted` are contributor
recruitment, which these repos are not doing.

### Legacy migration

`/issue-workflows:setup` maps the existing schemes onto the standard
rather than dropping them:

| Legacy | Becomes |
|---|---|
| `severity:high\|medium\|low` (prox) | `priority/high\|medium\|low` |
| `value/high\|medium\|low` (tapper) | `priority/high\|medium\|low` |
| `complexity:small\|medium\|large` (prox) | `effort/small\|medium\|large` |
| `effort/small\|medium\|large` (tapper) | unchanged — already correct |
| `type: bug` etc. (shed) | `type/bug` etc. |
| stock `bug` / `enhancement` / `documentation` | `type/bug` / `type/enhancement` / `type/docs` |
| dependabot's `dependencies`, `github_actions`, `rust` | left alone — machine-owned |

Do not add a fifth axis without editing this file first.

## 5. The PR closes the issue

A pull request that resolves an issue writes `Closes <owner>/<repo>#<n>`
in its body. Never close by hand when a PR did the work: the link is what
makes history navigable, and for epic items it is the entire status
mechanism (see `epic-model.md`).

Closing by hand is right for won't-fix, duplicate, obsolete, and "not
actually a defect" — apply the matching resolution label and say why in a
comment before closing.

## 6. Milestones: native for one repo, the board for many

GitHub's built-in milestones are **per-repo**, which makes them the right
tool for sequencing work inside a single repo — a release, a phase, a
cleanup sweep. Use them there.

They cannot sequence work that spans repos, which is the whole reason the
epic board carries its own **`Phase`** field (`epic-model.md`). The names
are deliberately different: Projects v2 already has a built-in `Milestone`
field that mirrors the repo's native milestone, so `Phase` is the epic's
own sequencer and there is no ambiguity about which is which. An issue can
carry both, meaning different things, and that is fine.

## Cross-references

Name related issues inline by number (`so #399 reaches scripts but not
people`). GitHub renders the link and the backlink both ways, which is
most of what makes a corpus navigable later.
