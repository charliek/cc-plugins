---
description: Ask both Codex and Kimi K2.5 to review a plan in parallel, synthesize and incorporate feedback
argument-hint: "[plan-file-path]"
---

# Ask Panel Command

Run Codex and Kimi K2.5 plan reviews in parallel, synthesize their feedback, and incorporate improvements. Two different AI models reviewing the same plan provides broader coverage and higher confidence in findings they agree on.

Use `$ARGUMENTS` as an optional path to the plan file. If not provided, check for an active plan file from conversation context.

## Steps

1. **Check prerequisites**: Verify available tools
   - Run `codex --version 2>&1` — note if Codex is available
   - Run `opencode --version 2>&1` — note if opencode (for Kimi) is available
   - If **neither** tool is available, tell the user and stop
   - If **one** tool is missing, warn the user and proceed with the available tool only

2. **Locate the plan file**:
   - If `$ARGUMENTS` contains a file path, expand `~` and resolve, verify with `test -f`
   - If no argument, check for an active plan file from conversation context
   - If no plan file is found, ask the user to provide the path and stop (a plan is required for panel review)

3. **Refine the plan before submission**: Read the plan and update it to meet review-readiness criteria before sending it to external reviewers. This ensures the external tools evaluate a well-structured plan, not a rough draft.
   - **Standalone**: Remove any dependencies on conversation context. The plan must be fully understandable on its own.
   - **Acceptance criteria**: Ensure the plan has clear acceptance criteria that serve as explicit exit criteria. A reader should know exactly when the plan is "done."
   - **Testing and linting**: Test updates, test coverage, and linting must be listed as exit criteria of the plan.
   - **Repo patterns**: Ensure the plan matches the repo's architectural patterns and conventions.
   - Edit the plan file with any needed refinements before proceeding.

4. **Run reviews in parallel**:

   Create a temp directory:
   ```bash
   tmpdir=$(mktemp -d)
   ```

   **Launch Codex** (in background, if available):
   ```bash
   (echo "Review the following implementation plan. Evaluate standalone readability, acceptance criteria, test coverage, and repo pattern alignment. Provide specific, actionable feedback organized by category."; echo ""; echo "---BEGIN PLAN---"; cat "<plan-file-path>"; echo "---END PLAN---") | codex exec - > "$tmpdir/codex.txt" 2>"$tmpdir/codex-stderr.txt" &
   codex_pid=$!
   ```

   **Launch Kimi** (in background, if available):
   ```bash
   cat "<plan-file-path>" | opencode run \
     -m "fireworks-ai/accounts/fireworks/models/kimi-k2p5" \
     -- "Review the following implementation plan. Evaluate: 1) Is the plan standalone? 2) Are acceptance criteria clear? 3) Does it include test coverage? 4) Does it match repo conventions? Provide specific, actionable feedback." \
     > "$tmpdir/kimi.txt" 2>"$tmpdir/kimi-stderr.txt" &
   kimi_pid=$!
   ```

   If a tool was skipped (unavailable), set its PID to `""`.

   **Wait for launched tools only**:
   ```bash
   [ -n "$codex_pid" ] && { wait $codex_pid; codex_status=$?; } || codex_status=""
   [ -n "$kimi_pid" ] && { wait $kimi_pid; kimi_status=$?; } || kimi_status=""
   ```

   Warn the user this may take a couple minutes.

5. **Collect results**: Read the output files
   - If `codex_status` is non-zero, read `$tmpdir/codex-stderr.txt` for error details
   - Read `$tmpdir/codex.txt` for Codex findings
   - If `kimi_status` is non-zero, read `$tmpdir/kimi-stderr.txt` for error details
   - Read `$tmpdir/kimi.txt` for Kimi findings
   - If one tool failed, proceed with the other tool's findings

6. **Synthesize feedback**: Cross-reference findings from both models
   - **Consensus findings**: Both models flag the same concern — highest priority, address first
   - **Unique findings**: Only one model flagged the concern — evaluate individually (fix real improvements, skip nitpicks)
   - **Contradictions**: Models disagree on the same topic — flag for user review, do not act autonomously

7. **Incorporate feedback**: Apply improvements to the plan file
   - Address consensus findings first
   - Address unique findings that meet the "real improvement" bar
   - Skip nitpicks and style-only suggestions

8. **Re-review**: If edits were made, automatically run one more pass
   - **Circuit breaker**: Maximum 2 total passes. After the second, stop and report regardless.
   - Only re-run the model(s) that found issues in areas that were changed

9. **Report results**: Summarize the full outcome (including refinements from step 3)
   - **Per-model summary**: How many findings each model returned
   - **Consensus findings**: Issues both models agreed on
   - **Unique findings addressed**: Model-specific issues that were fixed
   - **Findings skipped**: What was not addressed and why
   - **Contradictions**: Any disagreements flagged for user review
   - **Tool failures**: If one tool failed or was skipped, explain why
   - Clean up: `rm -rf "$tmpdir"`
