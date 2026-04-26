# planning

Commands for submitting implementation plans to external AI reviewers and incorporating feedback.

## Commands

### `/planning:ask-codex [plan-file-path]`

Submit a plan to Codex CLI (OpenAI) for review. Pipes review instructions and plan content to `codex exec -`, which evaluates the plan in the context of the current repository.

### `/planning:ask-kimi [plan-file-path]`

Submit a plan to Kimi K2.6 (Moonshot AI via Fireworks) for review using opencode CLI. Kimi proactively explores the repository to understand conventions before reviewing the plan.

### `/planning:ask-coderabbit [plan-file-path]`

Submit a plan to CodeRabbit for review using the `coderabbit:code-reviewer` agent. The agent reads repo files directly to ground its review in actual project state. Does not require git diffs — works on plan documents directly.

### `/planning:ask-panel [plan-file-path]`

Run all three reviewers (Codex, Kimi, CodeRabbit) in parallel, synthesize feedback, and incorporate improvements. Consensus findings (multiple reviewers agree) are prioritized.

## Prerequisites

- [Codex CLI](https://developers.openai.com/codex/cli) installed (`npm i -g @openai/codex`) (for ask-codex and ask-panel)
- [opencode CLI](https://opencode.ai) installed with Fireworks AI configured (for ask-kimi and ask-panel)
- CodeRabbit plugin installed (for ask-coderabbit and ask-panel) — uses the `coderabbit:code-reviewer` agent, no CLI required
