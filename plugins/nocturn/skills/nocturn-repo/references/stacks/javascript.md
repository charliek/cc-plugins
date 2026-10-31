# JavaScript and TypeScript

Standards: `conventions.yaml` and `rules.yaml` in the nocturn install. The
baseline is in `baseline.yaml` and moves (at the time of writing: bun 1.4).

## Files nocturn reads

- Lockfile: `bun.lock` / `bun.lockb` (ecosystem `bun`), `package-lock.json`,
  `yarn.lock`, `pnpm-lock.yaml` (ecosystem `npm`). The lockfile is the path in
  the repo file. Ecosystem is `bun` when a `bun.lock` sits beside the
  `package.json`.
- Pins: `.mise.toml` (`bun = "1.4.2"`, `node = "24.11.0"`), `.tool-versions`
  (`bun 1.4.2`, `nodejs 24.11.0`) and Node container image tags. A wildcard such
  as `1.4.x` is not concrete. `actions/setup-node` and `package.json` engines are
  not read, so pinning only there doesn't count.

## Conform to

- `toolchain-pinned` (warn): a `bun` ecosystem needs a concrete bun pin and an
  `npm` ecosystem a concrete node pin, usually in `.mise.toml`.
- Rule `other-runtimes` covers node and bun: critical at EOL, warn when
  inconsistent, info when unpinned. Bun also warns when a minor behind the
  baseline in `baseline.yaml`; node has no baseline entry.
- `dependabot-config`: `bun` or `npm` at each `package.json` directory,
  `github-actions` at `/`, `docker` per Dockerfile directory, weekly, grouped.
- `libraries-direct`: direct dependencies not a major behind latest. Dev
  dependencies in a shipping lockfile score as not shipping (scope), so keep
  `devDependencies` correct.
- Install with the frozen lockfile in CI (`bun install --frozen-lockfile`,
  `npm ci`).
- Shared: `gate-command`, `ci-on-pull-requests`, `agent-instructions`.

## File mapping

- A frontend built into a backend image (the Dockerfile builds the SPA):
  list its lockfile in that backend target's `ships`.
- A frontend deployed on its own: its own target, `kind: web-frontend`.
- Conformance suites, validators, scripts used only in CI: `{ role: test }`
  (automatic under `test/` or `tests/`).
- Docs-site tooling: `build-tool`.
