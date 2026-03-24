---
description: Ask Codex to review and challenge an implementation plan
argument-hint: "[plan-file-path]"
---

# Ask Codex Command

Submit an implementation plan to Codex CLI for review. Codex reads the plan and provides feedback on completeness, acceptance criteria, test coverage, and architectural alignment.

Use `$ARGUMENTS` as an optional path to the plan file. If not provided, use the active plan file from the current conversation context (typically in `~/.claude/plans/`).

## Steps

1. **Check prerequisites**: Verify Codex CLI is available
   - Run `codex --version 2>&1`
   - If the command fails, tell the user to install Codex CLI (`npm i -g @openai/codex`) and stop

2. **Locate the plan file**:
   - If `$ARGUMENTS` contains a file path, expand `~` and resolve relative paths, then verify with `test -f`
   - If no argument, check for an active plan file from the current conversation context
   - If no plan file can be found, ask the user to provide the path and stop

3. **Refine the plan before submission**: Read the plan and update it to meet review-readiness criteria before sending it to Codex. This ensures the external reviewer evaluates a well-structured plan, not a rough draft.
   - **Standalone**: Remove any dependencies on conversation context. The plan must be fully understandable on its own.
   - **Acceptance criteria**: Ensure the plan has clear acceptance criteria that serve as explicit exit criteria. A reader should know exactly when the plan is "done."
   - **Testing and linting**: Test updates, test coverage, and linting must be listed as exit criteria of the plan.
   - **Repo patterns**: Ensure the plan matches the repo's architectural patterns and conventions.
   - Edit the plan file with any needed refinements before proceeding.

4. **Submit the plan to Codex for review**: Pipe the plan content to Codex with review instructions prepended so Codex treats it as something to evaluate, not execute.

   Run the following as a **single Bash command** (the temp directory variable must remain in scope):

   ```bash
   tmpdir=$(mktemp -d) && \
   (echo "Review the following implementation plan. Evaluate: 1) Is the plan standalone and understandable without conversation context? 2) Are acceptance criteria clear and actionable? 3) Does it include test coverage requirements? 4) Does it match the repo's architectural patterns and conventions? <additional-user-prompt-if-any>. Provide specific, actionable feedback organized by category."; echo ""; echo "---BEGIN PLAN---"; cat "<plan-file-path>"; echo "---END PLAN---") | codex exec - -o "$tmpdir/codex.txt" 2>"$tmpdir/stderr.txt"
   ```

   **Important:** Always prepend review instructions before the plan content. Without them, Codex may interpret the plan as instructions to execute rather than content to review.

   **Important:** The `-o` flag writes Codex's final response to the specified file. Do not rely on stdout — `codex exec` produces no stdout output for multi-step sessions.

   Check the exit code. If non-zero, read `$tmpdir/stderr.txt` for error details and stop. Otherwise read `$tmpdir/codex.txt` for the review.

5. **Evaluate findings**: Analyze each piece of feedback from Codex
   - **Fix**: missing acceptance criteria, unclear exit conditions, incomplete test coverage, architectural misalignment, standalone readability issues, missing edge cases
   - **Skip**: style-only suggestions, subjective preferences, feedback that doesn't improve the plan

6. **Incorporate feedback**: Edit the plan file with worthwhile improvements

7. **Re-review**: If edits were made, automatically submit the updated plan to Codex one more time
   - **Circuit breaker**: Maximum 2 total review passes. After the second, stop and report regardless.

8. **Report results**: Summarize what was refined (step 3), what Codex found, what was incorporated, and what was skipped
   - Clean up: `rm -rf "$tmpdir"` (use the actual temp directory path from step 4)
