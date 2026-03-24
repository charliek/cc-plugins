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

3. **Refine the plan before submission**: Read the plan and verify it meets these review-readiness criteria. Edit the plan file to fix any gaps before proceeding.

   Checklist — the plan must have:
   - [ ] **Context section**: Why this change is being made (problem, motivation, intended outcome)
   - [ ] **File list**: Paths of all files to be created or modified
   - [ ] **Acceptance criteria**: Explicit exit criteria — a reader knows exactly when the plan is "done"
   - [ ] **Test plan**: What tests to add/update, what commands to run for verification
   - [ ] **No conversation dependencies**: Fully understandable without prior chat context
   - [ ] **Repo conventions**: Matches the repo's existing patterns (naming, structure, tooling)

4. **Submit the plan to Codex for review**: Pass the plan content inline in the Codex prompt. The plan is shell-expanded into the argument string — do not pipe via stdin.

   Run the following as a **single Bash command** (the temp directory variable must remain in scope):

   ```bash
   tmpdir=$(mktemp -d) && \
   echo "TMPDIR=$tmpdir" && \
   codex exec --full-auto -o "$tmpdir/codex.txt" \
     "Review the following implementation plan. Evaluate: 1) Is the plan standalone and understandable without conversation context? 2) Are acceptance criteria clear and actionable? 3) Does it include test coverage requirements? 4) Does it match the repo's architectural patterns and conventions? <additional-user-prompt-if-any>. Provide specific, actionable feedback organized by category.

   ---BEGIN PLAN---
   $(cat "<plan-file-path>")
   ---END PLAN---" \
     2>"$tmpdir/stderr.txt"
   ```

   **Important:** `--full-auto` lets Codex explore the repo for context. `-o` captures the final response to a file.

   **Note the temp directory path** from the `TMPDIR=...` output line — use it when reading output files and during cleanup.

   Check the exit code. If non-zero, read `$tmpdir/stderr.txt` for error details and stop. Otherwise read `$tmpdir/codex.txt` for the review.

5. **Evaluate findings**: Analyze each piece of feedback from Codex
   - **Fix**: missing acceptance criteria, unclear exit conditions, incomplete test coverage, architectural misalignment, standalone readability issues, missing edge cases
   - **Skip**: style-only suggestions, subjective preferences, feedback that doesn't improve the plan

6. **Incorporate feedback**: Edit the plan file with worthwhile improvements

7. **Report results**: Summarize what was refined (step 3), what Codex found, what was incorporated, and what was skipped
   - Clean up: `rm -rf "$tmpdir"` (use the actual temp directory path from step 4)
