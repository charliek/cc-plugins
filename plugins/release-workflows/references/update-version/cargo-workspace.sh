#!/usr/bin/env bash
# Bump the release version of a Rust workspace.
#
# Use this template for repos whose canonical version is
# `[workspace.package].version` in the root `Cargo.toml` (every workspace
# member inherits via `version.workspace = true`). The script bumps that
# field and regenerates `Cargo.lock` so the per-member entries match.
#
# If your repo is a *single-crate* package (no `[workspace.package]`,
# just `[package].version`), the same script works after one line edit:
# replace the sed pattern's prefix `version       =` with `version =`.
# Add a comment explaining why you diverged.
#
# Not handled here:
#   - workspace member crates that override the inherited version
#     (rare; if you have one, list it explicitly with a second sed call)
#   - `Cargo.toml`s outside the workspace root (e.g. an `examples/`
#     directory with its own Cargo.toml — those are not release artifacts)
#
# Contract (see references/update-version/README.md):
#   - one arg: semver string, no `v` prefix
#   - idempotent
#   - no network (--offline)
#   - verifies its own work
#   - does not `git add` (the release skill stages + commits)

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <X.Y.Z>   e.g. $0 0.0.6" >&2
  exit 2
fi
V="$1"

if [[ ! "$V" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
  echo "error: '$V' is not semver (X.Y.Z or X.Y.Z-suffix)" >&2
  exit 2
fi

# 1. Bump [workspace.package].version. Preserve the fixed-width column
#    layout cargo generates so the file's other entries stay aligned.
sed -i.bak -E 's/^version       = "[^"]+"/version       = "'"$V"'"/' Cargo.toml
rm -f Cargo.toml.bak

# 2. Regenerate Cargo.lock so workspace member entries match.
#    --workspace is the surface that actually moves.
#    --offline is safe: we're only changing internal version strings,
#    not touching the dep tree, so the cache is sufficient.
cargo update --workspace --offline >/dev/null

# 3. Verify the lockfile saw the bump. If not, something is off (maybe
#    a member crate overrides version manually, or sed missed the line).
if ! grep -q "^version = \"$V\"" Cargo.lock; then
  echo "error: Cargo.lock did not update to $V — inspect by hand" >&2
  exit 1
fi

echo "Bumped Cargo.toml + Cargo.lock to $V"
