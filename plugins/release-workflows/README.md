# release-workflows

Convention-based release commands for Claude Code.

## Commands

### `/release-workflows:release [version]`

Cut a semver release for a repo that follows this plugin's release
convention. Verifies CI status, drafts a CHANGELOG entry, calls the
repo's `scripts/release/update-version.sh` to bump every source-tree
manifest, commits the changelog + the bump (two commits), tags, and
pushes. The release workflow (`release.yml`) handles the rest.

Requires the repo to have adopted the convention. If
`scripts/release/update-version.sh` doesn't exist, the skill stops and
points at `/release-workflows:setup`.

### `/release-workflows:setup`

Conversational bootstrap. Walks through the GitHub App install, repo
secrets, branch protection ruleset, `scripts/release/update-version.sh`,
`RELEASING.md`, and `.github/workflows/release.yml` composition. Never
auto-commits — drafts files for the user to review.

## The convention

See [`references/convention.md`](references/convention.md) for the
contract: what files a "convention-compliant" repo has, what secrets
it sets, what its branch protection looks like, and where the
local-vs-CI split is for version-derived file updates.

## Why a new plugin

Replaces the existing `release` plugin (which assumed GoReleaser and
was tuned to single-binary Go projects). The new convention covers
Rust workspaces, Claude Code plugins, Python projects, Java/Gradle,
and any repo whose release wants:

- A shared GitHub App for bot-driven post-build pushes (signed Sparkle
  appcasts, formula updates, etc.) instead of stranding the work as a
  manual post-release step
- A branch protection ruleset that bypasses the App and admin role for
  release pushes, so `ci-success` stays required for everyone else
- A mechanical `scripts/release/update-version.sh` so version-bumping
  never silently misses a lockfile (the bug that bit roost v0.0.5)

The legacy `release` plugin stays available during migration. Once
every consumer of the legacy plugin has adopted this convention,
retire it.

## Plugin layout

```
release-workflows/
├── .claude-plugin/plugin.json
├── README.md (this file)
├── commands/
│   ├── release.md                 # /release-workflows:release
│   └── setup.md                   # /release-workflows:setup
└── references/
    ├── convention.md              # the contract everything cites
    ├── github-app.md              # App install + secrets + ruleset walkthrough
    ├── releasing-md.template.md   # RELEASING.md skeleton with placeholders
    ├── update-version/
    │   ├── README.md              # template picker
    │   └── cargo-workspace.sh     # Rust workspace template
    └── workflows/
        ├── README.md              # composition guide
        ├── release.yml.example    # complete example
        ├── sanity-check-app.yml.template
        ├── job-version-check.yml
        ├── job-ci-gate.yml
        ├── job-create-release.yml
        ├── job-sparkle-appcast.yml
        └── job-apt-dispatch.yml
```

Templates for other languages (Python pyproject, Java/Gradle, plugin.json,
Go) and other pipelines (Docker push, Homebrew tap) are deferred until
the first consumer needs them — they're each tiny additions following
the same shape as the shipped ones.
