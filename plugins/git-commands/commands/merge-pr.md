---
description: Merge a PR after verifying CI checks have passed
argument-hint: "[pr-number]"
---

# Merge PR Command

Merge a pull request after verifying CI checks have passed.

Use `$ARGUMENTS` as an optional PR number. If not provided, use the PR associated with the current branch.

## Steps

1. **Identify the PR**: Determine which PR to merge
   - If `$ARGUMENTS` is provided, use it as the PR number: `gh pr view $ARGUMENTS --json number,state,title,isDraft,headRefName,baseRefName,commits,url`
   - Otherwise, detect from current branch: `gh pr view --json number,state,title,isDraft,headRefName,baseRefName,commits,url`
   - If no PR is found, stop and inform the user
   - If the PR is a draft, stop and inform the user it must be marked ready first
   - If the PR is already merged or closed, stop and inform the user

2. **Verify CI checks have passed**: Ensure all checks are green
   - Run `gh pr checks <number>`
   - All checks must pass; ignore bot review checks (e.g. CodeRabbit) which are informational and not required
   - If any required checks have failed, stop and show which checks failed
   - If checks are still running, suggest the user run `/watch-pr` first and then come back to merge

3. **Determine merge strategy**: Choose between merge commit and squash
   - If there is only **one commit**, use a merge commit (`--merge`) since squash would be equivalent — skip to step 4
   - If there are **multiple commits**:
     a. Fetch the commit list: `gh pr view <number> --json commits --jq '.commits[] | .messageHeadline'`
     b. Display all commit messages to the user so they can see what's in the PR
     c. Analyze the commits and form a recommendation:
        - If most commits look like fix-up or debug work (matching patterns like "fix lint", "fix tests", "fix CI", "address review", "WIP", "debug", "cleanup", "nit", very short/generic messages, or commits that clearly iterate on earlier commits in the same PR), recommend **squash**
        - If the commits are meaningful, atomic changes with distinct purposes, recommend **merge commit**
     d. Use the `AskUserQuestion` tool to present the choice:
        - Put the recommended option first with "(Recommended)" in the label
        - Include a brief reason in each option's description (e.g., "Most commits are fix-ups" or "Commits represent distinct logical changes")
        - Header: "Merge strategy"
        - Question: "This PR has N commits. How would you like to merge?"

4. **Merge the PR**: Execute the merge
   - Run `gh pr merge <number> --merge --delete-branch` or `gh pr merge <number> --squash --delete-branch` based on the chosen strategy

5. **Clean up local branch**: Sync local state
   - Switch to the base branch: `git checkout <baseRefName>`
   - Pull latest: `git pull`
   - Delete the local head branch if it still exists: `git branch -d <headRefName>`

6. **Confirm success**: Report the result
   - Show the PR URL and title
   - State which merge strategy was used (merge commit or squash)

## Error Handling

- If no PR is found for the current branch, inform the user and suggest providing a PR number
- If CI checks are still running, suggest `/watch-pr` first
- If CI checks have failed, show which checks failed and suggest fixing them
- If the PR is a draft, tell the user to mark it ready for review first
- If merge conflicts exist, inform the user they need to resolve conflicts before merging
- If permission errors occur, inform the user they may not have merge access
