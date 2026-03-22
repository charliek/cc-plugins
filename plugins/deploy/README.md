# deploy

Deployment commands for Claude Code.

## Commands

### `/deploy:build`

Create a date-based release (`vYYYY.MM.DD`) for site/app deployments. Verifies CI status, auto-generates a version tag, generates a changelog entry from commits since the last tag, updates CHANGELOG.md, commits, tags, and pushes to trigger Docker image builds.

## Setup

See [references/setup.md](references/setup.md) for prerequisites (GitHub Actions workflow for Docker builds).
