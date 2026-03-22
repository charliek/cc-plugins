# Release Plugin Setup

The `/release:release` command requires two things in your repository:

## 1. GoReleaser Configuration

Create a `.goreleaser.yaml` in your repo root. This controls how binaries are built and published to GitHub Releases.

See [charliek/prox/.goreleaser.yaml](https://github.com/charliek/prox/blob/main/.goreleaser.yaml) for a working example that builds multi-platform Go binaries with checksums and automatic pre-release detection.

Key sections:
- **builds** — define binary targets, platforms (linux/darwin, amd64/arm64), and ldflags for version injection
- **archives** — tar.gz packaging with platform-specific naming
- **release** — GitHub release settings, `prerelease: auto` to detect pre-release tags
- **changelog** — use GitHub API, filter out docs/test/chore/ci commits

## 2. GitHub Actions Workflow

Create `.github/workflows/release.yaml` triggered on `v*` tag pushes.

See [charliek/prox/.github/workflows/release.yaml](https://github.com/charliek/prox/blob/main/.github/workflows/release.yaml) for a working example.

The workflow should:
1. Checkout with `fetch-depth: 0` (GoReleaser needs full history)
2. Set up Go from `go.mod`
3. Run tests
4. Run linter
5. Run GoReleaser with `release --clean`

Required permissions: `contents: write` (for creating the GitHub Release).

## 3. CHANGELOG.md

Optional — the command will create it if it doesn't exist. If you already have one, the new entry will be prepended after the first header line.
