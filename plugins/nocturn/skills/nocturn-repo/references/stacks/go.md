# Go

Standards: `conventions.yaml` and `rules.yaml` in the nocturn install. The
baseline is in `baseline.yaml` and moves (at the time of writing: Go 1.27,
golangci-lint 2.13.2, goreleaser 2.15.3).

## Files nocturn reads

- `go.mod`: the manifest path (there is no lockfile entry; `go.sum` is not a
  path). Pins come from its `go` and `toolchain` lines.
- `.mise.toml`: `go = "1.27.1"`. `.tool-versions`: `golang 1.27.1`.
- Workflows: `actions/setup-go` `go-version` or `go-version-file`;
  `golangci/golangci-lint-action` and `goreleaser/goreleaser-action` `version`.

## Conform to

- `toolchain-pinned` (warn): a concrete Go pin. `go 1.27` plus `toolchain
  go1.27.1` in `go.mod` counts.
- Rule `go-runtime`: critical when the minor is end of life; warn when behind
  the baseline by a minor, unpinned, or inconsistent. Move `go.mod` (`go` and
  `toolchain` lines), `.mise.toml`, and every `setup-go` together.
- `dependabot-config`: `gomod` at each directory with a `go.mod` (not under a
  test directory), `github-actions` at `/`, `docker` per Dockerfile
  directory. Weekly, grouped.
- `libraries-direct`: direct modules not a major behind latest.
- Shared: `gate-command` (`make check` or the project's gate, such as `make
  lint test build` set centrally), `ci-on-pull-requests`,
  `agent-instructions`.
- Nocturn's own repos use `make lint && make test && make build` and keep
  `go mod tidy` clean; match what `CLAUDE.md` says.

## File mapping

- A shipped CLI or service: `ships: [go.mod]` (or `sub/dir/go.mod`) on its
  target; a CLI with goreleaser uses `released: { tag_pattern, homebrew }`.
- Multi-module repo: list each shipping `go.mod`; give tool or test modules a
  role (or put them under a test directory).
- A docs-only `uv.lock` (zensical docs group) is `build-tool`.
