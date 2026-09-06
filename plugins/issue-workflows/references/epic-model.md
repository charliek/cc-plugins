# The epic model

An **epic** is one initiative that spans several repos. It lives as a set
of ordinary issues — one per work item, in whichever repo the work happens
— tied together by a single user-level Projects v2 board.

Nothing about an epic changes how an individual issue is written. The
conventions in `conventions.md` apply unchanged; an epic item just carries
a few extra fields on the board.

## Why a Project, and not issue types or sub-issues

Two constraints, both verified against this account:

- **Issue Types** (the native Bug/Feature/Epic dropdown) are an
  organization feature. These repos are user-owned, so they are not
  available. Epic must therefore be a **Project field**.
- **Sub-issues** do work on these repos, but whether a sub-issue may live
  in a *different repo* from its parent is unconfirmed. An epic spanning
  four repos cannot rest on an unverified assumption, so the `Epic` field
  is the mechanism and sub-issues are not used.

Built-in **milestones are per-repo** and so cannot sequence a cross-repo
epic — hence the custom `Phase` field below.

The name matters. Projects v2 already ships a built-in `Milestone` field
that mirrors each issue's native repo milestone, so the name is taken —
and that is a good outcome, because two fields called Milestone meaning
different things would have been a standing trap. `Phase` sequences the
epic; `Milestone` keeps meaning what GitHub means by it. See
`conventions.md` § 6.

## One board, many epics

A single board holds **every** epic. A new initiative is a new value in the
`Epic` field, never a new board. Default name: `StrideLabs Epics`.

That scales because the board stays deliberately thin — three custom
fields against GitHub's documented budget of **50 fields per project,
including built-ins**:

| Field | Type | Purpose |
|---|---|---|
| `Epic` | single-select | Which initiative. One value per epic; every view filters on it. |
| `Phase` | single-select | **Prefixed per epic** — `RP/M1`, `RP/M2`. Single-selects are board-global, so bare `M1` would collide across epics. |
| `Blocked by` | text | Item IDs, comma-separated. Projects has no dependency field. **Display-only** — text fields cannot be filtered, sliced or grouped, so this can never drive a view; `/issue-workflows:status` reads it instead. See § Projects v2 limits. |
| `Status` | built-in | `Todo`, `In Progress`, `Done` — the stock set, not customised. Blocked is carried by the `status/blocked` label and the `Blocked by` field, so the board needs no fourth column. |
| `Repository` | built-in | **This is the track.** Do not add a `Track` field — for a repo-shaped epic it would duplicate this exactly. |
| labels | from the issue | `effort/` carries size; do not mirror it into a board field. |

Two fields deliberately absent, because each would have drifted against an
existing source of truth: `Track` (the built-in `Repository` already says
it) and `Size` (the `effort/` label already says it).

Where a track genuinely is not a repo — a docs or infra lane inside one
repo — subdivide with an `area/` label rather than adding a field.

## Views

One board-wide index, plus two saved views per epic. Each epic view is
filtered to a single `Epic` value — a view must never show a mix, because
the board holds every epic.

- **`All epics`** — the default view, unfiltered, with **Slice by `Epic`**.
  Slicing puts a sidebar on the left listing every epic with a live item
  count; clicking one filters the table to it. New epics appear there on
  their own, which is what makes a single board scale. Columns: `Title`,
  `Epic`, `Phase`, `Status`, `Repository` — the stock column set
  (Assignees, Linked pull requests, Sub-issues progress) is empty for every
  epic item and should be replaced.
- **`<Epic> — by phase`**, grouped by `Phase`. Reading it top to bottom is
  the execution order. This is the view that answers "what next, and what
  can ship".
- **`<Epic> — by repo`**, grouped by `Repository`. What you hand to a
  session working in one repo.

Two views that look obvious and are not worth creating:

- **A `blocked` view cannot be built.** The filter language has no
  empty/non-empty predicate for a **text** field, so nothing can select
  "items whose `Blocked by` is set" — see § Projects v2 limits. Such a view
  degrades to `-status:Done`, which is a duplicate of `by phase` wearing a
  misleading name. Blocked analysis belongs in
  `/issue-workflows:status`, which resolves the ID → status map
  client-side and can therefore also spot *stale* blockers.
- **A board (kanban) view is a trap here.** Its primary affordance is
  dragging a card between Status columns, and that is precisely what
  § Status moves by itself forbids. `by phase` already carries `Status` as
  a column, in execution order.

Archive an epic's items when it closes, so the board stays readable.

## Projects v2 limits worth knowing before designing a view

All four verified against this account; each one has cost a session real
time.

- **Group by, sort by and slice by are not settable through the API.**
  `ProjectV2ViewConfigurationInput` carries exactly one field,
  `visibleFieldIds`. Views can be *created* and filtered and given columns
  by GraphQL, but grouping is a **manual browser step**: open the view,
  *View* → *Group by*, then **Save view** and confirm the dialog — picking
  the field alone leaves the change unsaved.
- **A view's item count cannot be read back from the API.**
  `ProjectV2View` has no `items` field, so a filter cannot be verified by
  GraphQL. `createProjectV2View` also accepts no `filter`, so a view is
  created and then updated. The server stores any filter string verbatim
  without validating it — **a filter that matches nothing looks exactly
  like a filter that works**. Verify by reading the count in the browser's
  filter bar, against a number computed independently from item field
  values. The view's `fields` connection *is* readable, but it returns the
  project's field-definition order, so it confirms which columns are
  present and never their arrangement.
- **A `[ID!]` argument has no working `gh` flag form.** `visibleFieldIds`
  must be sent as JSON through `gh api graphql --input -`. Repeated
  `-F ids=` is rejected outright; `-F ids='["a","b"]'` is accepted and
  wrong, passing the bracketed string as one id.
- **Text fields cannot be filtered on presence.** Against 16 items that
  had a `Blocked by` value, `has:blocked-by`, `-no:blocked-by`,
  `-blocked-by:""` and `blocked-by:*` each returned **0**; bare
  `no:blocked-by` returned all 24. A text field is display-only — it can
  never drive a view, a slice, or a group. Anything that must be
  filterable has to be a single-select.
- **A roadmap needs a Date or Iteration field; there is no free timeline.**
  The roadmap layout renders every row blank until a date source is set,
  and the picker offers only those two types — `Created`, `Updated` and
  `Closed` are not offered. `Date` means start+target **per item**;
  `Iteration` sets its dates once on the field, so items stay a dropdown
  pick and the timeline gains milestone markers and an auto-advancing
  `@current`. For an epic paced in someone's free time, neither earns its
  upkeep: `Phase` already sequences the work, and **Insights → Burn up**
  charts progress from item add/close timestamps with no date field at
  all.

## Item identity

Every epic item gets a short ID, unique within its epic, prefixed by
track: `R3`, `A0`, `S7`. The issue title carries it in brackets:

```
[R3] roost: a vt payload kind, so a third-party client can attach
```

The ID makes items greppable and lets `Blocked by` reference them without
issue numbers, which do not exist until filing time. The rest of the title
still follows rule 1 in `conventions.md`.

## Item body

```markdown
**Epic:** Roost Pivot · **Phase:** RP/M2 · **Depends on:** A0
**Context:** <url to the reasoning doc, with the section>

## What
## Why it matters
## Acceptance
## Out of scope
```

`Out of scope` matters more here than on a standalone issue: epic items
are picked up by sessions that did not scope them, and the common failure
is an item quietly growing to swallow its neighbours.

## Status moves by itself

The PR that does the work writes `Closes <owner>/<repo>#<n>`. Merging
closes the issue, which moves the board item to `Done`. **No session
should ever set board status by hand** — if it is doing that, the `Closes`
line was missing.

The one field a session may set mid-flight is `Status: In progress` when
it starts, which is optional and only useful when several sessions run at
once.
