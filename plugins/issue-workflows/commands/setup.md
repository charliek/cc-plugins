# Issue workflow setup

Make a machine, and a set of repos, ready for the issue conventions in
`references/conventions.md` and the epic model in `references/epic-model.md`.

Idempotent: safe to re-run, and re-running after adding a repo is the
intended way to onboard it. `$ARGUMENTS` may name repos (`shed roost`),
`--all` for every repo the user owns with issues enabled, or be empty
(current repo only). Add `--epics` to also provision the shared board.

## 1. Check the machine's gh token — do this first, always

```bash
gh auth status
```

The scopes line must include **`project`** (or `read:project` for
read-only use). It is stored per machine in `~/.config/gh/hosts.yml`, so a
second computer needs it again even though the Project already exists.

If it is missing, stop and tell the user to run:

```bash
gh auth refresh -s project
```

That is interactive (it opens a browser), so **the user must run it, not
you** — suggest they type `! gh auth refresh -s project` to run it in
this session. Without it, labels and migration still work; only the board steps need it.
**But if `--epics` was requested, stop** — do not silently do half the job
and report success. Say which steps ran and which need the refresh.

## 2. Reconcile labels, per repo

For each target repo, bring it onto the three-axis standard.

Create the canonical set (skip any that exist — `gh label create` fails
loudly on a duplicate, so use `--force` to make it an upsert):

```bash
gh label create type/bug              -R "$R" -c B60205 -d "A defect"  --force
gh label create type/enhancement      -R "$R" -c 0E8A16 -d "New or improved behavior" --force
gh label create type/docs             -R "$R" -c 006B75 -d "Documentation" --force
gh label create type/chore            -R "$R" -c BFD4F2 -d "Maintenance, no behavior change" --force
gh label create type/ci               -R "$R" -c 5319E7 -d "Build, test, or release plumbing" --force
gh label create priority/high         -R "$R" -c D93F0B --force
gh label create priority/medium       -R "$R" -c FBCA04 --force
gh label create priority/low          -R "$R" -c C2E0C6 --force
gh label create effort/small          -R "$R" -c EDEDED --force
gh label create effort/medium         -R "$R" -c D4D4D4 --force
gh label create effort/large          -R "$R" -c BBBBBB --force
gh label create status/needs-triage   -R "$R" -c FEF2C0 -d "Not yet understood, or not yet decided" --force
gh label create status/blocked        -R "$R" -c 000000 -d "Waiting on something named in a comment" --force
```

Then migrate the legacy schemes named in `conventions.md` § 4. For each
mapping, relabel the issues that carry the old label before deleting it:

```bash
# example: prox severity:high -> priority/high
OLD="severity:high"; NEW="priority/high"; failed=0
for n in $(gh issue list -R "$R" --state all --label "$OLD" --limit 400 --json number --jq '.[].number'); do
  gh issue edit "$n" -R "$R" --add-label "$NEW" --remove-label "$OLD" || failed=1
done
# only delete once nothing carries it any more
remaining=$(gh issue list -R "$R" --state all --label "$OLD" --limit 1 --json number --jq 'length')
if [ "$failed" = 0 ] && [ "$remaining" = 0 ]; then
  gh label delete "$OLD" -R "$R" --yes
else
  echo "KEEPING $OLD: $remaining issue(s) still carry it"
fi
```

**Never delete on the strength of the loop having run.** A failed edit
mid-loop leaves issues carrying a label you are about to destroy, and the
labelling is then lost with no record of which issues had it. Re-check the
count and delete only on zero. Note `--limit` defaults to 30, so pass one
large enough for the repo.

Report how many issues moved per mapping.

`question` has no `type/` equivalent and is dropped rather than mapped. If
a repo actually uses it, do not delete it silently: re-label those issues
`type/docs` where they are answered documentation gaps, or leave the label
in place and say so. An unused `question` label is safe to delete outright.

Finally, remove the stock labels the convention drops. `good first issue`
and `help wanted` go **regardless of usage** — these repos are public but
are not seeking contributors, so the labels are actively misleading. For
`bug`, `enhancement`, `documentation` and `question`, migrate any issues
onto the `type/` axis first, then delete. **Ask before deleting** —
deletion is not reversible:

```bash
gh label list -R "$R" --limit 100 --json name,description
gh issue list -R "$R" --state all --label "<name>" --limit 1 --json number
```

Leave dependabot's labels (`dependencies`, `github_actions`, `rust`,
language names) alone — they are machine-owned.

## 3. Provision the epics board — only with `--epics`, and only with `project` scope

Look for an existing board before creating one, and match on the title
rather than assuming a number:

```bash
gh project list --owner "$OWNER" --format json \
  --jq '.projects[] | select(.title=="StrideLabs Epics") | {number, id}'
```

If a board named `StrideLabs Epics` exists, reuse it — **never create a
second**. Otherwise:

```bash
gh project create --owner "$OWNER" --title "StrideLabs Epics"
```

Then ensure the custom fields from `references/epic-model.md` exist.
Discover them by **name and type together** — a field that exists with the
wrong type must be reported, never silently reused, because every later
`item-edit` against it will fail:

```bash
gh project field-list "$N" --owner "$OWNER" --format json \
  --jq '.fields[] | {name, type, id}'
```

Create only what is missing: `Epic` and `Phase` as `SINGLE_SELECT`,
`Blocked by` as `TEXT`. Adding *options* to a field that already exists is
a GraphQL operation and is destructive if done partially — see
`epic.md` § 3.

Three names are already taken by built-ins and must not be recreated:
`Status`, `Repository`, and — the one that surprises — **`Milestone`**,
which Projects v2 ships to mirror each issue's native repo milestone.
That collision is why the epic's own sequencer is called `Phase`.

Field *values* are per-epic and are added by `/issue-workflows:epic`, not
here. This step only guarantees the board and its field shapes.

Finally, give the board its index view. Rename the stock `View 1` to
`All epics`, leave it unfiltered and default, and replace its stock
columns — the defaults (Assignees, Linked pull requests, Sub-issues
progress) are empty for every epic item:

```bash
# Field and view IDs come from field-list and the views query above.
# The [ID!] list must go in as JSON: repeated -F flags do not build an
# array, and -F f='["a","b"]' passes the whole string as one id.
IDS=$(printf '%s\n' "$TITLE_ID" "$EPIC_ID" "$PHASE_ID" "$STATUS_ID" \
        "$REPO_ID" | jq -R . | jq -s -c .)

jq -n --arg v "$VIEW_ID" --argjson ids "$IDS" \
  '{query:"mutation($v:ID!,$ids:[ID!]){updateProjectV2View(input:{viewId:$v,name:\"All epics\",layout:TABLE_LAYOUT,filter:\"\",configuration:{visibleFieldIds:$ids}}){projectV2View{name}}}",
    variables:{v:$v, ids:$ids}}' \
  | gh api graphql --input -
```

Then set **Slice by `Epic`** on it — the sidebar that makes one board hold
many epics. That step is **browser-only**; so is the per-epic grouping in
`/issue-workflows:epic`. See `references/epic-model.md` § Projects v2
limits for why, and for the three other API gaps that shape what a view
can do. Do not report a view as configured until its grouping or slicing
has been saved and survives a reload.

## 4. Report

State plainly, per repo: labels created, issues migrated by mapping, stock
labels removed or left, and whether the board was created or reused. If
step 1 skipped the board, end by repeating the one command the user needs
and that it is per machine.
