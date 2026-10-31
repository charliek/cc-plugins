# .nocturn.yaml

At the repo root. Schema version 1. Parsed strictly: an unknown key is an
error. Nocturn reads it at the scanned commit (default branch).

```yaml
version: 1
targets:
  server:
    kind: web-service
    cloud_run: { service: myapp, container: app, image: stridelabs/myapp-rs }
    ships: [backend/Cargo.lock, frontend/bun.lock]
  cli:
    kind: cli
    released: { tag_pattern: '^v\d+\.\d+\.\d+$', homebrew: myapp }
    ships: [go.mod]
lockfiles:
  conformance/bun.lock: { role: test }
  backend/uv.lock: { role: retiring, until: 2026-12-01, note: "Python, until the Rust cutover" }
services_ignored: ["myapp-staging", "*-staging"]
```

## version

Must be `1`.

## targets

A map from target name to a target. A name matches `^[a-z0-9][a-z0-9-]*$`.
A target is something the repo ships. If the project has the same target name
in `projects.yaml`, the file's target replaces it whole. A repo with no file
falls back to the central targets.

| Key | Meaning |
|---|---|
| `kind` | Required. One of `cli`, `library`, `web-service`, `web-frontend`, `desktop`, `mobile`, `docs`, `infra`, `plugin`. |
| `cloud_run` | `{ service, container, image }`. Maps the target to one Cloud Run service. |
| `released` | `{ tag_pattern, homebrew }`. Shipped as tagged releases. |
| `ships` | Lockfiles the target delivers (repo-relative). |

Rules:

- Set at most one of `cloud_run` and `released`. A target with neither is not
  tracked, but its `ships` still count as shipping.
- `cloud_run.service` is required. `container` names the app container when a
  service has several (the sidecar-free one that runs your code). `image` is
  the image path the container should run, without registry host, tag or
  digest, matching `^[a-z0-9][a-z0-9._/-]*$`. Leave `image` out if you aren't
  sure what production runs; a wrong value is a finding every night.
- `released.tag_pattern` is a Go regexp, required. `homebrew` is the formula
  name.
- Two Cloud Run services means two targets (`server`, `worker`). There is no
  multi-service form.
- Not allowed in the file: `region`, `gcp_project`, `homebrew_tap`. They are
  central defaults; the parser rejects them.

## ships and lockfile paths

- A path is the component's manifest path: the lockfile (`Cargo.lock`,
  `uv.lock`, `bun.lock`, `bun.lockb`, `package-lock.json`, `yarn.lock`,
  `pnpm-lock.yaml`, `poetry.lock`, `pubspec.lock`, `Gemfile.lock`), or `go.mod` for Go.
  Go has no lockfile entry; `go.sum` is not a path.
- Clean, slash-separated, relative to the repo root: no leading `/`, no `..`,
  no `./`, no backslash.
- Each path must exist in the repo as one of those files (`check` fails otherwise).
- Several targets may ship the same lockfile.
- A path in `ships` can't also be in `lockfiles` (invalid).

## lockfiles

Every lockfile that no target ships needs an entry here, except lockfiles
under a `test`, `tests`, `test-fixtures`, `testdata` or `examples` directory
at any depth. Those are already scoped test.

| Role | Use for |
|---|---|
| `test` | Test harnesses, evals, conformance suites. |
| `build-tool` | Used to build or release but copied into no artifact: fastlane `Gemfile.lock`, a docs-site `uv.lock`. |
| `example` | Sample projects. |
| `legacy` | Old code kept around, not shipping. |
| `retiring` | Being removed, and no longer the shipping path. Needs `until: YYYY-MM-DD`. It stops counting as shipping at once, so don't use it for code that still ships and is only planned to go. |

Rules:

- A role means the lockfile does not ship, so its libraries score as not
  shipping. Roles apply to libraries only; the runtime pins stay counted.
- `retiring` needs `until`. Any other role with `until` is invalid.
  After `until` (from the next day) the lockfile ships again and `check`
  exits 1 with "retiring until ... has passed".
- `note` is free text. Use it for why.
- An unlisted lockfile falls back to its scope and fails `repo-file-current`.
  A gap never hides risk.
- A role lowers risk for a lockfile, so be honest: dev-only packages inside a
  shipping lockfile need no role (scope handles them).

## services_ignored

A list of Cloud Run service names or globs (`path.Match`, so `*` matches within
a name) that are not targets. The nightly check flags any service whose name is
the repo name or starts with `<repo>-`, if no target names it and
`services_ignored` doesn't match it. List staging and idle services here, with
a comment.

## What stays out of the file

Project list, tags, `enabled`, gate command and timeout, GCP project, region,
Homebrew tap, waivers. Waivers live in `rules.yaml` because an agent could
otherwise edit a repo file to silence its own finding.

## Comments

Keep a short comment above each target and role saying where the evidence is
(`release-android.yml builds ...`, `Dockerfile never copies it`). The real
files do; the next maintainer needs it.

## Example: Rust server, Flutter app, retiring Python

```yaml
version: 1
targets:
  server:
    kind: web-service
    cloud_run: { service: slaudio, container: app, image: stridelabs/slaudio-rs }
    ships: [backend-rs/Cargo.lock, frontend/bun.lock]
  worker:
    kind: web-service
    cloud_run: { service: slaudio-restate-rs, container: handler, image: stridelabs/slaudio-rs }
    ships: [backend-rs/Cargo.lock]
  android:
    kind: mobile
    ships: [mobile/pubspec.lock]
lockfiles:
  backend/uv.lock: { role: retiring, until: 2026-12-01, note: "Python backend, retired in favor of backend-rs" }
  conformance/bun.lock: { role: test }
  mobile/android/Gemfile.lock: { role: build-tool }
services_ignored:
  - slaudio-restate
  - "*-staging"
```

## Example: Go CLI released with Homebrew

```yaml
version: 1
targets:
  cli:
    kind: cli
    released: { tag_pattern: '^v\d+\.\d+\.\d+$', homebrew: prox }
    ships: [go.mod]
lockfiles:
  uv.lock: { role: build-tool }   # docs group only: builds the site, ships in no artifact
```
