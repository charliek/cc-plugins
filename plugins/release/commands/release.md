---
description: Create a semver software release with changelog and tag
argument-hint: "[version]"
---

# Release Command

Create a new software release by generating a changelog entry, committing it, and pushing a semantic version tag.
This triggers the release workflow which builds binaries via GoReleaser and creates a GitHub Release.

Use `$ARGUMENTS` as an optional version. If provided and valid, skip the version prompt.

**Execution discipline for release steps.** Release operations move
refs and create tags — don't chain them through `&&` with piped output
(e.g. `git commit -m ... | tail -3 && git tag ...`). Piping masks the
exit status of the left side, so a failed commit can still advance to
the tag step and produce a tag pointing at the wrong SHA. Run each
destructive step on its own, verify the expected state with the
post-step check listed below, then move on.

## Steps

1. **Check branch**: Ensure we're on the main branch
   - Run `git branch --show-current`
   - If not on main, stop and inform the user

2. **Check working tree**: Ensure there are no uncommitted changes
   - Run `git status --porcelain`
   - If there are changes, warn the user and ask how to proceed

3. **Verify CI status**: Check that CI has passed for the current commit
   - Run `gh run list --commit $(git rev-parse HEAD) --status completed --json conclusion,name`
   - All workflows should have conclusion "success"
   - If CI hasn't completed or failed, stop and inform the user

4. **Determine version tag**: Get semantic version from user or arguments
   - If `$ARGUMENTS` is provided and matches `v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?`, use it as the version
   - Otherwise, prompt: "What version should this release be? (e.g., v1.0.0, v1.1.0, v2.0.0)"
   - Validate format matches `v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?`
   - Check tag doesn't already exist: `git tag -l "<version>"`
   - If tag exists, inform user and ask for different version

5. **Generate changelog entry**: Summarize changes since last release
   - Find the previous release tag: `git describe --tags --abbrev=0 --match "v*" 2>/dev/null`
   - Get commits since that tag: `git log <previous-tag>..HEAD --oneline`
   - If no previous tag exists, get all commits: `git log --oneline`
   - Write a concise summary of the changes (group by type: features, fixes, updates)

6. **Update CHANGELOG.md**: Prepend the new entry
   - Read the current CHANGELOG.md (create if it doesn't exist)
   - Add a new section at the top (after the header) with the version and changes
   - Format:
     ```
     ## vX.Y.Z

     - Change 1
     - Change 2
     ```

7. **Commit the changelog**: Create a release commit
   - Stage CHANGELOG.md: `git add CHANGELOG.md`
   - Commit with inline `-m` flags — do **not** use `git commit -F <file>`.
     A stale temp file left over from a previous session can silently
     produce a wrong commit message; inline avoids the whole class of
     bug:
     ```bash
     git commit -m "Release vX.Y.Z" -m "<your Co-Authored-By line>"
     ```
   - Run this as its own command. Don't chain it with `&&` through
     `| tail -N` — the pipe masks the commit's exit status.
   - **Verify the commit landed before tagging:**
     ```bash
     git log -1 --pretty=%s
     ```
     This must print `Release vX.Y.Z`. If it doesn't, stop and
     reconcile (likely cause: nothing was staged, or a previous step
     failed silently). Don't tag the wrong commit.

8. **Create and push tag**: Trigger the release workflow
   - Create annotated tag: `git tag -a vX.Y.Z -m "vX.Y.Z"`
   - **Verify the tag points at the Release commit you just made:**
     ```bash
     [ "$(git rev-list -n1 vX.Y.Z)" = "$(git rev-parse HEAD)" ] \
       && echo "tag SHA OK" || echo "tag does NOT point at HEAD — STOP"
     ```
     If the tag doesn't point at HEAD, fix locally before pushing.
   - Push commit and tag together: `git push --follow-tags`

9. **Confirm success**: Show the release URL
   - Get the repo URL: `gh repo view --json url --jq '.url'`
   - Display: `<repo-url>/releases/tag/vX.Y.Z`
   - Inform user that the release workflow has been triggered
   - They can monitor it at the Actions tab

## Error Handling

- If CI hasn't passed, inform the user and suggest running `/release:release` again after CI completes
- If not on main branch, inform the user to switch branches
- If there are uncommitted changes, warn the user and ask how to proceed
- If the version tag already exists, ask for a different version
- If push fails, provide troubleshooting steps

## Prerequisites

See `references/setup.md` for required GitHub Actions workflow and GoReleaser configuration.
