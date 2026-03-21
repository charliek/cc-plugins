# prox

Claude Code skill for working with the [prox](https://github.com/charliek/prox) process manager.

## What it does

Activates automatically when Claude detects a `prox.yaml` in the project or when you mention prox. Gives Claude knowledge of:

- **Process management** — start/stop/restart processes via prox instead of running commands directly
- **Log viewing** — aggregate logs with filtering, pattern matching, and output limiting
- **HTTP requests** — understands proxy subdomain routing to construct correct service URLs
- **Traffic inspection** — view and filter proxy requests for debugging
- **Configuration** — prox.yaml format for processes, proxy, health checks, and certificates

## References

Includes detailed reference docs for:
- `configuration.md` — all prox.yaml fields
- `api.md` — HTTP API endpoints for scripting
