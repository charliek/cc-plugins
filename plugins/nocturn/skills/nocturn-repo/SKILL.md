---
name: nocturn-repo
description: >-
  Maintain a repository's own Nocturn contract: write or update its
  .nocturn.yaml, onboard a repo to Nocturn, and make a Rust, Go, Python,
  JavaScript or Flutter/Android repo conform to the fleet's standards (pinned
  toolchains, dependabot.yml, gate command, CI on pull requests, CLAUDE.md).
  Use when working inside a repo and asked to add or edit .nocturn.yaml, to
  onboard it, to fix a repo-file or repo-file-current finding, or after a
  change that moves what the repo ships: a cutover, a moved or renamed
  directory, a new or retired lockfile, a retired Cloud Run service, a new
  deploy target. Also when `nocturn repo check` fails. Do NOT use it to
  operate the fleet (scores, focus items, proposals, decisions, runs, jobs):
  that is the `nocturn` skill embedded in the nocturn binary.
---

# nocturn-repo

Nocturn scores each repo nightly. It reads `.nocturn.yaml` at the repo root to
learn what the repo ships. The rule: **the repo describes, the install
decides.** The repo says what it ships and what its other lockfiles are for.
The project list, tags, gate, GCP project, region, Homebrew tap and waivers
stay central in the nocturn repo's `install/`, so don't look for them here.

Scope: this skill is for maintaining one repo's file and conformance. The
`nocturn` skill embedded in the `nocturn` binary keeps operating the fleet.
`nocturn repo check` is the authority: if this skill and the code disagree,
the command wins. Say so in the PR.

## Commands

Both run on a checkout, with no database and no `NOCTURN_CONFIG_DIR`.

```bash
nocturn repo inspect [dir] --json   # what's there; "unmapped" lists lockfiles the file doesn't cover
nocturn repo check [dir] --json     # validates the file; exit 0 valid, 1 not valid, 2 usage
```

- `inspect` lists lockfiles, unmapped lockfiles, Dockerfiles, workflows,
  deploy files, toolchain pins, Android apps' target SDK, ecosystems, the
  current file's state, and warnings.
- `check` fails (exit 1) when there is no file, it doesn't parse, a named path
  isn't a lockfile in the repo, a lockfile is unmapped, or a `retiring` date
  has passed. It also lists five conventions (`gate-command`,
  `dependabot-config`, `ci-on-pull-requests`, `agent-instructions`,
  `toolchain-pinned`). Those never change the exit code, but fix the failing
  ones: the nightly scorer grades them.
- Live checks (the deployed image, Cloud Run services) happen only in the
  nightly run. `check` can't see them, so read the deploy files yourself.

## Workflow

1. Run `nocturn repo inspect --json`. Read `unmapped`, `dockerfiles`,
   `deploy_files` and the workflows.
2. Write or edit `.nocturn.yaml` ([file-format.md](references/file-format.md)).
3. Fix conformance gaps for the stack ([stacks/](references/stacks/)).
4. Run `nocturn repo check --json` until it exits 0 and the conventions pass.
5. Open a normal PR. Agents can't change `.nocturn.yaml` through Nocturn's own
   runs (an edit run that touches it is refused), so a person or a coding
   agent in the repo does it, reviewed like any change.

Full onboarding, including the one line in the central `projects.yaml`, is in
[onboarding.md](references/onboarding.md).

## Stacks

Open the file for each stack the repo has:

- [rust](references/stacks/rust.md)
- [go](references/stacks/go.md)
- [python](references/stacks/python.md)
- [javascript](references/stacks/javascript.md)
- [flutter-android](references/stacks/flutter-android.md)

## When to change the file

Re-run `inspect` and `check` after any of these, in the same PR as the change:

- Lockfile added, removed, moved or renamed: update `ships` or `lockfiles`.
- Directory moved: every path in the file is a repo-relative path to a
  lockfile (`go.mod` for Go), so a move breaks `repo-file-current`.
- New or retired Cloud Run service: add or remove the target, or list the
  service in `services_ignored`.
- Image renamed or a container renamed: update `cloud_run.image` or `container`.
- Cutover (a rewrite replaces an old backend): move the old lockfile from a
  target's `ships` to `lockfiles` as `retiring` with an `until` date, or
  `legacy`. When the old code is deleted, delete the line.
- A `retiring` date nears: it ships again the day after `until`, with a
  finding. Extend the date only if the retirement really slipped; otherwise
  delete the code and the line.
- New CI-only or test-only lockfile: give it a role.

Don't use a role to hide a lockfile that does ship. Roles lower risk; the
reviewer is the check on that. An image scan is the real one.
