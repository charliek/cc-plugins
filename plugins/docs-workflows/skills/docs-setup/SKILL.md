---
name: docs-setup
description: >-
  Stand up a documentation site for a repo that does not have one yet, built
  with Zensical and published to GitHub Pages: zensical.toml, a docs/ skeleton,
  a uv "docs" dependency group, both GitHub Actions workflows, and .gitignore
  entries. Use when asked to "set up docs", "add a documentation site", "add
  docs to this repo", "publish docs to GitHub Pages", "scaffold documentation",
  or "add a zensical site" — and when a repo has documentation Markdown but no
  site generator wired up. If the repo already has an mkdocs.yml, this is the
  WRONG skill: use docs-migrate instead. Do NOT use this skill for writing or
  authoring documentation content (that is ordinary writing, not tooling), and
  do NOT use it for Docusaurus, Sphinx, Jekyll, Hugo, VitePress, MkDocs, or any
  other generator — it only sets up Zensical.
---

# Set up a Zensical documentation site

Scaffolds a documentation site the house way. Written against **Zensical
0.0.52**, which is **pre-1.0** — re-verify against the current release before
trusting the templates.

## When this is the wrong skill

| Situation | Do this instead |
|---|---|
| Repo has `mkdocs.yml` | Use `docs-workflows:docs-migrate` |
| Repo already has `zensical.toml` | Nothing to set up — see Preflight |
| User wants docs *written*, not a site built | Just write the docs |
| Repo uses Docusaurus / Sphinx / Jekyll / Hugo | Out of scope; say so |

## Preflight — never overwrite

Check all of these before writing anything. If **any** exists, stop and report
what you found rather than overwriting:

```bash
ls zensical.toml mkdocs.yml docs/ 2>/dev/null
ls .github/workflows/docs.yml .github/workflows/docs-pr.yml 2>/dev/null
grep -n 'docs = \[' pyproject.toml 2>/dev/null
```

- `mkdocs.yml` present → stop, redirect to `docs-migrate`.
- `zensical.toml` present → the site is already set up. Report that and stop;
  re-running must be a no-op, not a duplicator.
- Anything else present → report and ask before proceeding.

The repo needs `uv` and a `pyproject.toml`. If there is no `pyproject.toml`,
create a minimal one (a `[project]` table with `name`, `version`,
`requires-python` is enough) — a bare dependency-group snippet cannot stand on
its own.

## Steps

### 1. Config

Copy `templates/zensical.toml.template` to `zensical.toml` and substitute:

| Placeholder | Value |
|---|---|
| `{{SITE_NAME}}` | usually the repo name |
| `{{SITE_DESCRIPTION}}` | one line, used in `<meta name="description">` |
| `{{SITE_AUTHOR}}` | e.g. `<project> Contributors` |
| `{{SITE_URL}}` | `https://<owner>.github.io/<repo>/` — trailing slash matters |
| `{{REPO_NAME}}` | `<owner>/<repo>` |
| `{{REPO_URL}}` | `https://github.com/<owner>/<repo>` |
| `{{LOGO_ICON}}` | an icon from the bundled sets, e.g. `material/console` |
| `{{DEV_PORT}}` | local preview port, pick an unused one |

Everything else in the template is a **house default** — theme variant,
feature list, palette, extensions, `site_dir = "site-build"`. Do not change
them without a reason; they are what makes the fleet consistent.

Icon sets available: `fontawesome`, `lucide`, `material`, `octicons`,
`simple`.

### 2. Dependency group

Merge `templates/pyproject-docs-group.toml.template` into `pyproject.toml`,
then:

```bash
uv sync --group docs
```

Commit the resulting `uv.lock`. Zensical is 0.0.x and moves fast, so the
lockfile is what makes builds reproducible.

### 3. Docs skeleton

Create `docs/index.md` at minimum. Add a `nav` to `zensical.toml` only if you
want an order different from the directory structure — Zensical derives
navigation from `docs_dir` when `nav` is absent.

### 4. Workflows

Copy both templates, dropping the `.template` suffix:

- `templates/docs.yml.template` → `.github/workflows/docs.yml` (publishes on
  push to `main`)
- `templates/docs-pr.yml.template` → `.github/workflows/docs-pr.yml` (strict
  build on PRs)

Both build `--strict` and both watch `uv.lock` in their `paths:` filters.

**Verify every action ref resolves before committing** — checking the latest
*release* is not the same as checking that a moving major *tag* exists.
`astral-sh/setup-uv` publishes `v9.0.0` but no bare `v9`, which fails CI with
"unable to find version". `actionlint` does **not** catch this; it validates
syntax only.

```bash
for ref in actions/checkout@v7 astral-sh/setup-uv@v9.0.0 \
           actions/upload-pages-artifact@v5 actions/deploy-pages@v5; do
  r="${ref%@*}"; t="${ref##*@}"
  printf '%-38s ' "$ref"
  gh api "repos/$r/git/ref/tags/$t" --jq .ref 2>/dev/null || echo MISSING
done
```

### 5. .gitignore

Append idempotently — check before adding, so a second run does not duplicate:

```gitignore
# Docs build output
site-build/

# Zensical differential-build cache (root only)
/.cache/
```

The `/.cache/` anchor matters: unanchored, it would also swallow a nested
`testdata/.cache/`.

### 6. GitHub Pages setting — manual, tell the user

Repository **Settings → Pages → Source** must be set to **GitHub Actions**.
This cannot be done from the repo tree. Say so explicitly; the workflow will
run and fail to deploy otherwise.

### 7. Verify

```bash
uv run --locked zensical build --strict   # must exit 0
uv run zensical serve                     # preview on {{DEV_PORT}}
```

Do not treat "the serve process started" as success — load a page and check
the content is there.

## House documentation conventions

These are carried in the template's header comment so they stay with the repo.
New docs should follow them:

- Professional, direct tone; no marketing language.
- Tables for all CLI options and configuration fields.
- Code blocks with language hints (`yaml`, `bash`, `json`).
- Admonitions sparingly — only for genuinely important notes and warnings.
- Examples must be copy-pasteable.
- One topic per page; keep pages focused and concise.
- No deep troubleshooting guides — minimal but useful.

## Zensical gotchas

- **Unknown config keys are silently ignored, even under `--strict`.** A
  literal `totally_bogus_key = "xyzzy"` builds clean. A green build does not
  prove your config edit did what you meant — read the rendered output.
- **`pymdownx.emoji` callables must use the `zensical.extensions.emoji`
  namespace.** The Material for MkDocs `material.extensions.emoji` namespace
  aborts the build with `ModuleNotFoundError: No module named 'material'`.
- **`exclude_docs` is unsupported and silently ignored.** There is no
  supported way to keep a file in `docs_dir` out of the published site — move
  it out of `docs_dir` instead.
- **`serve --strict` is unsupported.** Verify with `build --strict`.
- `--strict` fails the build on broken links *and* broken heading anchors.
  This is a feature; it is why both workflows use it.
