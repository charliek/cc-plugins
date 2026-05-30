# Workflow job templates

This directory holds GitHub Actions templates for the per-repo
`.github/workflows/release.yml`. The setup skill picks the right pieces
based on which artifact pipelines the repo opted into, drops them into
`release.yml`, and the repo owns its workflow from there.

The templates are **not** reusable workflows (no
`uses: charliek/cc-plugins/.github/workflows/*`). They're meant to be
copied into each consuming repo verbatim or near-verbatim. This keeps
each repo's release definition self-contained and visible — no
cross-repo refs to chase when debugging.

## Files

| File | Purpose |
|---|---|
| [`release.yml.example`](release.yml.example) | A complete `release.yml` showing how the jobs compose for a representative repo (mac DMG + Sparkle appcast + linux .deb + apt dispatch). Use as a skeleton; cherry-pick the jobs you need. |
| [`sanity-check-app.yml.template`](sanity-check-app.yml.template) | Standalone `workflow_dispatch`-only workflow that mints a release-bot token and verifies the App is wired. Drop in as-is; runs nothing automatically. |
| [`job-version-check.yml`](job-version-check.yml) | Asserts the tag matches the repo's version manifest. Generic; takes manifest path + extraction regex inline. |
| [`job-ci-gate.yml`](job-ci-gate.yml) | Polls `ci-success` on the tagged commit and refuses to publish unless it's green. Universal; copy as-is. |
| [`job-create-release.yml`](job-create-release.yml) | Extracts this tag's CHANGELOG section and `gh release create`s. Universal. |
| [`job-sparkle-appcast.yml`](job-sparkle-appcast.yml) | EdDSA-signs a built DMG, appends to the appcast XML, bot-pushes to main. Mac/Sparkle-specific. |
| [`job-apt-dispatch.yml`](job-apt-dispatch.yml) | Fires a `repository_dispatch` at an apt-repo receiver after the .debs are uploaded. Generic dispatch pattern; receiver repo is a config knob. Uses a release-bot App token (PAT alternative documented inline). |
| [`job-homebrew-tap.yml`](job-homebrew-tap.yml) | Renders an in-repo formula template with the released tarball sha256s and pushes `Formula/<name>.rb` to a tap repo. The GoReleaser-free `brews:` equivalent for hand-built binaries. Uses a release-bot App token. |

## Composition

Every release workflow has the same skeleton:

```text
on push tag v*:
  version-check        ← generic
  ci-gate              ← generic
  create-release       ← generic
  <build jobs>         ← repo-specific (mac DMG, linux .deb, Docker image, …)
  <publish jobs>       ← mixed; some generic (apt-dispatch, sparkle-appcast),
                                some repo-specific
```

The generic jobs are byte-for-byte the same across repos. The build
jobs are repo-specific and stay inline. The publish jobs split: a few
follow common patterns (covered by templates here), the rest are
repo-specific.

### Paste-ready indentation

Each `job-*.yml` fragment file's YAML body is already indented by 2
spaces so it sits cleanly under `jobs:` in `release.yml`. **Don't
re-indent when pasting.** The `# === Paste-ready fragment ===` comment
at the top of each file repeats this.

After pasting all the jobs you need under your `jobs:` block, the
result should look like the [`release.yml.example`](release.yml.example)
skeleton (each job id at column 2, job content at column 4 or more).

## Substitution

Templates use prose placeholders that the setup skill replaces during
emission. The placeholders read naturally — they're not macro syntax
the build interprets. Examples:

- `<MANIFEST_PATH>` → `Cargo.toml`
- `<VERSION_PATTERN>` → `'^version[[:space:]]*=[[:space:]]*"([^"]+)"'`
- `<APPCAST_PATH>` → `docs/appcast.xml`
- `<DMG_PATTERN>` → `Roost-*.dmg`
- `<UPDATE_APPCAST_SCRIPT>` → `mac/scripts/update-appcast.py`
- `<APT_RECEIVER_REPO>` → `charliek/apt-charliek`
- `<APT_EVENT_TYPE>` → `publish`
- `<APT_PACKAGE>` → `roost`
- `<TAP_REPO>` → `charliek/homebrew-tap`
- `<FORMULA_NAME>` → `strix`
- `<FORMULA_TEMPLATE>` → `scripts/release/strix.rb.tmpl`

When you emit a job into a repo, replace every angle-bracket placeholder
with the repo's specific value. Don't leave placeholders in the
committed file — they don't expand at runtime.

## What the templates assume

- The repo has `RELEASE_BOT_APP_ID` + `RELEASE_BOT_APP_KEY` secrets (see
  [`../github-app.md`](../github-app.md)).
- `main` is protected by a ruleset that bypasses both the App and the
  admin role.
- The repo has a `CHANGELOG.md` at the root following the Keep-a-Changelog
  shape (a `## vX.Y.Z` heading per release, optionally with a date).
- For Sparkle: the repo has an `update-appcast.py` (or equivalent) that
  takes `ROOST_VERSION` / `ROOST_TAG` / `ROOST_SIGN_FILE` env vars and
  mutates the appcast in place. The script is repo-specific; the
  workflow is not. (One day this could be promoted to a bundled script
  if every Sparkle consumer ends up with the same one.)

## What the templates don't ship

- Templates for ecosystems no consumer has migrated yet: PyPI publish,
  crates.io publish, npm publish, Docker push.
  Add when the first consumer needs them. (Homebrew tap update shipped with
  strix — see [`job-homebrew-tap.yml`](job-homebrew-tap.yml).)
- A reusable-workflows variant. We deliberately chose per-repo
  composition over `uses: <central>/.github/workflows/*` to keep each
  repo's release definition self-contained. If you want centralized
  reusables later, that's a separate plugin.
