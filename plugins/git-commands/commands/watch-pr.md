---
description: Watch PR CI checks and bot reviews, fixing failures along the way
argument-hint: "[pr-number]"
---

# Watch PR Command

Watch a pull request's CI checks and bot reviews, fixing failures along the way.

Use `$ARGUMENTS` as an optional PR number. If not provided, use the PR associated with the current branch.

## Steps

1. **Identify the PR**: Determine which PR to watch
   - If `$ARGUMENTS` is provided, use it as the PR number: `gh pr view $ARGUMENTS --json number,headRefName,baseRefName,url`
   - Otherwise, detect from current branch: `gh pr view --json number,headRefName,baseRefName,url`
   - If no PR is found, stop and inform the user

2. **Wait for CI checks**: Watch until all checks complete
   - Run `gh pr checks <number> --watch --fail-fast`
   - If `--watch` is not supported, fall back to polling `gh pr checks <number>` every 30 seconds
   - Ignore bot review checks (e.g. CodeRabbit) when evaluating pass/fail — these are informational
   - `--fail-fast` exits on the *first* failing check, bot checks included, so it can end the watch while required CI is still running. When it returns, look at what actually failed: if it was only a bot review check, resume with `gh pr checks <number> --watch` (no `--fail-fast`) and keep waiting. In a repo that defines required checks, `gh pr checks <number> --watch --fail-fast --required` avoids the problem outright — but `--required` shows nothing at all in a repo without branch protection, so don't reach for it blindly

3. **Evaluate CI results**: Categorize the outcomes
   - If all required checks passed, move to step 5 (bot review)
   - If any required checks failed, proceed to step 4

4. **Handle CI failures**: Diagnose and fix
   - Identify the failed check from `gh pr checks <number>` — the output includes a link column with the run URL containing the run ID
   - Fetch failure logs using that run ID: `gh run view <run-id> --log-failed`
   - Examine the repo's CI config to understand what the check does
   - Determine the fix from the logs and CI config — do not hardcode any CI job names or language-specific commands
   - Run equivalent local checks to verify the fix before pushing
   - Commit the fix, push, and go back to step 2 to re-watch
   - To retry an infra flake rather than fix code: `gh run rerun <run-id> --failed` is **refused while the run is still in progress** — wait for the run to settle first
   - **Circuit breaker**: count infrastructure reruns, not just code fixes. After one rerun of the same job, a second failure — whether it followed a code-fix push or a plain flake rerun — stops the loop: ask the user for guidance instead of retrying again. If the *same* check fails with a *different* test each time, that is runner load rather than anything wrong with the branch; say so, and still stop after two reruns

5. **Wait for bot review**: Check for bot review tools
   - Look at the PR checks for any bot review tool (e.g. CodeRabbit, Greptile) — **more than one may review**, so check each for an actual body; a "pass" check with no review body is not a review
   - If no bot review tool is detected, skip to step 7
   - Poll for review comments using `gh pr view <number> --json reviews,comments`.
     CodeRabbit typically completes within a few minutes; if no review
     has appeared after ~10 minutes, move on to step 7.
   - **Note:** parallel reviewers spawned via the `Agent` tool (e.g.
     `subagent_type: "codex-cli:codex-rescue"` or
     `subagent_type: "coderabbit:code-reviewer"`) are *complementary*
     to the automatic CodeRabbit check on the PR — different reviewer,
     different perspective. Review-purpose rescue agents must be prompted
     to run read-only (their default is write-capable). If you launched
     one in parallel with `/watch-pr`, synthesize both sets of findings
     before responding.

6. **Handle review comments**: Evaluate and address feedback
   - List the inline review comments first: `gh api --paginate repos/{owner}/{repo}/pulls/<pr>/comments`. `gh pr view --json reviews,comments` returns review summaries and issue comments but no inline bodies or ids, so relying on it alone silently skips every line comment. Read one comment in full with `gh api repos/{owner}/{repo}/pulls/comments/<id>`
   - Evaluate each comment: fix comments that point out real improvements (bugs, correctness, meaningful quality issues)
   - Verify a suggested fix against the change's own pinned decisions before applying it — a reviewer will happily "fix" a deliberate choice back to the default
   - Reply on the thread with `gh api --method POST repos/{owner}/{repo}/pulls/<pr>/comments/<id>/replies -f body=…` so the disposition lands where the finding is. `<id>` must be the thread's **root** comment: if the comment you are answering has an `in_reply_to_id`, post to that id instead of its own — GitHub rejects a reply to a reply
   - Skip nitpicks, style-only suggestions, and comments that don't improve the code
   - Editing the PR body (`gh pr edit --body-file`) overwrites CodeRabbit's appended summary — harmless, it re-adds it on the next review, but don't mistake it for the bot retracting anything
   - If changes were made, commit, push, and go back to step 2 to re-watch
   - If no changes were needed, move to step 7

7. **Report results**: Summarize the outcome
   - State whether all CI checks passed
   - Summarize any fixes that were made
   - Summarize any review comments that were addressed or skipped
   - If everything is green, suggest the user can now run `/merge-pr` to merge
