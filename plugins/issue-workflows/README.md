# issue-workflows

Convention-based GitHub issue workflows for every `charliek` repo: file
well-formed single issues, run cross-repo epics on one shared Projects v2
board, and keep titles and labels consistent.

## Commands

| Command | What it does |
|---|---|
| `/issue-workflows:setup` | Make a machine and a set of repos ready — check the `project` token scope, create the canonical labels, migrate the legacy schemes, optionally provision the shared epics board |
| `/issue-workflows:file` | Write and file one issue following the conventions, labelled automatically |
| `/issue-workflows:epic` | Create or extend a cross-repo epic: file its items and put them on the board |
| `/issue-workflows:status` | Read an epic's cross-repo state and say what can start now |

## References

- `references/conventions.md` — the standard: title shape, body sections,
  the three label axes, and how issues get closed.
- `references/epic-model.md` — the Projects v2 field model, the views, and
  why an epic is a project field rather than an issue type or a sub-issue.

## The one thing to know

Status is not maintained by hand. A pull request writes
`Closes <owner>/<repo>#<n>`, merging closes the issue, and the board item
moves to Done by itself. If a session is editing board status manually,
the `Closes` line was missing.

Three conditions have to hold for that to work, and all three are easy to
miss:

- **The closing keyword only works within one repository.** A PR in
  `roost` cannot close an issue in `shed` by keyword — GitHub ignores the
  cross-repo form on merge. File each epic item in the repo whose PR will
  close it.
- **The board must be linked to that repo's issue** — an item added as a
  draft, rather than by issue URL, has no issue to close and will sit in
  `Todo` for ever.
- **`Status` needs its built-in workflow enabled** (Project settings →
  Workflows → *Item closed* → set `Status: Done`). It is on by default for
  a new board; confirm it when reusing one.

## Per-machine setup

The GitHub token needs `project` scope. `gh` stores it per machine (under
its config dir — `$GH_CONFIG_DIR` when set, otherwise the platform
default), so every computer needs this once:

```bash
gh auth refresh -s project
```

`/issue-workflows:setup` checks for it before anything else.
