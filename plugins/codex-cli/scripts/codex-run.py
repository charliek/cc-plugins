#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Run one read-only `codex exec` with a hard cap and a stall watchdog.

This is the shared engine for every scripted Codex call in the cc-plugins
flows (gated-commit reviews, branch reviews, plan-panel seats). It exists so
those callers stop re-implementing the same fragile shell recipe, and so the
two things a shell recipe does badly are done once, here:

* **Supervision.** A review can legitimately run 20+ minutes, longer than one
  shell-tool call allows, so callers launch this in the background and are
  told when it exits. Meanwhile it checks that Codex is still making progress
  (its log keeps growing) and kills it if the log has been flat for a whole
  stall window, or when the hard cap is reached.
* **Outcome classification.** A killed, empty, or rate-limited run is "no
  review", never "no findings". Distinct exit codes let the caller pick the
  fallback without parsing prose.

Usage:
    codex-run.py [--model sol|astra|luna|<id>] [--effort LEVEL]
                 [--prompt-file PATH ...]        # repeatable, joined in order; else stdin
                 [--changes-since REF]           # append the diff since REF (HEAD = uncommitted only)
                 [--cap-min N] [--stall-min N] [--out PATH] [--keep]
    codex-run.py --changes-since REF --bundle-only   # print the bundle for another reviewer; no codex run

Output: the final Codex message on stdout. Progress and status lines go to
stderr, prefixed `codex-run:`.

Exit codes:
    0 ok        final message is on stdout
    2 usage     bad arguments or empty prompt
    3 failed    codex exited non-zero for another reason
    4 empty     codex exited 0 but wrote no final message
    5 stalled   no new output for a whole stall window; killed
    6 capped    hit the hard cap; killed
    7 limited   usage/rate limit or model capacity; do not retry codex
    8 auth      not logged in / unauthorized
    9 missing   the codex binary was not found
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ALIASES = {"sol": "gpt-6.1-sol", "astra": "gpt-6-astra", "luna": "gpt-6-luna"}
# Astra is the slower, deeper model; everything else gets the shorter cap.
CAP_MINUTES = {"gpt-6-astra": 25.0}
DEFAULT_CAP_MINUTES = 20.0
DEFAULT_STALL_MINUTES = 10.0
EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra")
MODEL_ID = re.compile(r"^[A-Za-z0-9._-]+$")

EXIT = {
    "ok": 0,
    "usage": 2,
    "failed": 3,
    "empty": 4,
    "stalled": 5,
    "capped": 6,
    "limited": 7,
    "auth": 8,
    "missing": 9,
}

# Matched against codex's own error events (and the tail of stderr, for errors
# raised before a session starts) -- never against tool output, where a file
# Codex read can mention rate limits innocently.
LIMITED = re.compile(
    r"usage limit|rate.?limit|too many requests|\b429\b|at capacity|overloaded|\b503\b",
    re.IGNORECASE,
)
AUTH = re.compile(r"\b401\b|unauthori[sz]ed|not logged in|codex login", re.IGNORECASE)

# Past this size, inlining the changes crowds out the review itself; hand Codex
# a file and tell it to read only what it needs.
INLINE_MAX_LINES = 900
INLINE_MAX_BYTES = 100_000
UNTRACKED_MAX_BYTES = 200_000
INDEX_MAX_ENTRIES = 300
KILL_GRACE_SECONDS = 10.0
CLASSIFY_TAIL_LINES = 15

# Read-only git: no optional index locks, so `git status` never writes a stat
# refresh into the index of a tree another tool may be using.
GIT_ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")


def say(message: str) -> None:
    # A caller that stopped reading stderr must not take the supervision down
    # with it: an exception here would leave codex running.
    try:
        print(f"codex-run: {message}", file=sys.stderr, flush=True)
    except OSError:
        pass


def resolve_model(value: str) -> str:
    model = ALIASES.get(value, value)
    if not MODEL_ID.fullmatch(model):
        raise ValueError(f"invalid model id: {value!r}")
    return model


def git(*args: str, cwd=None) -> str:
    return git_bytes(*args, cwd=cwd).decode("utf-8", errors="replace")


def git_bytes(*args: str, cwd=None) -> bytes:
    try:
        return subprocess.run(
            ["git", *args], check=True, capture_output=True, cwd=cwd, env=GIT_ENV
        ).stdout
    except subprocess.CalledProcessError as err:
        err.stderr = (err.stderr or b"").decode("utf-8", errors="replace")
        raise


def is_text(path: Path) -> bool:
    with path.open("rb") as handle:
        return b"\0" not in handle.read(8192)


def build_changes(base: str, run_dir: Path) -> str:
    """Describe the changes since `base`: committed, staged, unstaged, untracked.

    The diff is the working tree against `base` -- the tree that will be
    committed -- not the intermediate staged state. Nothing is staged and no
    index lock is taken, so it is safe while other tools use the same tree.
    Runs from the repository root, whatever the caller's directory.
    """
    top = Path(git("rev-parse", "--show-toplevel").rstrip("\n"))

    def g(*args: str) -> str:
        return git(*args, cwd=top)

    g("rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")

    # Built line by line so each file's range is recorded as it is appended.
    # Parsing headers back out afterwards would mistake an untracked file's
    # own `diff --git` or `===== x =====` lines for boundaries.
    out: list = []
    ranges: list = []  # (name, first line, last line), 1-based

    def add(text: str) -> None:
        # Only the terminating newline goes: a file's own trailing blank lines stay.
        out.extend((text[:-1] if text.endswith("\n") else text).split("\n"))

    log = g("log", "--oneline", f"{base}..HEAD")
    if log.strip():
        add(f"--- commits since {base} ---\n{log}")
        out.append("")
    add("--- changed files ---\n" + g("status", "--short", "--untracked-files=all"))
    out.append("")
    # Plumbing, not `git diff`: the porcelain refreshes stat info and rewrites
    # the index even with optional locks off. Plumbing skips textconv filters
    # unless asked, so ask.
    add(f"--- diff against {base} (committed + staged + unstaged) ---")
    # Names come from git's own NUL-separated list, which diffs the same queue
    # in the same order as the patch -- no parsing of quoted or odd paths.
    names = [n for n in g("diff-index", "--name-only", "-z", "-M", base).split("\0") if n]
    starts = []
    patch = g("diff-index", "-p", "-M", "--textconv", base)
    for line in (patch[:-1] if patch.endswith("\n") else patch).split("\n"):
        # In a patch, content lines carry a +/-/space prefix, so an unprefixed
        # `diff --git` line is always a real file header.
        if line.startswith("diff --git "):
            starts.append((len(out) + 1, line))
        out.append(line)
    for i, (first, header) in enumerate(starts):
        last = starts[i + 1][0] - 1 if i + 1 < len(starts) else len(out)
        name = names[i] if len(names) == len(starts) else header[len("diff --git "):]
        ranges.append((name, first, last))

    raw = git_bytes("ls-files", "--others", "--exclude-standard", "-z", cwd=top)
    blocks = []
    for entry in (e for e in raw.split(b"\0") if e):
        path = top / os.fsdecode(entry)  # lossless, even for non-UTF-8 names
        name = entry.decode("utf-8", errors="replace")
        if path.is_symlink():
            blocks.append((name, f"===== {name} (symlink -> {os.readlink(path)}) ====="))
            continue
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > UNTRACKED_MAX_BYTES or not is_text(path):
            # Say so in a way any reviewer acts on: a big new source file must
            # still be read, just not inlined.
            blocks.append((name, f"===== {name} (not inlined: {size} bytes or binary; "
                                 "read it from the worktree before giving a verdict) ====="))
            continue
        blocks.append((name, f"===== {name} =====\n{path.read_text(errors='replace')}"))
    if blocks:
        out.append("")
        add("--- untracked file contents ---")
        for name, block in blocks:
            first = len(out) + 1
            add(block)
            ranges.append((name, first, len(out)))

    changes = "\n".join(out) + "\n"
    if len(out) <= INLINE_MAX_LINES and len(changes.encode()) <= INLINE_MAX_BYTES:
        return f"\n\n=== BEGIN CHANGES ===\n{changes}=== END CHANGES ===\n"

    diff_file = run_dir / "changes.diff"
    diff_file.write_text(changes)
    return (
        f"\n\nThe changes under review are large, so they are in a file: {diff_file}\n"
        "Do NOT run `git diff` or re-derive the changes. Read that file in slices by line "
        f"range (for example `sed -n '120,480p' {diff_file}`): a whole-file read comes back "
        "truncated. The index below gives each changed file's lines in it. Beyond that, read "
        "only the specific files, symbols, or line ranges you need, and list what you read in "
        "your report.\n" + index_text(ranges)
    )


def index_text(ranges: list) -> str:
    """Render the per-file line ranges of a large bundle.

    Long tool reads get truncated, so a reviewer has to read a big bundle in
    slices; the index tells it which slice holds which file.
    """
    if not ranges:
        return ""
    shown = [f"  {name}: lines {first}-{last}" for name, first, last in ranges[:INDEX_MAX_ENTRIES]]
    more = len(ranges) - len(shown)
    tail = f"  … and {more} more files; search the file for `diff --git` or `=====` headers\n" if more else ""
    return "Index:\n" + "\n".join(shown) + "\n" + tail


def read_prompt(args: argparse.Namespace) -> str:
    # Several files join in order, so a panel seat can pass a short brief and
    # then the plan file itself, with no shell plumbing to combine them.
    if args.prompt_file:
        return "\n\n".join(Path(f).read_text(encoding="utf-8") for f in args.prompt_file)
    if sys.stdin.isatty():
        return ""
    return sys.stdin.buffer.read().decode("utf-8")  # errors surface as a usage error


def log_size(*paths: Path) -> int:
    return sum(p.stat().st_size for p in paths if p.exists())


# os.waitid reached macOS only in Python 3.13; --no-waitid forces the fallback in tests.
CAN_PEEK = hasattr(os, "waitid") and hasattr(os, "WNOWAIT")


def exited(proc: subprocess.Popen) -> bool:
    """Has codex exited? Checked without reaping it where the OS allows.

    An exited-but-unreaped leader keeps its pid, so its process-group id cannot
    be reused by an unrelated group before kill_group sweeps it. Without
    waitid, poll() reaps; kill_group then leaves the group alone.
    """
    if proc.returncode is not None:
        return True
    if CAN_PEEK:
        try:
            return os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
        except ChildProcessError:
            return True
    return proc.poll() is not None


def signal_group(pgid: int, sig: int) -> None:
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError):
        pass


def kill_group(proc: subprocess.Popen, grace: float) -> None:
    """Stop codex and everything it started, whether or not codex is still up.

    SIGTERM first so codex can shut down cleanly, then SIGKILL to the whole
    group: a shell codex spawned can ignore SIGTERM or outlive codex itself,
    and a leftover process keeps the thread locked. The sweep lands only while
    codex is unreaped (alive or a zombie), because only then is the group id
    guaranteed to still be ours. With waitid that is always the case here.
    Without it, a codex that already exited on its own was reaped by poll(),
    so its group is not swept -- a stray descendant beats killing a stranger.
    """
    if proc.returncode is None and not (CAN_PEEK and exited(proc)):
        signal_group(proc.pid, signal.SIGTERM)
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            # Without waitid, checking would reap codex and forfeit the sweep,
            # so the fallback simply waits out the grace period.
            if CAN_PEEK and exited(proc):
                break
            time.sleep(0.05)
    if proc.returncode is None:
        signal_group(proc.pid, signal.SIGKILL)
    try:
        proc.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        pass


def error_events(stdout_log: Path) -> list:
    """Messages from codex's `error` / `turn.failed` JSON events."""
    messages = []
    if not stdout_log.exists():
        return messages
    for line in stdout_log.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "error":
            messages.append(str(event.get("message", "")))
        elif event.get("type") == "turn.failed":
            error = event.get("error")
            messages.append(str(error.get("message", "") if isinstance(error, dict) else error))
    return messages


def classify_failure(stdout_log: Path, stderr_log: Path) -> str:
    """Name a non-zero exit from codex's own error events.

    With `--json`, codex reports failures as structured events on stdout and
    does not echo the prompt, so tool output that happens to mention rate
    limits (a file Codex read, the prompt itself) is never classified. The
    tail of stderr covers errors raised before a session starts.
    """
    stderr_tail = []
    if stderr_log.exists():
        lines = [line for line in stderr_log.read_text(errors="replace").splitlines() if line.strip()]
        stderr_tail = lines[-CLASSIFY_TAIL_LINES:]
    tail = "\n".join(error_events(stdout_log) + stderr_tail)
    if LIMITED.search(tail):
        return "limited"
    if AUTH.search(tail):
        return "auth"
    return "failed"


def supervise(proc: subprocess.Popen, logs: tuple, cap_s: float, stall_s: float, signals: list) -> str:
    """Wait for codex; return 'exited', 'stalled', 'capped', or 'interrupted'."""
    poll = max(0.05, min(0.25, stall_s / 5, cap_s / 10))
    start = last_growth = last_report = time.monotonic()
    size = report_size = log_size(*logs)
    while True:
        # Checked first on every pass, so a codex that finished during the last
        # sleep is reported as exited rather than capped or stalled.
        if signals:
            return "interrupted"
        if exited(proc):
            return "exited"
        now = time.monotonic()
        current = log_size(*logs)
        if current != size:
            size, last_growth = current, now
        if now - start >= cap_s:
            return "capped"
        if now - last_growth >= stall_s:
            return "stalled"
        if now - last_report >= stall_s:
            say(
                f"{(now - start) / 60:.1f}m elapsed, output grew "
                f"{(current - report_size) / 1024:.1f} KB since the last check"
            )
            last_report, report_size = now, current
        time.sleep(poll)


def print_bundle(base) -> int:
    """Hand the same change bundle to a reviewer that is not codex (a native
    subagent, a fallback) so every route reviews exactly the same thing."""
    if not base:
        say("--bundle-only needs --changes-since REF")
        return EXIT["usage"]
    run_dir = Path(tempfile.mkdtemp(prefix="codex-run-"))
    try:
        bundle = build_changes(base, run_dir)
    except subprocess.CalledProcessError as err:
        say(f"could not collect changes since {base}: {(err.stderr or '').strip()}")
        shutil.rmtree(run_dir, ignore_errors=True)
        return EXIT["usage"]
    if not any(run_dir.iterdir()):
        shutil.rmtree(run_dir, ignore_errors=True)
    sys.stdout.write(bundle.lstrip("\n"))
    return EXIT["ok"]


def parse_args(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one read-only codex exec with a hard cap and a stall watchdog.",
        epilog="Exit codes: 0 ok, 2 usage, 3 failed, 4 empty, 5 stalled, 6 capped, "
        "7 limited, 8 auth, 9 missing.",
    )
    parser.add_argument("--model", default="sol", help="sol, astra, luna, or a full model id (default: sol)")
    parser.add_argument("--effort", default="high", choices=EFFORTS, help="reasoning effort (default: high)")
    parser.add_argument("--prompt-file", action="append", help="prompt text; repeatable, joined in order; stdin when omitted")
    parser.add_argument("--changes-since", metavar="REF", help="append the changes since REF (HEAD = uncommitted only)")
    parser.add_argument("--cap-min", type=float, help="hard cap in minutes (default: 25 for astra, 20 otherwise)")
    parser.add_argument("--stall-min", type=float, default=DEFAULT_STALL_MINUTES, help="kill after this many minutes without new output (default: 10)")
    parser.add_argument("--out", help="also write the final message to this path")
    parser.add_argument("--keep", action="store_true", help="keep the run directory even on success")
    parser.add_argument("--bundle-only", action="store_true", help="print the --changes-since bundle for another reviewer and exit; no codex run")
    parser.add_argument("--codex-bin", default="codex", help=argparse.SUPPRESS)
    parser.add_argument("--kill-grace", type=float, default=KILL_GRACE_SECONDS, help=argparse.SUPPRESS)
    parser.add_argument("--no-waitid", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list) -> int:
    global CAN_PEEK
    args = parse_args(argv)
    if args.no_waitid:
        CAN_PEEK = False
    try:
        model = resolve_model(args.model)
    except ValueError as err:
        say(str(err))
        return EXIT["usage"]
    cap_min = args.cap_min if args.cap_min is not None else CAP_MINUTES.get(model, DEFAULT_CAP_MINUTES)
    if not all(math.isfinite(v) and v > 0 for v in (cap_min, args.stall_min)):
        say("--cap-min and --stall-min must be positive numbers")
        return EXIT["usage"]
    if not (math.isfinite(args.kill_grace) and args.kill_grace >= 0):
        say("--kill-grace must be a non-negative number")
        return EXIT["usage"]

    if args.bundle_only:
        return print_bundle(args.changes_since)

    try:
        prompt = read_prompt(args)
    except (OSError, ValueError) as err:  # ValueError covers undecodable text
        say(f"cannot read the prompt: {err}")
        return EXIT["usage"]
    if not prompt.strip():
        say("empty prompt: pass --prompt-file or pipe the prompt on stdin")
        return EXIT["usage"]

    codex = shutil.which(args.codex_bin)
    if codex is None:
        say(f"codex binary not found ({args.codex_bin}); install it or run /codex-cli:setup")
        return EXIT["missing"]

    run_dir = Path(tempfile.mkdtemp(prefix="codex-run-"))
    if args.changes_since:
        try:
            prompt += build_changes(args.changes_since, run_dir)
        except subprocess.CalledProcessError as err:
            say(f"could not collect changes since {args.changes_since}: {(err.stderr or '').strip()}")
            shutil.rmtree(run_dir, ignore_errors=True)
            return EXIT["usage"]

    prompt_path = run_dir / "prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    last = run_dir / "last.txt"
    stdout_log = run_dir / "stdout.log"
    stderr_log = run_dir / "stderr.log"

    say(f"model={model} effort={args.effort} cap={cap_min:g}m stall={args.stall_min:g}m")
    # --json: progress and errors arrive as structured events on stdout, and
    # the prompt is not echoed into any log we classify.
    cmd = [
        codex, "exec", "--json", "-s", "read-only", "-m", model,
        "-c", f'model_reasoning_effort="{args.effort}"',
        "-o", str(last), "-",
    ]

    # Codex runs in its own session so a kill reaches the shells it spawns.
    # The flip side is that nothing kills it when this runner dies, so every
    # way out below goes through kill_group. Signals only record themselves;
    # the loop acts on them, so a signal can never land between starting
    # codex and knowing its pid, or interrupt the kill itself.
    signals: list = []

    def on_signal(signum, _frame):
        signals.append(signum)

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, on_signal)
    # An inherited SIGCHLD=SIG_IGN makes the OS reap codex on its own, which
    # breaks both the exit status and the unreaped-group guarantee above.
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    if signals:
        shutil.rmtree(run_dir, ignore_errors=True)
        return 128 + signals[0]

    start = time.monotonic()
    proc = None
    try:
        with prompt_path.open("rb") as stdin, stdout_log.open("wb") as out, stderr_log.open("wb") as err:
            proc = subprocess.Popen(cmd, stdin=stdin, stdout=out, stderr=err, start_new_session=True)
        say(f"run-dir={run_dir} pid={proc.pid}")
        state = supervise(proc, (stdout_log, stderr_log), cap_min * 60, args.stall_min * 60, signals)
    finally:
        if proc is not None:
            kill_group(proc, args.kill_grace)
        # Codex is gone; from here a signal may simply end the runner, so a
        # late one can never be swallowed into a successful exit.
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(sig, signal.SIG_DFL)

    # A signal that landed while codex was finishing or being killed still wins.
    if signals:
        say(f"interrupted by signal {signals[0]}; codex killed. Logs kept in {run_dir}")
        return 128 + signals[0]
    if state == "exited":
        if proc.returncode != 0:
            outcome = classify_failure(stdout_log, stderr_log)
        elif not last.exists() or not last.read_text(errors="replace").strip():
            outcome = "empty"
        else:
            outcome = "ok"
    else:
        outcome = state

    say(f"outcome={outcome} exit={proc.returncode} elapsed={(time.monotonic() - start) / 60:.1f}m")
    if outcome != "ok":
        detail = error_events(stdout_log)
        if stderr_log.exists():
            detail += stderr_log.read_text(errors="replace").splitlines()[-40:]
        if detail:
            say("codex said:")
            print("\n".join(detail), file=sys.stderr)
        say(f"no review: treat this as a failed route, not as 'no findings'. Logs kept in {run_dir}")
        return EXIT[outcome]

    message = last.read_text(errors="replace")
    # Two independent destinations: neither failure may cost the other, and
    # the run directory (with last.txt) is kept if stdout could not take it.
    delivered = True
    try:
        sys.stdout.write(message if message.endswith("\n") else message + "\n")
        sys.stdout.flush()
    except OSError as err:
        delivered = False
        say(f"could not write the review to stdout ({err}); it is in {last}")
        # Point stdout at /dev/null, or the interpreter's exit-time flush hits
        # the same broken pipe and turns a finished review into exit 120.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except OSError:
            pass
    if args.out:
        try:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(message, encoding="utf-8")
        except OSError as err:
            say(f"--out could not be written ({err}); the review is on stdout")
    if delivered and not args.keep:
        shutil.rmtree(run_dir, ignore_errors=True)
    return EXIT["ok"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
