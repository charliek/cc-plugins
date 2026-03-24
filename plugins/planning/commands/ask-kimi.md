---
description: Ask Kimi K2.5 to review and challenge an implementation plan
argument-hint: "[plan-file-path]"
---

# Ask Kimi Command

Submit an implementation plan to Kimi K2.5 (via opencode + Fireworks AI) for review. Kimi reads the plan, explores the repository to understand conventions, and provides feedback on completeness, acceptance criteria, test coverage, and architectural alignment.

Use `$ARGUMENTS` as an optional path to the plan file. If not provided, use the active plan file from the current conversation context (typically in `~/.claude/plans/`).

## Steps

1. **Check prerequisites**: Verify opencode CLI is available
   - Run `opencode --version 2>&1`
   - If the command fails, tell the user to install opencode and stop

2. **Locate the plan file**:
   - If `$ARGUMENTS` contains a file path, expand `~` and resolve relative paths, then verify with `test -f`
   - If no argument, check for an active plan file from the current conversation context
   - If no plan file can be found, ask the user to provide the path and stop

3. **Refine the plan before submission**: Read the plan and update it to meet review-readiness criteria before sending it to Kimi. This ensures the external reviewer evaluates a well-structured plan, not a rough draft.
   - **Standalone**: Remove any dependencies on conversation context. The plan must be fully understandable on its own.
   - **Acceptance criteria**: Ensure the plan has clear acceptance criteria that serve as explicit exit criteria. A reader should know exactly when the plan is "done."
   - **Testing and linting**: Test updates, test coverage, and linting must be listed as exit criteria of the plan.
   - **Repo patterns**: Ensure the plan matches the repo's architectural patterns and conventions.
   - Edit the plan file with any needed refinements before proceeding.

4. **Submit the plan to Kimi for review**: Pipe the plan content to opencode with a review prompt.

   Run the following as a **single Bash command** (the temp directory variable must remain in scope):

   ```bash
   tmpdir=$(mktemp -d) && \
   cat "<plan-file-path>" | opencode run \
     -m "fireworks-ai/accounts/fireworks/models/kimi-k2p5" \
     -- "Review the following implementation plan. Evaluate: 1) Is the plan standalone and understandable without conversation context? 2) Are acceptance criteria clear and actionable? 3) Does it include test coverage requirements? 4) Does it match the repo's architectural patterns and conventions? Provide specific, actionable feedback organized by category." \
     > "$tmpdir/output.txt" 2>"$tmpdir/stderr.txt"
   ```

   **Important:** Always use `--` before the message to prevent it from being interpreted as file paths. Pipe the plan via stdin rather than using `-f` for files outside the repo (opencode may reject external directory permissions).

   Check the exit code. If non-zero, read `$tmpdir/stderr.txt` for error details and stop. Otherwise read `$tmpdir/output.txt` for the review.

   **Note:** Kimi via opencode will proactively explore the repository to understand existing patterns and conventions before providing feedback.

5. **Evaluate findings**: Analyze each piece of feedback from Kimi
   - **Fix**: missing acceptance criteria, unclear exit conditions, incomplete test coverage, architectural misalignment, standalone readability issues, missing edge cases
   - **Skip**: style-only suggestions, subjective preferences, feedback that doesn't improve the plan

6. **Incorporate feedback**: Edit the plan file with worthwhile improvements

7. **Re-review**: If edits were made, automatically submit the updated plan to Kimi one more time
   - **Circuit breaker**: Maximum 2 total review passes. After the second, stop and report regardless.

8. **Report results**: Summarize what was refined (step 3), what Kimi found, what was incorporated, and what was skipped
   - Clean up: `rm -rf "$tmpdir"` (use the actual temp directory path from step 4)
