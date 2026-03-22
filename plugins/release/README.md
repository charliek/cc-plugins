# release

Software release commands for Claude Code.

## Commands

### `/release:release [version]`

Create a semantic version release for software projects. Verifies CI status, prompts for a version (e.g., v1.2.0), generates a changelog entry from commits since the last tag, updates CHANGELOG.md, commits, tags, and pushes to trigger GoReleaser.

## Setup

See [references/setup.md](references/setup.md) for prerequisites (GoReleaser config and GitHub Actions workflow).
