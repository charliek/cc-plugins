---
description: Check whether the local Grok CLI is installed and authenticated
argument-hint: ""
allowed-tools: Bash(command:*), Bash(grok:*), AskUserQuestion
---

Check that the Grok CLI is ready to use, then report a concise readiness summary.

## Steps

1. **Check the CLI is installed:**

   ```bash
   command -v grok
   ```

   - If this fails, the CLI is not installed. Tell the user to install it with `curl -fsSL https://x.ai/cli/install.sh | bash` and stop. Do **not** auto-run the installer; let the user run it themselves (they can use the `! <command>` prefix to run a command in this session).

2. **Check version:**

   ```bash
   grok version
   ```

3. **Check authentication:**

   ```bash
   grok models
   ```

   - If the output includes a logged-in account (for example `You are logged in with grok.com.`) and lists model ids, authentication is good. This is a local check — it can't detect every server-side auth failure; the first real `grok -p` call is the true probe.
   - If it reports the user is not logged in or fails to list models, tell them to run `grok login` (it opens a browser). Suggest the `! grok login` prefix so the login flow runs in this session. For headless/SSH machines, `grok login --device-auth`.

4. **Report a readiness summary** covering:
   - Installed? (path from step 1)
   - Version (from `grok version`)
   - Authenticated? (from `grok models`)
   - Next steps if anything is missing (install, or `grok login`).

5. **Mention model selection:** this plugin's commands pin `grok-4.6` at `--effort high` (they do NOT inherit `~/.grok/config.toml`'s default). Override per call with `--model <id>` and `--effort low|medium|high|xhigh`. Fast mode is `--effort low`. List ids with `grok models`.
