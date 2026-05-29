#!/usr/bin/env bash
# Bump the release version of a Rust workspace.
#
# Use this template for repos whose canonical version is
# `[workspace.package].version` in the root `Cargo.toml` (every workspace
# member inherits via `version.workspace = true`). The script bumps that
# field and regenerates `Cargo.lock` so the per-member entries match.
#
# The sed pattern allows variable whitespace around the `=`, so it
# matches both vanilla `cargo new`/`cargo init` output (`version = "0.1.0"`)
# and hand-aligned column-style layouts (`version       = "0.1.0"`). It
# does NOT preserve the original column alignment — the replacement
# uses a single space, which is the cargo-default. If your repo uses a
# column-aligned style and you want to preserve it, change the
# replacement's whitespace to match. (cargo doesn't care either way.)
#
# Also works for single-crate packages (no `[workspace.package]`, just
# `[package].version`) without changes — the pattern matches both.
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

if [[ ! "$V" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?$ ]]; then
  echo "error: '$V' is not semver (X.Y.Z or X.Y.Z-suffix)" >&2
  exit 2
fi

# 1. Bump [workspace.package].version. Variable whitespace around `=`
#    so both vanilla cargo (`version = "0.1.0"`) and column-aligned
#    layouts match.
sed -i.bak -E 's/^version[[:space:]]*=[[:space:]]*"[^"]+"/version = "'"$V"'"/' Cargo.toml
rm -f Cargo.toml.bak

# 2. Verify Cargo.toml saw the bump. A silent sed no-match — e.g. the
#    repo uses [package].version under a different section header, or
#    a layout the regex doesn't cover — is the most common failure
#    mode here. Catch it before blaming the lockfile.
if ! grep -q "^version = \"$V\"" Cargo.toml; then
  echo "error: Cargo.toml's [workspace.package].version did not update to $V." >&2
  echo "       The sed pattern matches \`version (whitespace) = (whitespace) \"<value>\"\` at column 0." >&2
  echo "       If your manifest has a different shape, adjust the sed pattern in this script." >&2
  exit 1
fi

# 3. Regenerate Cargo.lock so workspace member entries match.
#    --workspace is the surface that actually moves.
#    --offline is safe: we're only changing internal version strings,
#    not touching the dep tree, so the cache is sufficient.
cargo update --workspace --offline >/dev/null

# 4. Verify the lockfile saw the bump. If Cargo.toml updated but
#    Cargo.lock didn't, a member crate likely overrides version manually.
if ! grep -q "^version = \"$V\"" Cargo.lock; then
  echo "error: Cargo.lock did not update to $V — some member may override the version" >&2
  exit 1
fi

echo "Bumped Cargo.toml + Cargo.lock to $V"
