---
description: Ask Codex, Kimi K2.5, and CodeRabbit to review a plan in parallel, synthesize and incorporate feedback
argument-hint: "[plan-file-path]"
---

# Ask Panel Command

Run Codex, Kimi K2.5, and CodeRabbit plan reviews in parallel, synthesize their feedback, and incorporate improvements. Three different AI reviewers provide broad coverage and high confidence in findings they agree on.

- **Codex** (OpenAI) — reviews via `codex exec` with piped plan content
- **Kimi K2.5** (Moonshot AI via Fireworks) — reviews via `opencode run`, proactively explores the repo
- **CodeRabbit** — reviews via `coderabbit:code-reviewer` agent, reads repo files directly

Use `$ARGUMENTS` as an optional path to the plan file. If not provided, use the active plan file from the current conversation context (typically in `~/.claude/plans/`).

## Steps

1. **Check prerequisites**: Verify available tools
   - Run `codex --version 2>&1` — note if Codex is available
   - Run `opencode --version 2>&1` — note if opencode (for Kimi) is available
   - CodeRabbit agent requires no CLI prerequisite (it's a built-in subagent type)
   - If **no** tools are available, tell the user and stop
   - If some tools are missing, warn the user and proceed with the available tools

2. **Locate the plan file**:
   - If `$ARGUMENTS` contains a file path, expand `~` and resolve, verify with `test -f`
   - If no argument, check for an active plan file from conversation context
   - If no plan file is found, ask the user to provide the path and stop (a plan is required for panel review)

3. **Read and refine the plan before submission**: Read the plan and update it to meet review-readiness criteria before sending it to external reviewers. This ensures the reviewers evaluate a well-structured plan, not a rough draft.
   - **Standalone**: Remove any dependencies on conversation context. The plan must be fully understandable on its own.
   - **Acceptance criteria**: Ensure the plan has clear acceptance criteria that serve as explicit exit criteria. A reader should know exactly when the plan is "done."
   - **Testing and linting**: Test updates, test coverage, and linting must be listed as exit criteria of the plan.
   - **Repo patterns**: Ensure the plan matches the repo's architectural patterns and conventions.
   - Edit the plan file with any needed refinements before proceeding.

4. **Run reviews in parallel**: Launch all available reviewers concurrently. Warn the user this may take a couple minutes.

   **Launch Codex and Kimi via Bash** — Run the following as a **single Bash command**. All variable assignments (`tmpdir`, PIDs, exit statuses) must stay in the same shell. If a CLI tool was unavailable (detected in step 1), omit its lines from the script:

   ```bash
   tmpdir=$(mktemp -d) && \
   echo "Temp directory: $tmpdir" && \
   (echo "Review the following implementation plan. Evaluate standalone readability, acceptance criteria, test coverage, and repo pattern alignment. Provide specific, actionable feedback organized by category."; echo ""; echo "---BEGIN PLAN---"; cat "<plan-file-path>"; echo "---END PLAN---") | codex exec - -o "$tmpdir/codex.txt" 2>"$tmpdir/codex-stderr.txt" & \
   codex_pid=$! ; \
   cat "<plan-file-path>" | opencode run \
     -m "fireworks-ai/accounts/fireworks/models/kimi-k2p5" \
     -- "Review the following implementation plan. Evaluate: 1) Is the plan standalone? 2) Are acceptance criteria clear? 3) Does it include test coverage? 4) Does it match repo conventions? Provide specific, actionable feedback." \
     > "$tmpdir/kimi.txt" 2>"$tmpdir/kimi-stderr.txt" & \
   kimi_pid=$! ; \
   echo "Launched Codex (PID $codex_pid) and Kimi (PID $kimi_pid)" && \
   wait $codex_pid 2>/dev/null; codex_status=$? ; \
   wait $kimi_pid 2>/dev/null; kimi_status=$? ; \
   echo "Codex exit: $codex_status, Kimi exit: $kimi_status" && \
   echo "TMPDIR=$tmpdir"
   ```

   **Important:** The `-o` flag on `codex exec` writes Codex's final response to the specified file. Do not use stdout redirection — `codex exec` produces no stdout output for multi-step sessions.

   **Launch CodeRabbit** (via Agent tool with `run_in_background: true`):
   Use the Agent tool with `subagent_type: "coderabbit:code-reviewer"` and include the full plan text in the prompt along with these review questions:
   1. Is the plan standalone and understandable without conversation context?
   2. Are acceptance criteria clear, actionable, and sufficient as exit criteria?
   3. Does the plan include adequate test coverage requirements?
   4. Does the plan match the repo's architectural patterns and conventions?
   5. Are there any risks, gaps, or missing edge cases?
   Ask the agent to read relevant repo files to ground its review.

   Wait for the CodeRabbit agent to complete as well.

   **Note the temp directory path** from the Bash output (`TMPDIR=...` line) for use in step 5.

5. **Collect results**: Use the temp directory path printed by the script in step 4.
   - Read `$tmpdir/codex.txt` for Codex findings (if `codex_status` was 0; otherwise read `$tmpdir/codex-stderr.txt`)
   - Read `$tmpdir/kimi.txt` for Kimi findings (if `kimi_status` was 0; otherwise read `$tmpdir/kimi-stderr.txt`)
   - Read the CodeRabbit agent's returned result
   - If any tool failed, proceed with the others' findings

6. **Synthesize feedback**: Compile a unified list of all findings from all reviewers. Every finding should be evaluated on its own merit regardless of which reviewer raised it.
   - **Prioritization**: Findings flagged by multiple reviewers are likely higher priority, but a finding from a single reviewer is still valid and should be evaluated
   - **Reviewer strength**: Codex tends to be the strongest reviewer. Give its unique findings strong consideration. Kimi and CodeRabbit may catch things Codex misses but weigh their findings accordingly.
   - **Contradictions**: When reviewers disagree on the same topic, flag for user review rather than acting autonomously
   - Do not discard findings just because only one reviewer raised them

7. **Incorporate feedback**: Apply improvements to the plan file
   - Evaluate every finding on its own merit — does it make the plan better?
   - Skip only genuine nitpicks and style-only suggestions

8. **Re-review**: If edits were made, automatically run one more pass
   - **Circuit breaker**: Maximum 2 total passes. After the second, stop and report regardless.
   - Only re-run the reviewer(s) that found issues in areas that were changed

9. **Report results**: Summarize the full outcome (including refinements from step 3)
   - **Per-reviewer summary**: How many findings each reviewer returned
   - **Multi-reviewer findings**: Issues multiple reviewers agreed on (highest confidence)
   - **Single-reviewer findings addressed**: Issues raised by one reviewer that were fixed
   - **Findings skipped**: What was not addressed and why
   - **Contradictions**: Any disagreements flagged for user review
   - **Tool failures**: If any tool failed or was skipped, explain why
   - Clean up: `rm -rf "$tmpdir"` (use the temp directory path from step 4)
