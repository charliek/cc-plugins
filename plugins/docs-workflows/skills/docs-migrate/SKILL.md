---
name: docs-migrate
description: >-
  Port an existing Material for MkDocs documentation site to Zensical:
  translate mkdocs.yml into a native zensical.toml, swap the uv dependency
  group, rewrite both GitHub Actions workflows, delete mkdocs.yml, and verify
  the migration by comparing the generated page set and heading anchors
  against the pre-migration build. Use when asked to "migrate to Zensical",
  "move off MkDocs", "port the docs site", "replace mkdocs-material",
  "modernize the docs toolchain", or "set up docs" in a repo that already has
  an mkdocs.yml. If the repo has NO docs tooling at all, this is the wrong
  skill: use docs-setup instead. Do NOT use this skill for writing or
  authoring documentation content, and do NOT use it to migrate Docusaurus,
  Sphinx, Jekyll, Hugo, or VitePress sites — it only handles MkDocs to
  Zensical.
---

# Migrate a Material for MkDocs site to Zensical

Written against **Zensical 0.0.52**, which is **pre-1.0** — re-verify against
the current release before trusting this procedure.

Material for MkDocs entered maintenance mode in November 2025 with a
commitment to critical-bug and security fixes for *at least* 12 months.
Zensical is the successor from the same team.

## When this is the wrong skill

| Situation | Do this instead |
|---|---|
| Repo has no `mkdocs.yml` and no site | Use `docs-workflows:docs-setup` |
| Repo already has `zensical.toml` | Already migrated |
| User wants docs *written* | Just write the docs |
| Docusaurus / Sphinx / Jekyll / Hugo | Out of scope; say so |

## The one rule that matters

**Zensical silently ignores unknown config keys, even under `--strict`.** A
literal `totally_bogus_key = "xyzzy"` in `zensical.toml` produces
"No issues found".

So a clean build proves **nothing** about whether you translated the config
correctly. You must reconcile keys by hand and diff the output. Everything
below is built around that fact.

## Preflight — stop conditions

Read the existing `mkdocs.yml` fully, then check:

```bash
grep -nE '^(plugins|exclude_docs|hooks):' mkdocs.yml
grep -n 'custom_dir' mkdocs.yml
grep -n 'docs = \[' pyproject.toml
```

**Stop and report** — do not migrate — if any of these are present:

| Found | Why it blocks |
|---|---|
| `exclude_docs:` | **Unsupported and silently ignored.** Pages the repo deliberately withholds would start being published. There is no Zensical equivalent; the fix is to move those files out of `docs_dir`, which is a content decision for the user. |
| Any plugin other than `search` | Plugin support is partial. Check the plugin against Zensical's docs before proceeding. |
| `hooks:` | No equivalent. |
| `theme.custom_dir` | Template overrides need MiniJinja adjustments; hand-review required. |

`search` on its own is fine — it disappears, because search is built into
Zensical.

The repo should use `uv` with a `docs` dependency group. If it uses plain pip
or a different layout, adapt rather than assuming.

**Parsing trap:** `mkdocs.yml` uses `!!python/name:` YAML tags. PyYAML
`safe_load` and `yq` **throw** on these. Use `yaml.BaseLoader` or register an
unknown-tag handler if you parse the file programmatically.

## Procedure

### 1. Capture the baseline — before changing anything

```bash
uv run --locked mkdocs build --strict -d /tmp/verify/mkdocs
(cd /tmp/verify/mkdocs && find . -name '*.html' | sort) > /tmp/verify/pages-before.txt
wc -l < /tmp/verify/pages-before.txt
```

If this fails, fix the existing site first. You cannot verify a migration
against a broken baseline.

### 2. Translate the config

Work through `references/mkdocs-to-zensical.md` key by key. Produce
`zensical.toml`, and produce a **reconciliation table** as you go — every key
in `mkdocs.yml` gets a row saying where it went or why it disappeared. This
table is the deliverable that catches silent key-dropping.

**Adopt the shared theme rather than translating the look.** The palette,
font stack and feature toggles do *not* get carried across — they come from
[stridelabs-docs-theme](https://github.com/charliek/stridelabs-docs-theme).
Translating them into the new config defeats the point: the fleet would drift
again on the next restyle. So:

- `theme.palette`, `theme.font`, `theme.features` → **drop**, the theme owns
  them
- `theme.icon.logo` → **keep**, it is what identifies this project beside the
  shared owl
- add `name = "stridelabs"` under `[project.theme]`

Note the theme sets `font: false` and self-hosts its faces. Carrying a
`font.text` / `font.code` setting across re-enables Zensical's Google Fonts
`<link>` and reintroduces a third-party request on every page.

The three *content* translations that are not mechanical:

- **`theme.name: material`** → `[project.theme] variant = "modern"`. Pin it
  explicitly. `"classic"` reproduces the Material look if the repo wants no
  visual change.
- **`pymdownx.emoji`** → the callable namespace changes from
  `material.extensions.emoji.*` to `zensical.extensions.emoji.*`. Keeping the
  old one aborts with `ModuleNotFoundError: No module named 'material'`. This
  is the only *loud* failure in the whole migration.
- **`validation:`** → delete it. Zensical validates links and anchors natively
  and `--strict` aborts on them, which is stronger than MkDocs' warn-only
  default. Make sure both workflows then use `--strict`.

Carry any `# Documentation Style Guidelines` header comment across verbatim —
it is guidance for future sessions and losing it is a silent regression.

### 3. Sequence the commits so none is broken

Deleting `mkdocs.yml` before rewriting the workflows leaves commits whose docs
CI points at a config that does not exist. Instead:

1. **Additive commit** — add `zensical.toml`, add `/.cache/` to `.gitignore`.
   MkDocs still works. Both generators build.
2. **Atomic cutover commit** — dependency group + lockfile + both workflows +
   `rm mkdocs.yml`, together.

### 4. Swap the toolchain

```toml
[dependency-groups]
docs = [
    "zensical>=0.0.52",
    "stridelabs-docs-theme",
]

[tool.uv.sources]
stridelabs-docs-theme = { git = "https://github.com/charliek/stridelabs-docs-theme", tag = "v0.2.0" }
```

Check the theme's current tag first:

```bash
gh release view --repo charliek/stridelabs-docs-theme --json tagName -q .tagName
```

Drop `mkdocs`, `mkdocs-material`, **and** `pymdown-extensions` — the last
arrives transitively via `zensical`, and pinning it twice invites conflicts.
Regenerate `uv.lock` and confirm `grep -c mkdocs uv.lock` is `0`.

### 5. Rewrite both workflows

Use `docs-setup`'s templates as the target shape. Changes from the MkDocs
versions:

- `uv run mkdocs build` → `uv run --locked zensical build --strict`
- `paths:` filter `mkdocs.yml` → `zensical.toml`
- add `uv.lock` to the **publish** workflow's `paths:` filter if missing —
  repos often have it only on the PR workflow, so a lockfile-only bump never
  redeploys
- `--strict` on **both**, not just the PR build

Keep `site_dir`/artifact path as-is (`site-build` in this fleet) unless you
have a reason to churn it.

**Verify every action ref resolves** — via the git refs API, not the releases
API. `astral-sh/setup-uv` publishes `v9.0.0` but no moving `v9` tag, and
`actionlint` will not catch it:

```bash
gh api repos/astral-sh/setup-uv/git/ref/tags/v9.0.0 --jq .ref
```

### 6. Sweep stale references

The migration breaks any documented `mkdocs` command. Check the whole repo,
not just the config:

```bash
grep -ril mkdocs . | grep -v site-build | grep -v '\.git/'
```

Typical hits: `README.md` and `docs/development/setup.md` (both usually carry
a "uses MkDocs with Material theme" blurb plus `uv run mkdocs serve` /
`mkdocs build`), and a passing mention in `RELEASING.md` or `CONTRIBUTING.md`.

**Check the `Makefile` too** — it is the hit most easily missed, because
`docs:` / `docs-serve:` targets are real invocations that break silently until
someone runs them. Point them at the same commands CI uses, `--locked`
included:

```make
docs:  ## Build the docs site into site-build/ (same as CI)
	uv sync --locked --group docs && uv run --locked zensical build --strict

docs-serve:  ## Serve the docs locally with live reload
	uv sync --locked --group docs && uv run --locked zensical serve
```

**Do not edit `CHANGELOG.md` history.** Old entries describing the MkDocs
setup are accurate history.

### 6a. Fill fleet gaps rather than porting them forward

Older configs are often missing keys their siblings have. A pure translation
faithfully reproduces the gap. Check for and add:

| Missing key | Consequence of leaving it out |
|---|---|
| `theme.icon.logo` | no project mark beside the shared owl — the header cannot say *which* tool this is |
| `site_author` | `<meta name="author">` renders empty on every page |
| `edit_uri` | no "edit this page" links |
| trailing slash on `site_url` | canonical URLs take a non-standard form |

Call these out explicitly in the PR — they are deliberate additions, not part
of the mechanical translation, and a reviewer diffing key-for-key will
otherwise wonder where they came from.

### 7. Verify — the part that is not optional

`zensical build` has **no `-d` / `--dir` flag** — its only options are
`-f/--config-file`, `-c/--clean`, `-s/--strict`. Output always goes to
`site_dir`, so build in place and copy the result aside to compare:

```bash
uv run --locked zensical build --clean --strict   # -> site_dir (site-build/)
cp -R site-build /tmp/verify/zensical
diff <(cd /tmp/verify/mkdocs   && find . -name '*.html' | sort) \
     <(cd /tmp/verify/zensical && find . -name '*.html' | sort)
```

Note `--clean` cleans the *cache*, not the output directory. `rm -rf site-build`
first if a stale page could otherwise linger and mask a removal.

**Compare HTML pages only.** Do *not* diff the full file tree: MkDocs ships
~40 `lunr/*` search files and Zensical ships the Disco worker, so the asset
trees legitimately differ. Only the page set is a valid cross-generator
comparison.

Then check heading anchors, so inbound deep links do not break:

```python
import re
ids = lambda p: re.findall(r'<h[1-6][^>]*id="([^"]+)"', open(p).read())
# compare ids() for the same page in both builds; they should match exactly
```

And `<head>` metadata (`description`, `author`, `canonical`) on a sample page.

Confirm the theme actually applied — a missing theme still builds clean and
renders as stock Zensical:

```bash
grep -c 'sl-lockup'  site-build/index.html   # owl + project icon header
grep -c 'css/fonts.css' site-build/index.html
ls site-build/fonts/*.woff2 | wc -l          # self-hosted faces copied
grep -c 'fonts.googleapis\|fonts.gstatic' site-build/index.html   # must be 0
```

**Expected, benign delta:** `<title>` comes from the nav title under MkDocs
but from the page `<h1>` under Zensical, so `CLI - proj` becomes
`CLI Reference - proj`. A page whose `<h1>` equals the site name renders as
`name - name` (MkDocs special-cased that). Cosmetic.

Finally, load the site in a browser **at its published sub-path**, not root —
`http://127.0.0.1:<port>/<repo>/`. Root-vs-subpath asset and search-worker
URLs are a classic Pages breakage. Check: nav sections all present, search
returns results, dark-mode toggle works and survives a reload, no console
errors.

### 8. Record it

Add a CHANGELOG entry if the repo keeps one. Note in `CLAUDE.md` (or
equivalent) that the docs build is `uv run --locked zensical build --strict`
and that it is **not** part of the repo's main per-commit gate — otherwise the
next session either folds it into every commit or assumes the main gate covers
docs.

## Gotcha summary

| Gotcha | Consequence |
|---|---|
| Unknown keys silently ignored under `--strict` | A wrong config builds clean |
| `exclude_docs` unsupported, silently ignored | Withheld pages get published |
| `material.extensions.emoji.*` namespace | Build aborts, `ModuleNotFoundError` |
| `serve --strict` unsupported | Verify with `build --strict` |
| `build` has no `-d` flag | `Error: No such option '-d'`; build to `site_dir`, copy aside |
| `build --clean` cleans the *cache* | Not the output dir; `rm -rf site-build` to be sure |
| `Makefile` `docs:` targets | Missed by a config-only sweep; break silently |
| `!!python/name:` tags | `yaml.safe_load` / `yq` throw |
| No moving `v9` tag for `setup-uv` | CI "unable to find version" |
| `actionlint` passes on bad action tags | It checks syntax, not existence |
| Full file-tree diff across generators | False alarm; compare pages only |
