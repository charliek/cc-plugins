---
name: prox
description: "Use when a prox.yaml file exists in the project root, or when the user mentions prox, or asks to start/stop/restart development processes, view logs, make HTTP requests to local services, or inspect proxy traffic. Also use when the user says a program 'is running via prox' or asks you to 'start it with prox'."
version: 1.0.0
---

# Prox Process Manager

prox is a process manager for local development written in Go. It provides process supervision with automatic restarts, real-time log aggregation, HTTPS reverse proxy with subdomain routing, an interactive TUI, and a background daemon mode with a REST API.

## First Step: Read prox.yaml

**Always read the project's `prox.yaml` before taking any action.** This file defines the project's local development topology — what processes exist, what commands they run, what ports they use, and whether proxy routing is enabled. Without reading this file you cannot help effectively.

If the config file is at a non-default path, the user or CLAUDE.md will specify it (the `--config` / `-c` flag overrides the default).

## Process Management

When a project has a `prox.yaml`, **use prox to manage processes** — do not run process commands directly.

| Task | Command |
|------|---------|
| Start all processes (daemon) | `prox up -d` |
| Start specific process | `prox up -d <name>` |
| Stop one process | `prox stop <name>` |
| Restart one process | `prox restart <name>` |
| Stop everything | `prox down` |
| Check what's running | `prox status` |
| Attach interactive TUI | `prox attach` |

**Always use `-d` (daemon mode)** when starting prox so the CLI returns control immediately. Do not start prox in the foreground — it will block.

**Never kill processes directly** (e.g., `kill <pid>`). Use prox commands so it can track state and handle restarts correctly.

## Viewing Logs

prox aggregates output from all processes. When debugging, check logs first.

```bash
prox logs --lines 50                          # Recent 50 lines, all processes
prox logs --lines 50 --process api            # Recent 50 lines from "api"
prox logs -f --process api                    # Stream logs from "api"
prox logs --lines 100 --pattern ERROR         # Filter for "ERROR"
prox logs --lines 100 --pattern "err.*" --regex  # Regex filter
```

**Always use `--lines N`** to limit output. Without it, prox may return hundreds of lines that flood context.

**Pipe through bash tools when needed** — prox's built-in `--pattern` handles most filtering, but for counting (`| grep -c ERROR`), multi-pattern matching (`| grep -E "ERROR|WARN"`), or extracting specific fields, pipe through standard unix tools.

For daemon startup issues, check the daemon log directly: `cat .prox/prox.log`

## Making HTTP Requests

How to reach services depends on whether the proxy is configured in prox.yaml.

### With proxy enabled

Read the `proxy` and `services` sections of prox.yaml. Services are accessible via subdomain routing:

```
http://<service>.<domain>:<http_port>/path
```

For example, if prox.yaml contains:
```yaml
proxy:
  http_port: 6788
  domain: lvh.me

services:
  api: 8000
  app: 3000
```

Then:
- `curl http://api.lvh.me:6788/endpoint` → reaches the api service on port 8000
- `curl http://app.lvh.me:6788/` → reaches the app service on port 3000

For HTTPS, use `https://<service>.<domain>:<https_port>/path` (requires mkcert setup).

### Without proxy

Use direct ports from the process commands in prox.yaml. For example, if a process runs `uvicorn ... --port 8000`, reach it at `http://localhost:8000/endpoint`.

### Inspecting proxy traffic

```bash
prox requests                                  # Recent requests
prox requests -f                               # Stream in real-time
prox requests --subdomain api --min-status 400 # Filter for errors on api
prox requests <id>                             # Details for specific request
prox requests <id> --body                      # Include captured bodies
```

## Configuration (prox.yaml)

Processes can be defined in simple form (string) or expanded form (object):

```yaml
processes:
  # Simple: just a command
  web: npm run dev

  # Expanded: command with environment and health check
  api:
    cmd: go run ./cmd/server
    env:
      PORT: "8080"
    env_file: .env.api
    healthcheck:
      cmd: curl -f http://localhost:8080/health
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
```

Environment variable precedence (later overrides earlier):
1. System environment
2. Global `env_file`
3. Process-specific `env_file`
4. Process-specific `env` map

For the full configuration reference including all proxy, service, and certificate fields, read `references/configuration.md`.

## CLI Help

For detailed flags and options on any command, run:
```bash
prox <command> --help
```

The CLI help is comprehensive and always up to date. Use it as the authoritative reference for command syntax.

## References

For detailed documentation beyond what's covered here:
- `references/configuration.md` — all prox.yaml fields (proxy, services, certs, health checks)
- `references/api.md` — HTTP API endpoints for scripting and automation

## Runtime State

prox stores state in `.prox/` within the project directory:
- `.prox/prox.state` — API port, PID, host (used for auto-discovery by CLI commands)
- `.prox/prox.pid` — process ID with file locking
- `.prox/prox.log` — daemon logs (stdout/stderr in background mode)

The `.prox/` directory should be in `.gitignore`.
