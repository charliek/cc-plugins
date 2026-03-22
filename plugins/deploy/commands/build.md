---
description: Create a date-based release to trigger Docker image builds and site deployment
---

# Deploy Build Command

Create a new deployment release by generating a changelog entry, committing it, and pushing a date-based version tag.
This triggers the release workflow which builds and pushes Docker images.

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

4. **Determine version tag**: Generate a date-based version
   - Format: `vYYYY.MM.DD` (e.g., `v2026.03.22`)
   - Check existing tags for today: `git tag -l "v$(date +%Y.%m.%d)*"`
   - If no tags exist for today, use `vYYYY.MM.DD`
   - If tags exist, find the highest suffix and increment: `v2026.03.22` → `v2026.03.22.2`, `v2026.03.22.2` → `v2026.03.22.3`, etc.
   - Show the proposed tag to the user for confirmation

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
     ## vYYYY.MM.DD

     - Change 1
     - Change 2
     ```

7. **Commit the changelog**: Create a release commit
   - Stage CHANGELOG.md: `git add CHANGELOG.md`
   - Commit with message: `Release vYYYY.MM.DD`
   - Include Co-Authored-By line

8. **Create and push tag**: Trigger the release workflow
   - Create tag: `git tag vYYYY.MM.DD`
   - Push commit and tag: `git push --follow-tags`

9. **Confirm success**: Show the release URL
   - Get the repo URL: `gh repo view --json url --jq '.url'`
   - Display: `<repo-url>/releases/tag/vYYYY.MM.DD`
   - Inform user that the release workflow has been triggered
   - They can monitor it at the Actions tab

## Error Handling

- If CI hasn't passed, inform the user and suggest running `/deploy:build` again after CI completes
- If not on main branch, inform the user to switch branches
- If there are uncommitted changes, warn the user and ask how to proceed
- If push fails, provide troubleshooting steps

## Prerequisites

See `references/setup.md` for required GitHub Actions workflow configuration.
