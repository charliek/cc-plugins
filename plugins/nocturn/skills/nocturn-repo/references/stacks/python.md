# Python

Standards: `conventions.yaml` and `rules.yaml` in the nocturn install. The
baseline is in `baseline.yaml` and moves (at the time of writing: 3.13).

## Files nocturn reads

- Lockfile: `uv.lock` (manifest path; ecosystem `uv` when it sits next to a
  `pyproject.toml`), else `pip` for a `pyproject.toml` alone, `poetry.lock`.
- `.python-version` (first line): a concrete pin, e.g. `3.13.1`.
- `pyproject.toml` `requires-python`: a floor, not a pin. It is compared with
  the baseline but does not count as the pin for `toolchain-pinned`.
- `.mise.toml`; `actions/setup-python` `python-version` in workflows.

## Conform to

- `toolchain-pinned` (warn): `.python-version` or a mise pin that is concrete.
- Rule `python-runtime`: critical at end of life; warn when behind the
  baseline by a minor, unpinned, or inconsistent between files. Keep
  `.python-version`, `requires-python`, mise and `setup-python` in step.
- `dependabot-config`: `uv` (or `pip`) at each `pyproject.toml` directory,
  `github-actions` at `/`, `docker` per Dockerfile directory, weekly, grouped.
- `libraries-direct`: direct dependencies not a major behind latest.
  `stridelabs-python` (`pkg:pypi/stridelabs-*`) is an internal library: warn
  when a tag behind.
- Lock with `uv lock`; don't edit lockfiles by hand.
- Shared: `gate-command`, `ci-on-pull-requests`, `agent-instructions`.

## File mapping

- Python that ships (a Docker image copies it): in a target's `ships`.
- Evals, scripts and tests only: `{ role: test }`.
- A `pyproject.toml` with only a docs group (the docs-site build):
  `{ role: build-tool }`; a repo-wide test harness: `test`.
- A backend being replaced: `{ role: retiring, until: YYYY-MM-DD }`.
