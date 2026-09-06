# Epic status

Read the cross-repo state of an epic and say what to do next.
`$ARGUMENTS`: the epic name (default: the only one with open items).

## 1. Pull the board

```bash
gh project item-list "$N" --owner "$OWNER" --format json --limit 1000
```

`--limit` defaults to 30, so a bare call silently truncates a board with
several epics on it and every conclusion below would be drawn from a
partial list. Ask for more than you expect, and check whether the returned
count equals the board's `items.totalCount` (`gh project view "$N"
--owner "$OWNER" --format json`); if it does not, page rather than report.

Filter to the named `Epic`. Each item carries its `Phase`, `Blocked by`,
`Status` and `Repository`.

Labels are **not** on the project item — `effort/` lives on the issue. If
you need sizes, fetch them per repo rather than per item:

```bash
gh issue list -R "$R" --state all --limit 200 --json number,labels
```

## 2. Resolve dependencies

`Blocked by` holds item IDs, not issue numbers. Build the ID → status map
first, then mark an item **ready** when every ID it names is `Done`.

An item marked `Blocked` whose blockers are all `Done` is stale — call it
out; that is the most common way one of these boards goes wrong.

This resolution is the reason the command exists. `Blocked by` is a text
field, and Projects cannot filter, slice or group on text, so no saved
board view can show blocked items — see
`references/epic-model.md` § Projects v2 limits. Do not suggest one.

## 3. Report, in this order

1. **Ready now** — open, unblocked, grouped by track, with sizes. This is
   the answer to "what should I start".
2. **In progress** — with the repo and issue link.
3. **Blocked** — each with the specific ID it waits on.
4. **Done since last time**, if the user names a date. The board carries
   no completion timestamp, so read it from the issues:
   `gh issue list -R "$R" --state closed --search "closed:>=YYYY-MM-DD"`.
   Say so if a repo could not be queried, rather than reporting a short
   list as if it were complete.
5. **Phase progress** — done/total per phase, in order, so the
   sequencing is visible at a glance.

Do not editorialise about pace or estimate completion dates. Report what
the board says, name the next action, and stop.
