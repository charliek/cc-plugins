---
description: Ask Codex, Kimi K2.5, and CodeRabbit to review a plan in parallel, synthesize and incorporate feedback
argument-hint: "[plan-file-path]"
---

# Ask Panel Command

Run Codex, Kimi K2.5, and CodeRabbit plan reviews in parallel, synthesize their feedback, and incorporate improvements. Three different AI reviewers provide broad coverage and high confidence in findings they agree on.

- **Codex** (OpenAI) — reviews via `codex exec`, explores the repo with `--full-auto`
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

3. **Read and refine the plan before submission**: Read the plan and verify it meets these review-readiness criteria. Edit the plan file to fix any gaps before proceeding.

   Checklist — the plan must have:
   - [ ] **Context section**: Why this change is being made (problem, motivation, intended outcome)
   - [ ] **File list**: Paths of all files to be created or modified
   - [ ] **Acceptance criteria**: Explicit exit criteria — a reader knows exactly when the plan is "done"
   - [ ] **Test plan**: What tests to add/update, what commands to run for verification
   - [ ] **No conversation dependencies**: Fully understandable without prior chat context
   - [ ] **Repo conventions**: Matches the repo's existing patterns (naming, structure, tooling)

4. **Run reviews in parallel**: Launch all available reviewers as background agents. Warn the user this may take a couple minutes.

   Read the plan file content so it can be included in agent prompts.

   **Launch all reviewers concurrently** using a single message with multiple Agent tool calls, each with `run_in_background: true`. If a CLI tool was unavailable (detected in step 1), skip that agent.

   **Codex reviewer** (if codex CLI is available):
   Use the Agent tool with `subagent_type: "general-purpose"` and `run_in_background: true`.
   Prompt the agent to run the Codex review and return only the review text:

   > You are a plan reviewer. Run the following Bash command to get a Codex review of an implementation plan, then return ONLY the review text (no commentary or wrapper).
   >
   > Run as a single Bash command:
   > ```bash
   > tmpdir=$(mktemp -d) && \
   > codex exec --full-auto -o "$tmpdir/codex.txt" \
   >   "Review the following implementation plan. Evaluate standalone readability, acceptance criteria, test coverage, and repo pattern alignment. Provide specific, actionable feedback organized by category.
   >
   >   ---BEGIN PLAN---
   >   <paste full plan text here>
   >   ---END PLAN---" \
   >   2>"$tmpdir/stderr.txt" && \
   > cat "$tmpdir/codex.txt" && \
   > rm -rf "$tmpdir"
   > ```
   >
   > If codex fails (non-zero exit or empty output file), read $tmpdir/stderr.txt and report the error instead.

   **Kimi reviewer** (if opencode CLI is available):
   Use the Agent tool with `subagent_type: "general-purpose"` and `run_in_background: true`.
   Prompt the agent to run the Kimi review and return only the review text:

   > You are a plan reviewer. Run the following Bash command to get a Kimi K2.5 review of an implementation plan, then return ONLY the review text (no commentary or wrapper).
   >
   > Run as a single Bash command:
   > ```bash
   > tmpdir=$(mktemp -d) && \
   > cat "<plan-file-path>" | opencode run \
   >   -m "fireworks-ai/accounts/fireworks/models/kimi-k2p5" \
   >   -- "Review the following implementation plan. Evaluate: 1) Is the plan standalone? 2) Are acceptance criteria clear? 3) Does it include test coverage? 4) Does it match repo conventions? Provide specific, actionable feedback." \
   >   > "$tmpdir/output.txt" 2>"$tmpdir/stderr.txt" && \
   > cat "$tmpdir/output.txt" && \
   > rm -rf "$tmpdir"
   > ```
   >
   > If opencode fails (non-zero exit or empty output file), read $tmpdir/stderr.txt and report the error instead.

   **CodeRabbit reviewer**:
   Use the Agent tool with `subagent_type: "coderabbit:code-reviewer"` and `run_in_background: true`.
   Include the full plan text in the prompt along with these review questions:
   1. Is the plan standalone and understandable without conversation context?
   2. Are acceptance criteria clear, actionable, and sufficient as exit criteria?
   3. Does the plan include adequate test coverage requirements?
   4. Does the plan match the repo's architectural patterns and conventions?
   5. Are there any risks, gaps, or missing edge cases?
   Ask the agent to read relevant repo files to ground its review.

   Wait for all agents to complete.

5. **Collect results**: Read each agent's returned result. If any agent reported an error or was skipped, proceed with the others' findings.

6. **Synthesize feedback**: Compile a unified list of all findings from all reviewers. Every finding should be evaluated on its own merit regardless of which reviewer raised it.
   - **Prioritization**: Findings flagged by multiple reviewers are likely higher priority, but a finding from a single reviewer is still valid and should be evaluated
   - **Reviewer strength**: Codex tends to be the strongest reviewer. Give its unique findings strong consideration. Kimi and CodeRabbit may catch things Codex misses but weigh their findings accordingly.
   - **Contradictions**: When reviewers disagree on the same topic, flag for user review rather than acting autonomously
   - Do not discard findings just because only one reviewer raised them

7. **Incorporate feedback**: Apply improvements to the plan file
   - Evaluate every finding on its own merit — does it make the plan better?
   - Skip only genuine nitpicks and style-only suggestions

8. **Report results**: Summarize the full outcome (including refinements from step 3)
   - **Per-reviewer summary**: How many findings each reviewer returned
   - **Multi-reviewer findings**: Issues multiple reviewers agreed on (highest confidence)
   - **Single-reviewer findings addressed**: Issues raised by one reviewer that were fixed
   - **Findings skipped**: What was not addressed and why
   - **Contradictions**: Any disagreements flagged for user review
   - **Tool failures**: If any agent failed or was skipped, explain why
