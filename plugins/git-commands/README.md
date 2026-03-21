# git-commands

Git workflow commands for Claude Code.

## Commands

### `/watch-pr [pr-number]`

Watch a PR's CI checks and bot reviews, fixing failures along the way. Automatically diagnoses CI failures, runs equivalent local checks, and pushes fixes. Waits for bot reviews (e.g., CodeRabbit) and addresses real improvements.

### `/merge-pr [pr-number]`

Merge a PR after verifying CI checks have passed. Lists commits, recommends squash vs merge commit based on commit quality, and handles branch cleanup.

Both commands auto-detect the PR from the current branch if no number is provided.
