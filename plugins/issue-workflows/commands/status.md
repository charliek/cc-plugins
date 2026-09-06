# Epic status

Read the cross-repo state of an epic and say what to do next.
`$ARGUMENTS`: the epic name (default: the only one with open items).

## 1. Pull the board

```bash
gh project item-list "$N" --owner "$OWNER" --format json --limit 200
```

Filter to the named `Epic`. Each item carries its `Phase`,
`Blocked by`, `Status`, `Repository` and its `effort/` label.

## 2. Resolve dependencies

`Blocked by` holds item IDs, not issue numbers. Build the ID → status map
first, then mark an item **ready** when every ID it names is `Done`.

An item marked `Blocked` whose blockers are all `Done` is stale — call it
out; that is the most common way one of these boards goes wrong.

## 3. Report, in this order

1. **Ready now** — open, unblocked, grouped by track, with sizes. This is
   the answer to "what should I start".
2. **In progress** — with the repo and issue link.
3. **Blocked** — each with the specific ID it waits on.
4. **Done since last time**, if the user names a date.
5. **Phase progress** — done/total per phase, in order, so the
   sequencing is visible at a glance.

Do not editorialise about pace or estimate completion dates. Report what
the board says, name the next action, and stop.
