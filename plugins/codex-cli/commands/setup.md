---
description: Check whether the local Codex CLI is installed and authenticated
argument-hint: ""
allowed-tools: Bash(command:*), Bash(codex:*), AskUserQuestion
---

Check that the Codex CLI is ready to use, then report a concise readiness summary.

## Steps

1. **Check the CLI is installed:**

   ```bash
   command -v codex
   ```

   - If this fails, the CLI is not installed. Tell the user to install it with `npm install -g @openai/codex` and stop. Do **not** auto-run the installer; let the user run it themselves (they can use the `! <command>` prefix to run a command in this session).

2. **Check version:**

   ```bash
   codex --version
   ```

3. **Check authentication:**

   ```bash
   codex login status
   ```

   - If the output shows a logged-in account, authentication is good.
   - If it reports the user is not logged in, tell them to run `codex login` (it opens a browser). Suggest the `! codex login` prefix so the login flow runs in this session.

4. **Report a readiness summary** covering:
   - Installed? (path from step 1)
   - Version (from `codex --version`)
   - Authenticated? (from `codex login status`)
   - Next steps if anything is missing (install, or `codex login`).

5. **Mention model selection:** this plugin's commands pin `gpt-5.6-sol` at `model_reasoning_effort="high"` (they do NOT inherit `~/.codex/config.toml`'s default). Override per call with `--model <id>` and `--effort none|minimal|low|medium|high|xhigh`.
