# planning

Commands for submitting implementation plans to external AI models for review and incorporating feedback.

## Commands

### `/planning:ask-codex [plan-file-path]`

Submit a plan to Codex CLI (OpenAI) for review. Pipes review instructions and plan content to `codex exec -`, which evaluates the plan in the context of the current repository.

### `/planning:ask-kimi [plan-file-path]`

Submit a plan to Kimi K2.5 (Moonshot AI via Fireworks) for review using opencode CLI. Kimi proactively explores the repository to understand conventions before reviewing the plan.

### `/planning:ask-panel [plan-file-path]`

Run both Codex and Kimi reviews in parallel, synthesize feedback, and incorporate improvements. Consensus findings (both models agree) are prioritized.

## Prerequisites

- [Codex CLI](https://developers.openai.com/codex/cli) installed (`npm i -g @openai/codex`) (for ask-codex and ask-panel)
- [opencode CLI](https://opencode.ai) installed with Fireworks AI configured (for ask-kimi and ask-panel)
