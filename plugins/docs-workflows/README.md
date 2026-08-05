# docs-workflows

Documentation-site tooling for repos that publish to GitHub Pages with
[Zensical](https://zensical.org) — the successor to Material for MkDocs, from
the same team.

Two skills, split by what the repo already has:

| Repo state | Skill |
|---|---|
| No docs site yet | `docs-workflows:docs-setup` |
| Has an `mkdocs.yml` | `docs-workflows:docs-migrate` |

## Skills

### `docs-workflows:docs-setup`

Scaffolds a documentation site the house way: `zensical.toml`, a `docs/`
skeleton, a uv `docs` dependency group, both GitHub Actions workflows (publish
on `main`, strict build on PRs), and the `.gitignore` entries. Also carries the
house documentation conventions so new docs read like the rest of the fleet.

Preflight refuses to overwrite an existing setup, and re-running it is a no-op
rather than a duplicator.

Bundled templates in `skills/docs-setup/templates/`:
`zensical.toml.template`, `docs.yml.template`, `docs-pr.yml.template`,
`pyproject-docs-group.toml.template`.

### `docs-workflows:docs-migrate`

Ports an existing Material for MkDocs repo to Zensical: translates
`mkdocs.yml` to a native `zensical.toml`, swaps the dependency group, rewrites
both workflows, deletes `mkdocs.yml`, sweeps stale `mkdocs` commands from
README/setup docs, then runs a verification loop that compares the generated
page set and heading anchors against the pre-migration build.

The verification loop is not optional, because of trap #1 below.

Bundled reference: `skills/docs-migrate/references/mkdocs-to-zensical.md` — a
key-by-key mapping table covering every key observed across the fleet.

## The shared theme

Both skills wire new and migrated repos to
**[stridelabs-docs-theme](https://github.com/charliek/stridelabs-docs-theme)**,
installed as a plain git dependency from a public repo — no PyPI, no registry
auth, so forks and outside contributors can still build the docs.

The theme owns the palette, feature toggles, self-hosted type stack, and the
owl + project-icon header lockup. A repo's own `zensical.toml` therefore
carries only what is genuinely repo-specific: site metadata, nav, markdown
extensions, and `theme.icon.logo` — the icon shown beside the shared owl.

That is the point of the split: restyling ~24 sites is a tag bump in each
repo, not 24 CSS edits. `docs-migrate` explicitly **drops** a repo's existing
palette/font/feature settings rather than translating them, because carrying
them across would let the fleet drift again.

Opting a single repo out is one line — see the theme's README.

## Three traps these skills exist to encode

Verified against Zensical 0.0.52:

1. **Unknown config keys are silently ignored, even under `--strict`.** A
   literal `totally_bogus_key = "xyzzy"` builds clean. A green build is *not*
   evidence that a config was translated correctly — hence the mandatory
   key-by-key reconciliation.
2. **`exclude_docs` is unsupported and silently ignored.** Pages a repo
   deliberately withholds start getting published. `docs-migrate` stops rather
   than migrating a repo that uses it.
3. **The `pymdownx.emoji` callable namespace is a hard break.** Keeping
   `material.extensions.emoji.*` aborts with `ModuleNotFoundError: No module
   named 'material'`. The correct namespace is `zensical.extensions.emoji.*`.

Trap 3 is loud. Traps 1 and 2 are silent, which is what makes ad-hoc migration
risky and these skills worth having.

## Source of truth

The templates are derived from **`charliek/prox`**, the reference
implementation (migrated in prox plan 025, PR #103). If prox's docs setup
changes, update these templates to match — nothing enforces that automatically.

Written against Zensical **0.0.52**, which is pre-1.0. Re-verify the templates
against the current release before trusting them on a new repo.
