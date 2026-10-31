# Rust

Standards: `conventions.yaml` and `rules.yaml` in the nocturn install. The
baseline is in `baseline.yaml` and moves; read it from the install when you
need the number (at the time of writing, Rust 1.97.1).

## Files nocturn reads

- `Cargo.lock`: the manifest path for libraries. Workspace members' Cargo.toml
  don't count separately; one `Cargo.lock` at the workspace root.
- `rust-toolchain.toml`: `[toolchain] channel = "1.97.1"`. Pin an exact
  version. `stable`, `beta` and `nightly` read as unpinned.
- `.mise.toml` `[tools] rust = "1.97.1"` also counts. Workflows pinning Rust
  must agree with the file (`inconsistent` is a warning).

## Conform to

- `toolchain-pinned` (warn): a concrete Rust pin in `rust-toolchain.toml` or
  `.mise.toml`.
- Rule `rust-runtime` (warn): behind the baseline by a patch, unpinned, or
  inconsistent between files. Move every pin together. There is no EOL band,
  since endoflife.date marks every release but the newest as EOL.
- `dependabot-config`: `.github/dependabot.yml` with `cargo` at each directory
  that has a `Cargo.toml` outside a workspace (the workspace root once), plus
  `github-actions` at `/`, plus `docker` for each Dockerfile directory. All
  `interval: weekly` with `groups:`.
- `libraries-direct` (warn: a major behind latest): direct dependencies
  current. `stridelabs-rust` is an internal library graded by tags behind
  (warn at 1, critical at 5): bump its tag.
- Shared: `gate-command`, `ci-on-pull-requests`, `agent-instructions`
  (see SKILL.md).

## File mapping

- The deployed or released crate's `Cargo.lock` goes in a target's `ships`.
- A second, standalone `Cargo.lock` for a test tool or harness goes under
  `lockfiles` as `test` (automatic if under `tests/`).
- A frontend `bun.lock` that the backend Dockerfile builds into the image also
  goes in that target's `ships`.
