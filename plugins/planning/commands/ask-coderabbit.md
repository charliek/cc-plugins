---
description: Ask CodeRabbit to review and challenge an implementation plan
argument-hint: "[plan-file-path]"
---

# Ask CodeRabbit Command

Submit an implementation plan to CodeRabbit for review using the `coderabbit:code-reviewer` agent. The agent reads the plan and relevant repo files to provide feedback on completeness, acceptance criteria, test coverage, and architectural alignment.

Use `$ARGUMENTS` as an optional path to the plan file. If not provided, use the active plan file from the current conversation context (typically in `~/.claude/plans/`).

**Important:** This command uses the `coderabbit:code-reviewer` agent (subagent), not the `coderabbit review` CLI. The CLI requires git diffs and cannot review plan documents. The agent can review any content by reading files directly.

## Steps

1. **Locate the plan file**:
   - If `$ARGUMENTS` contains a file path, expand `~` and resolve relative paths, then verify with `test -f`
   - If no argument, check for an active plan file from the current conversation context
   - If no plan file can be found, ask the user to provide the path and stop

2. **Read the plan**: Read the full plan file content so it can be included in the agent prompt.

3. **Refine the plan before submission**: Update the plan to meet review-readiness criteria before sending it to CodeRabbit. This ensures the external reviewer evaluates a well-structured plan, not a rough draft.
   - **Standalone**: Remove any dependencies on conversation context. The plan must be fully understandable on its own.
   - **Acceptance criteria**: Ensure the plan has clear acceptance criteria that serve as explicit exit criteria. A reader should know exactly when the plan is "done."
   - **Testing and linting**: Test updates, test coverage, and linting must be listed as exit criteria of the plan.
   - **Repo patterns**: Ensure the plan matches the repo's architectural patterns and conventions.
   - Edit the plan file with any needed refinements before proceeding.

4. **Submit the plan to CodeRabbit for review**: Launch a `coderabbit:code-reviewer` agent with the plan content and specific review questions.

   Use the Agent tool with `subagent_type: "coderabbit:code-reviewer"` and include in the prompt:
   - The full plan text (paste it inline in the prompt)
   - Specific review questions to guide the analysis:
     1. Is the plan standalone and understandable without conversation context?
     2. Are acceptance criteria clear, actionable, and sufficient as exit criteria?
     3. Does the plan include adequate test coverage requirements?
     4. Does the plan match the repo's architectural patterns and conventions?
     5. Are there any risks, gaps, or missing edge cases?
   - Ask the agent to read relevant repo files (e.g., existing code, configs, patterns) to ground its review in actual project state

   The agent will return a single result message with its findings.

5. **Evaluate findings**: Analyze each piece of feedback from CodeRabbit
   - **Fix**: missing acceptance criteria, unclear exit conditions, incomplete test coverage, architectural misalignment, standalone readability issues, missing edge cases
   - **Skip**: style-only suggestions, subjective preferences, feedback that doesn't improve the plan

6. **Incorporate feedback**: Edit the plan file with worthwhile improvements

7. **Re-review**: If edits were made, automatically submit the updated plan to CodeRabbit one more time
   - **Circuit breaker**: Maximum 2 total review passes. After the second, stop and report regardless.

8. **Report results**: Summarize what was refined (step 3), what CodeRabbit found, what was incorporated, and what was skipped
