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

`Epic` and `Phase` are single-select fields shared by every epic on
the board. Add the new values — phases **prefixed per epic**
(`RP/M1`) because the field is board-global — and never remove another
epic's. There is no `Track` field: the built-in `Repository` is the track.

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

## 5. Add each issue to the board and set its fields

```bash
gh project item-add "$N" --owner "$OWNER" --url "$ISSUE_URL"
gh project item-edit --project-id "$PID" --id "$ITEM_ID" \
  --field-id "$FIELD_ID" --single-select-option-id "$OPTION_ID"
```

Set `Epic`, `Phase`, and `Blocked by` (free text — the IDs,
comma-separated). `Repository` fills itself, and size lives on the
`effort/` label, not on the board. Leave `Status` at its default; the PR
moves it.

## 6. Report

Print the board URL, a table of ID → issue URL, and — most usefully — the
items with no unmet dependencies, because those are what can start now.

## Extending an existing epic

Same command. Reuse the `Epic` value, allocate IDs that do not collide
with existing ones, and say explicitly which items are new.
