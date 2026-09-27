---
description: Ask GLM 5.3 to review and challenge an implementation plan
argument-hint: "[plan-file-path]"
---

# Ask GLM Command

Submit an implementation plan to GLM 5.3 (via opencode + Z.ai) for review. GLM reads the plan, explores the repository to understand conventions, and provides feedback on completeness, acceptance criteria, test coverage, and architectural alignment.

Use `$ARGUMENTS` as an optional path to the plan file. If not provided, use the active plan file from the current conversation context (typically in `~/.claude/plans/`).

## Steps

1. **Check prerequisites**: Verify opencode CLI is available
   - Run `opencode --version 2>&1`
   - If the command fails, tell the user to install opencode and stop

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

4. **Submit the plan to GLM for review**: pipe a brief and the plan to opencode. Use plain commands — no variables, `$(…)`, or heredocs, which a session pinned to a worktree refuses.

   1. **Write the review brief** with the file-writing tool, next to the plan (`<plan dir>/glm-brief.md`, outside the repo):

      > Review the implementation plan that follows this brief. You may read repository files for context; do not edit anything. Evaluate: 1) Is the plan standalone and understandable without conversation context? 2) Are acceptance criteria clear and actionable? 3) Does it include test coverage requirements? 4) Does it match the repo's architectural patterns and conventions? 5) Risks, gaps, or missing edge cases? Provide specific, actionable feedback organized by category, citing file:line where the repo contradicts the plan.

   2. **Run it in the background** (`run_in_background: true`) — a whole-plan review can outlast one 10-minute foreground call. Use resolved absolute paths in single quotes (`~` does not expand inside quotes; write an embedded `'` as `'\''`).

      ```bash
      cat -- '<brief path>' '<plan path>' | opencode run -m zai-coding-plan/glm-5.3 -- 'Follow the review brief on stdin; the full plan follows it. Use ONLY your read, grep and glob tools, and ONLY on files inside the current repository directory. Do not run shell commands.'
      ```

   **Why the tool rules:** in non-interactive mode, opencode kills the run as soon as GLM tries a shell command or reads outside the repo. **Always use `--`** before the message so it is not taken as file paths, and pipe the plan on stdin rather than `-f` (opencode may reject external directory permissions).

   Stop it with the task-stop tool if it is still running at 20 minutes. A stopped run, a non-zero exit, or empty output is a failed review — report it, never as "no findings".

5. **Evaluate findings**: Analyze each piece of feedback from GLM
   - **Fix**: missing acceptance criteria, unclear exit conditions, incomplete test coverage, architectural misalignment, standalone readability issues, missing edge cases
   - **Skip**: style-only suggestions, subjective preferences, feedback that doesn't improve the plan

6. **Incorporate feedback**: Edit the plan file with worthwhile improvements

7. **Report results**: Summarize what was refined (step 3), what GLM found, what was incorporated, and what was skipped
   - Clean up: `rm -rf "$tmpdir"` (use the actual temp directory path from step 4)
