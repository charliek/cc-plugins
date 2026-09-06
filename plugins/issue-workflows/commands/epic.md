# Run an epic

Create or extend a cross-repo epic on the shared Projects v2 board. An
epic is a set of ordinary issues — one per work item, each in the repo
where the work happens — tied together by the board's `Epic` field. Read
`references/epic-model.md` before running this; it explains why the model
is a Project field rather than issue types or sub-issues.

`$ARGUMENTS`: the epic name, plus a source for the items — a path to a
roadmap doc, an artifact URL, or "from this conversation".

## 1. Preconditions

Requires `project` scope (`gh auth status`). If missing, stop and tell the
user to run `gh auth refresh -s project` themselves — it is interactive
and per machine.

Find the board; never create a second one:

```bash
gh project list --owner "$OWNER" --format json
gh project field-list "$N" --owner "$OWNER" --format json
```

If the board or its fields are missing, run `/issue-workflows:setup --epics`
first rather than provisioning inline.

## 2. Read the roadmap source

Extract, per item: a short **ID** unique within the epic (`R3`, `A0`,
`S7`), the **repo it lands in**, a **title**, why it matters, **acceptance
criteria**, its **size**, its **phase**, and what it **depends on**.

If the source lacks acceptance criteria for an item, write them and say
which ones you authored — an item without acceptance cannot be handed to a
session (conventions rule 2), so filing it as-is just moves the problem.

## 3. Add the epic's field values

`Epic` and `Phase` are single-select fields shared by every epic on the
board. Phases are **prefixed per epic** (`RP/M1`) because the field is
board-global. There is no `Track` field: the built-in `Repository` is the
track.

**Adding options to an existing single-select field needs GraphQL, and it
is destructive if done wrong.** `gh project field-create` only creates a
field; the CLI cannot append an option to one that exists.
`updateProjectV2Field` **replaces** the whole option list, so omitting the
current options deletes them — and clears that field on every item already
using them.

Always read first, then write the union:

```bash
gh api graphql -f query='
  query($id: ID!) { node(id: $id) { ... on ProjectV2SingleSelectField {
    id name options { id name } } } }' -f id="$FIELD_ID"
```

Send every existing option back unchanged, with the new ones appended:

```bash
gh api graphql -f query='
  mutation($f: ID!, $opts: [ProjectV2SingleSelectFieldOptionInput!]!) {
    updateProjectV2Field(input: {fieldId: $f, singleSelectOptions: $opts}) {
      projectV2Field { ... on ProjectV2SingleSelectField { options { id name } } } } }'   -f f="$FIELD_ID" -F opts="$OPTS_JSON"
```

Option **names** round-trip; the returned **ids** are what step 5 needs.
Never send a partial list.

## 4. File one issue per item

Title carries the ID: `[R3] roost: a vt payload kind, so a third-party
client can attach`. Body follows `epic-model.md`, including the
`Context:` link back to the reasoning document and the section within it —
that link is how a session picks up an item cold and understands why it
exists.

Apply `type/` and `effort/` labels as usual (`file.md` § 5). File into the
repo where the work happens, which is often not the repo you are sitting in.

Filing is the slow part; do the whole set before touching the board so a
failure halfway leaves issues without board rows rather than the reverse.

**Make it resumable.** A retry must not double-file. Before creating
anything, search the target repo for the item's bracketed ID and reuse
what is already there:

```bash
gh issue list -R "$R" --state all --search "in:title [R3]" --json number,url,title
```

Keep an ID → issue-URL map as you go and write it somewhere durable, so a
run interrupted between filing and board updates resumes from the map
rather than from scratch. The duplicate check in `file.md` § 1 searches on
prose and will not catch a re-filed epic item; the bracketed ID is what
makes this reliable.

## 5. Add each issue to the board and set its fields

`item-add` is idempotent per issue and returns the item id; re-adding an
issue already on the board returns the existing one.

```bash
ITEM_ID=$(gh project item-add "$N" --owner "$OWNER" --url "$ISSUE_URL" \
            --format json --jq '.id')
```

**Each field type takes a different flag.** One `item-edit` call per
field — a single call cannot set them all:

```bash
# Epic and Phase are SINGLE_SELECT -> --single-select-option-id
gh project item-edit --project-id "$PID" --id "$ITEM_ID" \
  --field-id "$EPIC_FIELD_ID"  --single-select-option-id "$EPIC_OPTION_ID"
gh project item-edit --project-id "$PID" --id "$ITEM_ID" \
  --field-id "$PHASE_FIELD_ID" --single-select-option-id "$PHASE_OPTION_ID"

# Blocked by is TEXT -> --text
gh project item-edit --project-id "$PID" --id "$ITEM_ID" \
  --field-id "$BLOCKED_FIELD_ID" --text "A0, R2"
```

`Repository` fills itself, size lives on the `effort/` label rather than
on the board, and `Status` stays at its default — the PR moves it.

## 6. Create the epic's two views

Every epic gets exactly two saved views, both filtered to its own `Epic`
value. `references/epic-model.md` § Views explains why it is these two and
not more — in particular why a `blocked` view **cannot** be built and why a
board view works against the `Closes` convention. Do not add either.

| Name | Group by | Visible fields, in order |
|---|---|---|
| `<Epic> — by phase` | `Phase` | Title, Status, Repository, Blocked by, Labels |
| `<Epic> — by repo` | `Repository` | Title, Status, Phase, Blocked by, Labels |

**Check first — creation is not idempotent.** `createProjectV2View` will
happily make a second view with the same name, so look the name up and
**reuse the id if it is already there**; only create when the lookup comes
back empty. Extending an epic must not add a third and fourth view.

```bash
# 100 is the per-page maximum; page with `after` if the board ever exceeds it.
# Note the pipe: gh's own --jq takes one expression and no --arg, so the
# name is matched by a real jq process instead.
NAME="$EPIC — by phase"
VIEW_ID=$(gh api graphql -f query='
  query($id:ID!){node(id:$id){... on ProjectV2{
    views(first:100){nodes{id name}}}}}' -f id="$PID" \
  | jq -r --arg n "$NAME" '.data.node.views.nodes[] | select(.name==$n) | .id')
```

Match on the **exact** name: a `by phase` view for `Roost Pivot 2` must not
satisfy the lookup for `Roost Pivot`.

**Create, then update — `createProjectV2View` accepts no `filter`.** It
takes only `projectId`, `name`, `layout` and `configuration`, so the filter
and the column set go on in a second call.

**Run this pair once per row of the table above** — the block below is the
`by phase` view; the `by repo` view is the same two calls with that row's
name and column list, and `Repository` as the grouping field. An epic with
only one view is not finished.

```bash
VIEW_ID=$(gh api graphql -f query='
  mutation($p:ID!,$n:String!){
    createProjectV2View(input:{projectId:$p,name:$n,layout:TABLE_LAYOUT}){
      projectV2View{id}}}' \
  -f p="$PID" -f n="$NAME" \
  --jq '.data.createProjectV2View.projectV2View.id')

# Column order is the order of this list.
IDS=$(printf '%s\n' "$TITLE_ID" "$STATUS_ID" "$REPO_ID" "$BLOCKED_ID" \
        "$LABELS_ID" | jq -R . | jq -s -c .)

jq -n --arg v "$VIEW_ID" --arg f "epic:\"$EPIC\"" --argjson ids "$IDS" \
  '{query:"mutation($v:ID!,$f:String!,$ids:[ID!]){updateProjectV2View(input:{viewId:$v,filter:$f,configuration:{visibleFieldIds:$ids}}){projectV2View{name filter}}}",
    variables:{v:$v, f:$f, ids:$ids}}' \
  | gh api graphql --input -
```

**The id list must go in as JSON — no `gh` flag form works.** Repeating
`-F ids=` fails outright (`unexpected override existing field under
"ids"`), and `-F ids='["a","b"]'` is worse: it passes the whole bracketed
string as a *single* id and fails with a confusing `Could not resolve to a
node with the global id of '["a","b"]'`. Build the variables as JSON and
pipe them to `--input -`. Use `--argjson` with a pre-built array rather
than jq's `--args`, whose positional list must follow the filter — putting
it before makes jq read the next word as the filter itself. The same
applies anywhere a `[ID!]` is sent.

The filter is the Projects filter language: lowercase field names, spaces
as hyphens, **multi-word values quoted** — `epic:"Roost Pivot"`. An epic
name containing a quote cannot be filtered; rename it rather than escaping.

**Then set Group by in a browser — there is no API for it.**
`ProjectV2ViewConfigurationInput` carries only `visibleFieldIds`; grouping,
sorting and slicing are browser-only. Open the view, *View* → *Group by* →
the field, then **Save view** and confirm the dialog. Picking the field
alone leaves it unsaved, and reloading throws it away.

**Verify before reporting.** Name, filter and the column *set* read back
from the API — but `fields` returns them in the project's field-definition
order, **not** in visible column order, so it can confirm which columns are
present and never their arrangement:

```bash
gh api graphql -f query='
  query($id:ID!){node(id:$id){... on ProjectV2View{name filter
    fields(first:20){nodes{... on ProjectV2FieldCommon{name}}}}}}' \
  -f id="$VIEW_ID"
```

The **item count cannot**: `ProjectV2View` has no `items` field, and the
server stores any filter string verbatim without validating it, so a filter
matching nothing is indistinguishable from one that works. Read the count
in the browser's filter bar and check it against the number of items
carrying that `Epic` value — **the whole epic, not just the items this run
added**, since an extended epic's views already hold the earlier ones. Then reload the view and confirm the grouping survived. If no browser is available, create the views anyway and report
the grouping and the count check as **outstanding manual steps**, naming
them — never as done.

## 7. Report

Print the board URL, a table of ID → issue URL, and — most usefully — the
items with no unmet dependencies, because those are what can start now.
Name any view step left for the user to finish by hand.

## Extending an existing epic

Same command. Reuse the `Epic` value, allocate IDs that do not collide
with existing ones, and say explicitly which items are new. The views
already exist — step 6 finds them by name and leaves them alone; new items
appear in them automatically because the views filter on `Epic`.
