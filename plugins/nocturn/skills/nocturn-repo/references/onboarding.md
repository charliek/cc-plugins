# Onboarding a repo

Onboarding is done by an agent in the repo, in a normal PR. No Nocturn recipe
or Claude executor is involved. `nocturn onboard` (the Dependabot template)
still exists and is separate.

## Steps

1. In the repo checkout, run:

   ```bash
   nocturn repo inspect --json
   ```

   Read `lockfiles`, `unmapped`, `dockerfiles`, `deploy_files`, `workflows`,
   `pins`, `android_apps`, `ecosystems`, `warnings`.

2. Decide what ships. For each lockfile ask: does an artifact contain it?
   - Read each Dockerfile: which `COPY` lines bring in which lockfile or
     built output (an SPA built from `frontend/bun.lock` ships through the
     backend image).
   - Read deploy files (`deploy/`, `cloudbuild.yaml`, `service.yaml`) and the
     release workflows: Cloud Run service, container and image names; tag
     patterns; `flutter build appbundle` directories; goreleaser configs.
   - Anything run only in CI, tests, docs builds or release tooling is a
     role, not a ship.
   - Don't guess the live service or image. If you can't tell, ask, or leave
     `image` out and say so in the PR.

3. Write `.nocturn.yaml` ([file-format.md](file-format.md)). Comment the
   evidence for each decision.

4. Fix the conventions `check` lists, per stack (see [stacks/](stacks/)).
   They are in `conventions.yaml` of the nocturn install:
   - `gate-command`: one command that builds, lints and tests (`make check`).
     If the repo can't have that, tell the owner: the project's gate is set
     centrally in `projects.yaml`.
   - `dependabot-config`: `.github/dependabot.yml` covers `github-actions`
     plus every package ecosystem in the repo, each weekly and grouped.
   - `ci-on-pull-requests`: a workflow runs on `pull_request`.
   - `agent-instructions`: `CLAUDE.md` or `AGENTS.md` says how to build and test.
   - `toolchain-pinned`: each language has an exact pin.

5. Run `nocturn repo check --json`. Exit 0 and no failing conventions you can
   fix. A failing convention doesn't change the exit code, but the nightly
   scorer grades it.

6. Open a PR in the repo. In the PR body list: what each target ships and the
   evidence, each role and why, anything you couldn't verify.

7. Central step, in the nocturn repo (a person or an agent working there, not
   this skill): add one line for the project to `install/projects.yaml`
   (repo, tags `project:` and practice tags, plus stack tags such as
   `flutter`). Per-project overrides and waivers live there and in
   `rules.yaml`, never in the repo file.

## Keeping it current

The nightly `repo-file-current` check fails when:

- a path the file names doesn't exist,
- a lockfile is unmapped,
- the live Cloud Run container or image doesn't match `cloud_run`,
- a Cloud Run service named for the repo is neither a target nor in
  `services_ignored`.

Fix it by editing the file in a normal PR. When changing the repo in a way
that moves what ships, change the file in the same PR (see "When to change the
file" in SKILL.md).

## Pitfalls

- Don't put `region`, `gcp_project` or `homebrew_tap` in the file: rejected.
- Don't give a path in both `ships` and `lockfiles`.
- `until` only with `retiring`; the date passing makes the lockfile ship again.
- A multi-module Go repo: each `go.mod` is its own path; list the ones that
  ship and give the others a role.
- Run `nocturn repo check` from the repo root, or pass the directory.
