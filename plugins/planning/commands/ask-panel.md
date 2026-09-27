---
description: Ask Codex, GLM 5.3, and CodeRabbit to review a plan in parallel, synthesize and incorporate feedback
argument-hint: "[plan-file-path]"
---

# Ask Panel Command

Run Codex, GLM 5.3, and CodeRabbit plan reviews in parallel, synthesize their feedback, and incorporate improvements. Three different AI reviewers provide broad coverage and high confidence in findings they agree on.

- **Codex** (OpenAI) — reviews via the `codex-cli` plugin's supervised runner on `gpt-6-astra` (high effort, read-only, 25-minute cap with a progress check every 10 minutes)
- **GLM 5.3** (Z.ai) — reviews via `opencode run`, proactively explores the repo
- **CodeRabbit** — reviews via `coderabbit:code-reviewer` agent, reads repo files directly

Use `$ARGUMENTS` as an optional path to the plan file. If not provided, use the active plan file from the current conversation context (typically in `~/.claude/plans/`).

## Steps

1. **Check prerequisites**: Verify available tools
   - Run `codex --version 2>&1` — note if Codex is available
   - Run `opencode --version 2>&1` — note if opencode (for GLM) is available
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

   **Launch all reviewers concurrently** in a single message, each with `run_in_background: true`: the Codex and GLM seats as their own `Bash` calls, CodeRabbit as an `Agent` call. If a CLI tool was unavailable (detected in step 1), skip that seat.

   **Do NOT combine multiple reviewers into a single Agent or Bash call.** Combining CLI tools into one shell command causes bash operator precedence bugs that silently break variable scoping.

   **Shared brief.** First write the review brief once with the file-writing tool, next to the plan (`<plan dir>/panel-brief.md`, outside the repo); the Codex and GLM seats both read it, then the plan file itself, so nothing in the plan is ever expanded by the shell:

   > Review the implementation plan that follows this brief. You may read repository files for context; do not edit anything. Evaluate: 1) Is the plan standalone and understandable without conversation context? 2) Are acceptance criteria clear and actionable? 3) Does it include test coverage requirements? 4) Does it match the repo's architectural patterns and conventions? 5) Risks, gaps, or missing edge cases? Provide specific, actionable feedback organized by category, citing file:line where the repo contradicts the plan.

   Every seat command below is plain — no variables, `$(…)`, `||` guards, or heredocs, which a session pinned to a worktree refuses as too complex to verify. Use resolved absolute paths in single quotes (`~` does not expand inside quotes; write an embedded `'` as `'\''`).

   **Codex reviewer** (if codex CLI is available): run it yourself as a background `Bash` call — not inside an Agent. Astra on a whole plan can take well over 10 minutes, and a subagent's single foreground shell call is capped at 10; the runner (`scripts/codex-run.py` in the `codex-cli` plugin) supervises it instead: 25-minute cap, killed early if its output has been flat for 10 minutes, and a distinct exit code for every way it can fail. Locate it first — `printenv CODEX_RUN` (a checkout's copy, for changes not installed yet), else:

   ```bash
   find ~/.claude/plugins ~/.cursor/plugins ~/.grok/installed-plugins ~/.grok/plugins -path '*codex-cli*/scripts/codex-run.py' 2>/dev/null | xargs -r ls -t 2>/dev/null | head -n1
   ```

   Nothing printed means the codex-cli plugin isn't installed: skip the seat and say so. Otherwise, with that path:

   ```bash
   uv run --script '<runner path>' --model astra --prompt-file '<brief path>' --prompt-file '<plan path>'
   ```

   A non-zero exit is a failed seat — report the runner's reason, never "no findings". If it stalls on a big plan, one retry on an excerpt (design and work-breakdown sections, in their own file) beats a longer cap.

   **GLM reviewer** (if opencode CLI is available): also a background `Bash` call from you, not an Agent — whole-plan GLM reviews outlast a subagent's 10-minute shell call. The argument restricts its tools: in non-interactive mode, opencode kills the run as soon as GLM tries a shell command or reads outside the repo. Always use `--` before the message.

   ```bash
   cat -- '<brief path>' '<plan path>' | opencode run -m zai-coding-plan/glm-5.3 -- 'Follow the review brief on stdin; the full plan follows it. Use ONLY your read, grep and glob tools, and ONLY on files inside the current repository directory. Do not run shell commands.'
   ```

   Stop it with the task-stop tool if it is still running at 20 minutes. A stopped run, a non-zero exit, or empty output is a failed seat.

   **CodeRabbit reviewer**:
   Use the Agent tool with `subagent_type: "coderabbit:code-reviewer"` and `run_in_background: true`.
   Include the full plan text in the prompt along with these review questions:
   1. Is the plan standalone and understandable without conversation context?
   2. Are acceptance criteria clear, actionable, and sufficient as exit criteria?
   3. Does the plan include adequate test coverage requirements?
   4. Does the plan match the repo's architectural patterns and conventions?
   5. Are there any risks, gaps, or missing edge cases?
   Ask the agent to read relevant repo files to ground its review.

   Wait for all seats to complete (you are notified as each background call or agent finishes).

5. **Collect results**: Read each agent's returned result. If any agent reported an error or was skipped, proceed with the others' findings.

6. **Synthesize feedback**: Compile a unified list of all findings from all reviewers. Every finding should be evaluated on its own merit regardless of which reviewer raised it.
   - **Prioritization**: Findings flagged by multiple reviewers are likely higher priority, but a finding from a single reviewer is still valid and should be evaluated
   - **Reviewer strength**: Codex (astra) tends to be the strongest reviewer. Give its unique findings strong consideration. GLM and CodeRabbit may catch things Codex misses but weigh their findings accordingly.
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
