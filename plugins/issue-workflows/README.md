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

## Per-machine setup

The GitHub token needs `project` scope, stored in
`~/.config/gh/hosts.yml`. That is per machine, so each computer needs:

```bash
gh auth refresh -s project
```

`/issue-workflows:setup` checks for it before anything else.
