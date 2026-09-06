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

## 6. Report

Print the board URL, a table of ID → issue URL, and — most usefully — the
items with no unmet dependencies, because those are what can start now.

## Extending an existing epic

Same command. Reuse the `Epic` value, allocate IDs that do not collide
with existing ones, and say explicitly which items are new.
