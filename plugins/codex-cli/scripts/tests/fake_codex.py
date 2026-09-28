#!/usr/bin/env python3
"""Stand-in for `codex exec --json` in codex-run tests. Behavior comes from FAKE_CODEX_MODE.

Like the real CLI in --json mode, it writes JSONL events to stdout, reports
API failures as `error` / `turn.failed` events, and does not echo the prompt.
"""

import json
import os
import signal
import subprocess
import sys
import time


def arg_after(flag):
    args = sys.argv[1:]
    return args[args.index(flag) + 1] if flag in args else None


def event(kind, **fields):
    print(json.dumps({"type": kind, **fields}), flush=True)


def fail(message, code=1):
    # FAKE_CODEX_EVENTS picks which failure events to emit, so each parser
    # branch can be tested alone.
    which = os.environ.get("FAKE_CODEX_EVENTS", "both")
    if which in ("both", "error"):
        event("error", message=message)
    if which in ("both", "turn.failed"):
        event("turn.failed", error={"message": message})
    sys.exit(code)


def ignore_term_child():
    # A process that ignores SIGTERM, like a codex tool call mid-command. The
    # shell records its pid only after the trap is set, then execs sleep (an
    # ignored signal stays ignored across exec), so there is exactly one
    # process to track and it is already immune when the test sees it.
    childfile = os.environ["FAKE_CODEX_CHILDFILE"]
    subprocess.Popen(["sh", "-c", "trap '' TERM; echo $$ > \"$1.tmp\" && mv \"$1.tmp\" \"$1\"; exec sleep 300", "sh", childfile])
    deadline = time.monotonic() + 10
    while not os.path.exists(childfile) and time.monotonic() < deadline:
        time.sleep(0.02)


def main():
    mode = os.environ.get("FAKE_CODEX_MODE", "ok")
    if mode == "stubborn":
        # Before the pid file announces readiness, so a test's first signal
        # always meets a codex that ignores it.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    out = arg_after("-o")
    prompt = sys.stdin.read()
    if os.environ.get("FAKE_CODEX_PIDFILE"):
        with open(os.environ["FAKE_CODEX_PIDFILE"], "w") as handle:
            handle.write(str(os.getpid()))
    if os.environ.get("FAKE_CODEX_RECORD"):
        with open(os.environ["FAKE_CODEX_RECORD"], "w") as handle:
            json.dump({"argv": sys.argv[1:], "prompt": prompt}, handle)

    event("thread.started", thread_id="fake")
    event("turn.started")
    if mode == "ok":
        with open(out, "w") as handle:
            handle.write("no issue — looks right, fake.py:1\n")
    elif mode == "progress":
        to_stderr = os.environ.get("FAKE_CODEX_PROGRESS_STREAM") == "stderr"
        for tick in range(int(os.environ.get("FAKE_CODEX_TICKS", "10"))):
            if to_stderr:
                print(f"working on step {tick}", file=sys.stderr, flush=True)
            else:
                event("item.completed", item={"type": "command_execution", "command": f"step {tick}"})
            time.sleep(float(os.environ.get("FAKE_CODEX_INTERVAL", "0.3")))
        with open(out, "w") as handle:
            handle.write("finished after steady progress\n")
    elif mode == "stall":
        time.sleep(300)
    elif mode == "chatty":
        while True:
            event("item.started", item={"type": "reasoning"})
            time.sleep(0.1)
    elif mode == "stubborn":
        time.sleep(300)
    elif mode == "grandchild":
        ignore_term_child()
        time.sleep(300)
    elif mode == "orphan":
        # Finishes normally but leaves a descendant behind.
        ignore_term_child()
        with open(out, "w") as handle:
            handle.write("review done, one shell left running\n")
    elif mode == "empty":
        pass
    elif mode == "blank":
        with open(out, "w") as handle:
            handle.write("  \n")
    elif mode == "limited":
        fail("You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage "
             "to purchase more credits or try again at Sep 19th, 2026 3:13 AM.")
    elif mode == "auth":
        fail("unexpected status 401 Unauthorized")
    elif mode == "auth_before_session":
        print("Error: not logged in. Run `codex login` first.", file=sys.stderr)
        sys.exit(1)
    elif mode == "crash":
        # Tool output that mentions limits must not make an unrelated crash "limited".
        event("item.completed", item={
            "type": "command_execution",
            "aggregated_output": "retry on 429 / usage limit / rate limit; 401 Unauthorized paths",
        })
        print("thread panicked: boom", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
