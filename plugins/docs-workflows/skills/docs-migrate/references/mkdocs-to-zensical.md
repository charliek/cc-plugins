# mkdocs.yml → zensical.toml key mapping

Reference for `docs-workflows:docs-migrate`. Written against **Zensical
0.0.52** (pre-1.0).

Every key below was observed in at least one real repo across a 24-repo survey
of Material for MkDocs sites. The **top-level key universe** that survey found:

```
dev_addr, docs_dir, edit_uri, exclude_docs, extra, extra_javascript,
markdown_extensions, nav, plugins, repo_name, repo_url, site_author,
site_description, site_dir, site_name, site_url, theme, validation
```

If you meet a key not in this table, it is **not** automatically safe — see
[Silent failure](#silent-failure) first.

## Silent failure

Zensical **ignores unknown config keys without error, even under `--strict`**.
Verified: a literal `totally_bogus_key = "xyzzy"` yields "No issues found".

Consequences:

- A typo'd or unsupported key is invisible. The build is green and the site is
  quietly wrong.
- You cannot use "it builds" as evidence of a correct translation.
- Reconcile every key by hand and diff the generated output.

## Site metadata

| mkdocs.yml | zensical.toml | Notes |
|---|---|---|
| `site_name: X` | `site_name = "X"` | under `[project]` |
| `site_description: X` | `site_description = "X"` | `<meta name="description">` |
| `site_author: X` | `site_author = "X"` | |
| `site_url: X` | `site_url = "X"` | trailing slash matters for sub-path Pages sites |
| `copyright: X` | `copyright = "X"` | HTML fragment allowed |
| `repo_name: X` | `repo_name = "X"` | |
| `repo_url: X` | `repo_url = "X"` | |
| `edit_uri: X` | `edit_uri = "X"` | only renders a pencil if `content.action.edit` is in `features` |
| `docs_dir: X` | `docs_dir = "X"` | |
| `site_dir: X` | `site_dir = "X"` | Zensical's default is `site`; keep the repo's existing value to avoid churn |
| `dev_addr: '127.0.0.1:7070'` | `dev_addr = "127.0.0.1:7070"` | preserved; also settable with `serve -a` |
| `use_directory_urls: true` | `use_directory_urls = true` | |
| `watch: [...]` | `watch = [...]` | |

## Keys that disappear

| mkdocs.yml | Disposition |
|---|---|
| `theme.name: material` | Replaced by `[project.theme] variant`. See [Theme](#theme). |
| `plugins: - search` | **Delete.** Search is built into Zensical (the Disco engine). Output still contains a search index and worker. |
| `validation:` (and `validation.links.*`) | **Delete.** Zensical validates links and anchors natively; `--strict` aborts on them. Strictly stronger than MkDocs' `warn`. Make sure both workflows use `--strict` afterwards. |

## Keys that are UNSUPPORTED — stop, do not migrate silently

| mkdocs.yml | Behavior under Zensical |
|---|---|
| `exclude_docs:` | **Silently ignored.** Both the MkDocs newline-string form and a TOML array were tested; the excluded pages are built and published anyway. There is no equivalent. A repo using this to withhold internal notes (design docs, plans) will start publishing them. Stop and make the user decide — the real fix is moving those files out of `docs_dir`. |
| `hooks:` | No equivalent. |
| `theme.custom_dir` | Templates need MiniJinja adjustments. Hand-review. |
| Any plugin other than `search` | Support is partial. Check against Zensical's plugin docs. |

## Theme

**If the repo is adopting the shared StrideLabs theme** (the default —
`theme.name = "stridelabs"`), most of this section does not apply: the
palette, font stack and feature toggles come from the theme package and
should be *dropped* rather than translated. Carrying them across defeats the
point of a shared theme, and a `font.*` setting in particular re-enables
Zensical's Google Fonts `<link>` on top of the theme's self-hosted faces.

Keep only `theme.icon.logo` — it identifies the project beside the shared owl.

The table below is for repos deliberately opting out of the shared theme.

| mkdocs.yml | zensical.toml |
|---|---|
| `theme.name: material` | `[project.theme]` `variant = "modern"` (or `"classic"` for the Material look) |
| `theme.features: [a, b]` | `features = ["a", "b"]` |
| `theme.font.text/code` | `[project.theme.font]` `text = / code =` |
| `theme.icon.logo: material/console` | `[project.theme.icon]` `logo = "material/console"` |
| `theme.logo: assets/logo.png` | `logo = "assets/logo.png"` under `[project.theme]` (takes precedence over `icon.logo`) |
| `theme.favicon: X` | `favicon = "X"` under `[project.theme]` |
| `theme.language: en` | `language = "en"` |

Icon sets shipped: `fontawesome`, `lucide`, `material`, `octicons`, `simple`.
So `material/*` and `fontawesome/brands/*` references keep working.

### Palette

A YAML list of palette entries becomes an **array of tables**:

```yaml
theme:
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
```

```toml
[[project.theme.palette]]
media = "(prefers-color-scheme: light)"
scheme = "default"
primary = "indigo"
accent = "indigo"
toggle.icon = "lucide/sun"
toggle.name = "Switch to dark mode"
```

Note the double brackets. Toggle icons are conventionally switched to
`lucide/sun` and `lucide/moon` to match the `modern` variant's icon language —
`material/brightness-7|4` still work if you prefer them.

### Feature notes

- `header.autohide` fights the `modern` variant's header treatment. Consider
  dropping it; it is a preference, not a capability.
- `navigation.top` (back-to-top) is on by default in Zensical's own template
  and is worth adding for long reference pages.
- Everything else in common use maps 1:1: `navigation.sections`,
  `navigation.expand`, `navigation.footer`, `navigation.indexes`,
  `navigation.tabs`, `navigation.instant`, `content.code.copy`,
  `content.code.annotate`, `content.tabs.link`, `search.highlight`,
  `search.share`, `toc.follow`, `toc.integrate`.

## Navigation

YAML nesting becomes an array of single-key inline tables:

```yaml
nav:
  - Home: index.md
  - Guides:
      - Local DNS: guides/local-dns.md
```

```toml
nav = [
  { "Home" = "index.md" },
  { "Guides" = [
    { "Local DNS" = "guides/local-dns.md" },
  ] },
]
```

Omit `nav` entirely to derive navigation from the `docs_dir` structure.

## Extra

| mkdocs.yml | zensical.toml |
|---|---|
| `extra: {key: value}` | `[project.extra]` `key = "value"` |
| `extra.social: [{icon, link}]` | `[[project.extra.social]]` `icon = / link =` (array of tables) |
| `extra_css: [a.css]` | `extra_css = ["a.css"]` under `[project]` |
| `extra_javascript: [js/x.js]` | `extra_javascript = ["js/x.js"]` under `[project]` |

## Markdown extensions

Each extension becomes its own table. Extensions with no options are an empty
table header.

```yaml
markdown_extensions:
  - admonition
  - toc:
      permalink: true
```

```toml
[project.markdown_extensions.admonition]
[project.markdown_extensions.toc]
permalink = true
```

Dotted names nest: `pymdownx.details` →
`[project.markdown_extensions.pymdownx.details]`.

### `!!python/name:` tags become plain strings

This is the trap that breaks naive parsers **and** naive translations.

| mkdocs.yml | zensical.toml |
|---|---|
| `format: !!python/name:pymdownx.superfences.fence_code_format` | `format = "pymdownx.superfences.fence_code_format"` |
| `emoji_index: !!python/name:material.extensions.emoji.twemoji` | `emoji_index = "zensical.extensions.emoji.twemoji"` |
| `emoji_generator: !!python/name:material.extensions.emoji.to_svg` | `emoji_generator = "zensical.extensions.emoji.to_svg"` |

**The emoji namespace changes.** Dropping only the `!!python/name:` prefix and
keeping `material.extensions.emoji.*` aborts the build:

```
ModuleNotFoundError: No module named 'material'
```

This is the only *loud* failure in the migration — and it hits any repo using
`pymdownx.emoji` (16 of 24 in the surveyed fleet).

Also note: PyYAML `safe_load` and `yq` **throw** on `!!python/name:` tags. Use
`yaml.BaseLoader` or an unknown-tag handler when parsing `mkdocs.yml`.

### superfences / mermaid

```toml
[project.markdown_extensions.pymdownx.superfences]
custom_fences = [
  { name = "mermaid", class = "mermaid", format = "pymdownx.superfences.fence_code_format" },
]
```

Mermaid needs nothing further — Zensical initializes the JS runtime itself
when it sees a mermaid fence, and the diagrams follow the configured fonts and
color schemes including dark mode.

### Common extensions, verified working

`admonition`, `attr_list`, `md_in_html`, `def_list`, `footnotes`, `abbr`,
`tables`, `toc`, and `pymdownx.{highlight, inlinehilite, snippets,
superfences, tabbed, details, emoji, tasklist, keys, mark, caret, tilde,
betterem, smartsymbols, magiclink, arithmatex}`.

## Output differences to expect

These are **not** bugs; do not chase them.

| Difference | Explanation |
|---|---|
| Asset tree differs completely | MkDocs ships ~40 `lunr/*` files + `main.*.min.css`; Zensical ships the Disco worker + `stylesheets/{classic,modern}/*`. **Only compare the HTML page set across generators.** |
| `search/search_index.json` → `search.json` | Different search engine |
| `<title>` text changes | MkDocs uses the **nav title**; Zensical uses the page **`<h1>`**. `CLI - proj` becomes `CLI Reference - proj`. A page whose `<h1>` equals the site name renders `name - name`. |

Verified **unchanged** on a real 13-page migration: the HTML page set, every
heading anchor `id` (so deep links survive), and the `description`, `author`
and `canonical` `<head>` metadata.
