---
description: Ask Codex to review and challenge an implementation plan
argument-hint: "[plan-file-path]"
---

# Ask Codex Command

Submit an implementation plan to Codex CLI for review, running `gpt-6-astra` at high reasoning effort through the codex-cli plugin's supervised runner. Codex reads the plan and provides feedback on completeness, acceptance criteria, test coverage, and architectural alignment.

Use `$ARGUMENTS` as an optional path to the plan file. If not provided, use the active plan file from the current conversation context (typically in `~/.claude/plans/`).

## Steps

1. **Check prerequisites**: Verify Codex CLI is available
   - Run `codex --version 2>&1`
   - If the command fails, tell the user to install Codex CLI (`npm i -g @openai/codex`) and stop
   - The review runs through the `codex-cli` plugin's runner (step 4), so that plugin must be installed too

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

4. **Submit the plan to Codex for review**: run the plan through the codex-cli plugin's supervised runner, `scripts/codex-run.py`, on `gpt-6-astra` (OpenAI's frontier model — plan review is where its depth pays off). Astra is slow on a big plan, so the runner gives it a 25-minute cap and checks every 10 minutes that it is still making progress; that is longer than one foreground shell call allows, so launch it with `run_in_background: true` and you will be told when it exits. Pipe the plan in as data — never expand it into a quoted shell argument, where `$`, backticks, and quotes in the plan get interpreted.

```bash
runner=${CODEX_RUN:-$(find ~/.claude/plugins ~/.cursor/plugins ~/.grok/installed-plugins ~/.grok/plugins \
  -path '*codex-cli*/scripts/codex-run.py' 2>/dev/null | xargs -r ls -t 2>/dev/null | head -n1)}
[ -f "$runner" ] || { echo "codex-run.py not found: install the codex-cli plugin (or set CODEX_RUN)"; exit 9; }
plan='<plan-file-path>'
test -f "$plan" || { echo "plan not found"; exit 2; }
{
  cat <<'PLAN_REVIEW_9f3a2b1c'
Review the following implementation plan. You may read repository files for context; do not edit anything. Evaluate: 1) Is the plan standalone and understandable without conversation context? 2) Are acceptance criteria clear and actionable? 3) Does it include test coverage requirements? 4) Does it match the repo's architectural patterns and conventions? 5) Risks, gaps, or missing edge cases? Provide specific, actionable feedback organized by category, citing file:line where the repo contradicts the plan.
---BEGIN PLAN---
PLAN_REVIEW_9f3a2b1c
  cat -- "$plan"
  echo '---END PLAN---'
} | uv run --script "$runner" --model astra
```

   Put the plan path in **single** quotes (write an embedded `'` as `'\''`): inside double quotes, a `$(…)` or backtick in the path would still run. Use a fresh random suffix on the heredoc delimiter each time. The runner prints the review on stdout. Any non-zero exit means **no review** (the runner says why: stalled, capped, empty, usage-limited, auth) — report it; never treat it as "no findings". If a big plan stalls, retry once with a narrower brief (for example only the design and work-breakdown sections) rather than a longer cap.

5. **Evaluate findings**: Analyze each piece of feedback from Codex
   - **Fix**: missing acceptance criteria, unclear exit conditions, incomplete test coverage, architectural misalignment, standalone readability issues, missing edge cases
   - **Skip**: style-only suggestions, subjective preferences, feedback that doesn't improve the plan

6. **Incorporate feedback**: Edit the plan file with worthwhile improvements

7. **Report results**: Summarize what was refined (step 3), what Codex found, what was incorporated, and what was skipped
