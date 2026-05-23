---
description: Check whether the local Cursor agent CLI is installed and authenticated
argument-hint: ""
allowed-tools: Bash(command:*), Bash(agent:*), AskUserQuestion
---

Check that the Cursor `agent` CLI is ready to use, then report a concise readiness summary.

## Steps

1. **Check the CLI is installed:**

   ```bash
   command -v agent
   ```

   - If this fails, the CLI is not installed. Tell the user to install the Cursor CLI from the official source — `curl https://cursor.com/install -fsS | bash` (see https://cursor.com/cli) — and stop. Do **not** auto-run a `curl | bash` installer; let the user run it themselves (they can use the `! <command>` prefix to run it in this session).

2. **Check version and account:**

   ```bash
   agent about
   ```

   This reports the CLI version, system info, and account.

3. **Check authentication:**

   ```bash
   agent status
   ```

   - If the output shows an authenticated account, authentication is good.
   - If it reports the user is not logged in, tell them to run `agent login` (it opens a browser). Suggest the `! agent login` prefix so the login flow runs in this session.

4. **Report a readiness summary** covering:
   - Installed? (path from step 1)
   - Authenticated? (account from `agent status`)
   - Version (from `agent about`)
   - Next steps if anything is missing (install, or `agent login`).

5. **Mention discovery:** the default model used by this plugin's commands is `gpt-5.5-high`; run `agent --list-models` to see all available model ids that can be passed with `--model`.
