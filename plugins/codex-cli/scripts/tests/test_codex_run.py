"""Black-box tests for codex-run.py against a fake codex binary.

Run: python3 -m unittest discover -s plugins/codex-cli/scripts/tests -v
"""

import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE.parent / "codex-run.py"
FAKE = HERE / "fake_codex.py"

HAS_WAITID = hasattr(os, "waitid") and hasattr(os, "WNOWAIT")

# Minutes, as the runner takes them. Small enough that the whole suite runs in seconds.
FAST_STALL = "0.02"  # 1.2 s


def pid_alive(pid):
    """Running, and not merely a zombie waiting to be reaped."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout
    return bool(state.strip()) and not state.strip().startswith("Z")


def wait_dead(pid, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not pid_alive(pid):
            return True
        time.sleep(0.05)
    return False


class RunnerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="codex-run-test-"))
        self.record = self.tmp / "record.json"
        self.pidfile = self.tmp / "pid"

    def env(self, mode, **extra):
        env = dict(os.environ)
        env.update(
            FAKE_CODEX_MODE=mode,
            FAKE_CODEX_RECORD=str(self.record),
            FAKE_CODEX_PIDFILE=str(self.pidfile),
        )
        env.update(extra)
        return env

    def run_runner(self, mode, *args, prompt="Review this.", cwd=None, **extra):
        return subprocess.run(
            [sys.executable, str(RUNNER), "--codex-bin", str(FAKE), *args],
            input=prompt,
            capture_output=True,
            text=True,
            env=self.env(mode, **extra),
            cwd=cwd,
            timeout=60,
        )

    def recorded(self):
        return json.loads(self.record.read_text())

    def run_dir(self, stderr):
        match = re.search(r"run-dir=(\S+)", stderr)
        self.assertIsNotNone(match, stderr)
        return Path(match.group(1))


class InvocationTests(RunnerCase):
    def test_ok_prints_final_message_and_pins_read_only_model_and_effort(self):
        result = self.run_runner("ok")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no issue — looks right", result.stdout)
        argv = self.recorded()["argv"]
        self.assertEqual(argv[:6], ["exec", "--json", "-s", "read-only", "-m", "gpt-6-sol"])
        self.assertIn('model_reasoning_effort="high"', argv)
        self.assertEqual(argv[-1], "-")
        self.assertEqual(self.recorded()["prompt"], "Review this.")
        self.assertFalse(self.run_dir(result.stderr).exists(), "run dir should be removed on success")

    def test_astra_alias_gets_the_25_minute_cap(self):
        result = self.run_runner("ok", "--model", "astra", "--effort", "xhigh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("model=gpt-6-astra effort=xhigh cap=25m", result.stderr)
        self.assertIn("gpt-6-astra", self.recorded()["argv"])

    def test_full_model_ids_pass_through(self):
        result = self.run_runner("ok", "--model", "gpt-5.6-sol")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cap=20m", result.stderr)
        self.assertIn("gpt-5.6-sol", self.recorded()["argv"])

    def test_prompt_file_and_out(self):
        prompt = self.tmp / "prompt.txt"
        prompt.write_text("From a file.")
        out = self.tmp / "out.txt"
        result = self.run_runner("ok", "--prompt-file", str(prompt), "--out", str(out), prompt="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded()["prompt"], "From a file.")
        self.assertIn("looks right", out.read_text())

    def test_prompt_files_join_in_order(self):
        brief, plan = self.tmp / "brief.md", self.tmp / "plan.md"
        brief.write_text("Review the plan that follows.\n")
        plan.write_text("# Plan\nDo the thing.\n")
        result = self.run_runner("ok", "--prompt-file", str(brief), "--prompt-file", str(plan), prompt="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded()["prompt"], "Review the plan that follows.\n\n\n# Plan\nDo the thing.\n")

    def test_usage_errors(self):
        for args in (
            ["--model", "sol; rm -rf /"],
            ["--effort", "extreme"],
            ["--cap-min", "0"],
            ["--cap-min", "nan"],
            ["--stall-min", "inf"],
            ["--prompt-file", str(self.tmp / "missing.txt")],
            ["--kill-grace", "inf"],
        ):
            with self.subTest(args=args):
                self.assertEqual(self.run_runner("ok", *args).returncode, 2)
        self.assertEqual(self.run_runner("ok", prompt="   ").returncode, 2)
        undecodable = self.tmp / "latin1.txt"
        undecodable.write_bytes(b"caf\xe9 review")
        self.assertEqual(self.run_runner("ok", "--prompt-file", str(undecodable), prompt="").returncode, 2)

    @unittest.skipUnless(shutil.which("uv"), "uv not installed")
    def test_runs_through_uv_run_script(self):
        result = subprocess.run(
            ["uv", "run", "--script", str(RUNNER), "--codex-bin", str(FAKE)],
            input="Review this.", capture_output=True, text=True,
            env=self.env("ok"), timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("looks right", result.stdout)

    def test_model_id_with_a_trailing_newline_is_rejected(self):
        self.assertEqual(self.run_runner("ok", "--model", "gpt-6-sol\n").returncode, 2)

    def test_undecodable_stdin_is_a_usage_error(self):
        # UTF-8 mode reads stdin with surrogateescape, so bad bytes get through
        # a text read and only blow up later; a strict locale would mask that.
        env = self.env("ok", PYTHONUTF8="1")
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--codex-bin", str(FAKE)],
            input=b"caf\xe9 review", capture_output=True, env=env, timeout=30,
        )
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_out_creates_missing_directories(self):
        out = self.tmp / "plan" / "reviews" / "u1.md"
        result = self.run_runner("ok", "--out", str(out))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("looks right", out.read_text())

    def test_unwritable_out_still_delivers_the_review(self):
        blocker = self.tmp / "a-file"
        blocker.write_text("")
        result = self.run_runner("ok", "--out", str(blocker / "review.md"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("looks right", result.stdout)
        self.assertIn("--out could not be written", result.stderr)

    def test_closed_stdout_still_writes_out_and_keeps_the_review(self):
        out = self.tmp / "review.md"
        proc = subprocess.Popen(
            [sys.executable, str(RUNNER), "--codex-bin", str(FAKE), "--out", str(out)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env("ok"),
        )
        proc.stdout.close()  # the reader goes away before the review arrives
        proc.stdin.write(b"Review this.")
        proc.stdin.close()
        stderr = proc.stderr.read().decode()
        proc.stderr.close()
        self.assertEqual(proc.wait(timeout=60), 0, stderr)
        self.assertIn("looks right", out.read_text())
        self.assertIn("could not write the review to stdout", stderr)

    def test_inherited_ignored_sigchld_does_not_hide_the_exit_status(self):
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--codex-bin", str(FAKE)],
            input="Review this.", capture_output=True, text=True, env=self.env("crash"), timeout=60,
            preexec_fn=lambda: signal.signal(signal.SIGCHLD, signal.SIG_IGN),
        )
        self.assertEqual(result.returncode, 3, result.stderr)

    def test_missing_binary(self):
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--codex-bin", str(self.tmp / "nope")],
            input="x", capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 9)


class OutcomeTests(RunnerCase):
    def assert_no_review(self, result, code):
        self.assertEqual(result.returncode, code, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("not as 'no findings'", result.stderr)
        self.assertTrue(self.run_dir(result.stderr).exists(), "run dir should be kept on failure")

    def test_empty_final_message_is_a_failure(self):
        self.assert_no_review(self.run_runner("empty"), 4)

    def test_usage_limit_is_limited(self):
        self.assert_no_review(self.run_runner("limited"), 7)

    def test_unauthorized_is_auth(self):
        self.assert_no_review(self.run_runner("auth"), 8)

    def test_whitespace_only_final_message_is_empty(self):
        self.assert_no_review(self.run_runner("blank"), 4)

    def test_each_failure_event_classifies_on_its_own(self):
        for which in ("error", "turn.failed"):
            with self.subTest(which=which):
                self.assert_no_review(self.run_runner("limited", FAKE_CODEX_EVENTS=which), 7)
                self.assert_no_review(self.run_runner("auth", FAKE_CODEX_EVENTS=which), 8)

    def test_auth_error_before_a_session_starts(self):
        self.assert_no_review(self.run_runner("auth_before_session"), 8)

    def test_other_failure_is_failed(self):
        self.assert_no_review(self.run_runner("crash"), 3)

    def test_limit_words_in_prompt_or_tool_output_do_not_misclassify(self):
        # The crash mode's tool output mentions 429 / usage limit / 401; only
        # codex's own error events count.
        prompt = "Check the usage limit handling.\nMake sure a 429 is retried.\nAlso 401 Unauthorized paths."
        result = self.run_runner("crash", prompt=prompt)
        self.assert_no_review(result, 3)
        self.assertIn("thread panicked", result.stderr)


class SupervisionTests(RunnerCase):
    def test_flat_log_is_killed_as_stalled(self):
        start = time.monotonic()
        result = self.run_runner("stall", "--stall-min", FAST_STALL)
        self.assert_killed(result, 5)
        self.assertLess(time.monotonic() - start, 20)

    def test_steady_progress_outlives_the_stall_window(self):
        # 10 ticks x 0.3 s = 3 s of work, well past the 1.2 s stall window.
        result = self.run_runner("progress", "--stall-min", FAST_STALL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("steady progress", result.stdout)
        self.assertIn("since the last check", result.stderr)

    def test_stderr_only_progress_also_counts(self):
        result = self.run_runner("progress", "--stall-min", FAST_STALL, FAKE_CODEX_PROGRESS_STREAM="stderr")
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(HAS_WAITID, "needs os.waitid to sweep after a natural exit")
    def test_natural_exit_sweeps_leftover_descendants(self):
        childfile = self.tmp / "child"
        result = self.run_runner("orphan", FAKE_CODEX_CHILDFILE=str(childfile))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(wait_dead(int(childfile.read_text())), "descendant survived a natural exit")

    def test_without_waitid_a_kill_still_reaches_grandchildren(self):
        childfile = self.tmp / "child"
        result = self.run_runner(
            "grandchild", "--no-waitid", "--kill-grace", "0.5", "--stall-min", FAST_STALL,
            FAKE_CODEX_CHILDFILE=str(childfile),
        )
        self.assert_killed(result, 5)
        self.assertTrue(wait_dead(int(childfile.read_text())), "grandchild survived the fallback kill")

    def test_without_waitid_a_natural_exit_leaves_the_group_alone(self):
        # Codex was reaped by poll(), so its group id may already belong to
        # someone else: the documented trade-off is to skip the sweep.
        childfile = self.tmp / "child"
        result = self.run_runner("orphan", "--no-waitid", FAKE_CODEX_CHILDFILE=str(childfile))
        child = int(childfile.read_text())
        self.addCleanup(lambda: pid_alive(child) and os.kill(child, signal.SIGKILL))  # the one leftover
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(pid_alive(child), "the fallback swept a group it could not prove was codex's")

    def test_hard_cap_kills_even_while_progressing(self):
        result = self.run_runner("chatty", "--cap-min", "0.03", "--stall-min", FAST_STALL)
        self.assert_killed(result, 6)

    def test_kill_reaches_grandchildren(self):
        childfile = self.tmp / "child"
        result = self.run_runner(
            "grandchild", "--stall-min", FAST_STALL, FAKE_CODEX_CHILDFILE=str(childfile)
        )
        self.assert_killed(result, 5)
        self.assertTrue(wait_dead(int(childfile.read_text())), "grandchild survived the kill")

    def start_runner(self, mode, *args):
        if "--stall-min" not in args:
            args = ("--stall-min", "5", *args)
        proc = subprocess.Popen(
            [sys.executable, str(RUNNER), "--codex-bin", str(FAKE), *args],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=self.env(mode),
        )
        self.addCleanup(proc.stdout.close)
        self.addCleanup(proc.stderr.close)
        proc.stdin.write("Review this.")
        proc.stdin.close()
        deadline = time.monotonic() + 10
        while not (self.pidfile.exists() and self.pidfile.read_text()):
            self.assertLess(time.monotonic(), deadline, "fake codex never started")
            time.sleep(0.05)
        return proc, int(self.pidfile.read_text())

    def test_sigterm_to_the_runner_kills_codex(self):
        proc, codex_pid = self.start_runner("stall")
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=30)
        self.assertEqual(proc.returncode, 128 + signal.SIGTERM)
        self.assertTrue(wait_dead(codex_pid), "codex survived the runner being killed")

    def test_second_signal_during_the_kill_still_cleans_up(self):
        # Codex ignores SIGTERM, so the runner sits in its kill grace period
        # when the second signal lands; it must still finish the kill.
        proc, codex_pid = self.start_runner("stubborn", "--kill-grace", "2")
        proc.send_signal(signal.SIGTERM)
        time.sleep(0.5)
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=30)
        self.assertEqual(proc.returncode, 128 + signal.SIGTERM, proc.stderr.read())
        self.assertTrue(wait_dead(codex_pid), "stubborn codex survived")

    def test_signal_during_a_cap_kill_still_reports_the_interruption(self):
        # Stall at ~1.2 s starts the kill; codex ignores SIGTERM, so the
        # runner sits in its 3 s grace period when our signal lands.
        proc, codex_pid = self.start_runner("stubborn", "--stall-min", FAST_STALL, "--kill-grace", "3")
        time.sleep(2.5)
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=30)
        self.assertEqual(proc.returncode, 128 + signal.SIGTERM, proc.stderr.read())
        self.assertTrue(wait_dead(codex_pid), "stubborn codex survived")

    def assert_killed(self, result, code):
        self.assertEqual(result.returncode, code, result.stderr)
        self.assertTrue(wait_dead(int(self.pidfile.read_text())), "fake codex survived the kill")


class SuperviseOrderTests(unittest.TestCase):
    def test_an_exit_during_the_last_sleep_is_not_reported_as_capped(self):
        spec = importlib.util.spec_from_file_location("codex_run", RUNNER)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        states = iter([False, True])  # codex finishes while the loop sleeps
        runner.exited = lambda proc: next(states)
        # A fake clock that only moves when the loop sleeps: deterministic on
        # any runner, however slow. The sleep carries it past the cap.
        clock = [0.0]
        runner.time = types.SimpleNamespace(
            monotonic=lambda: clock[0],
            sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
        )
        state = runner.supervise(object(), (), cap_s=0.05, stall_s=100, signals=[])
        self.assertEqual(state, "exited")


class ChangesTests(RunnerCase):
    # A trailing space in the checkout's path must survive (`strip()` would
    # silently point git at a different directory).
    REPO_DIR = "repo "

    def setUp(self):
        super().setUp()
        self.repo = self.tmp / self.REPO_DIR
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        (self.repo / "app.py").write_text("x = 1\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, capture_output=True, text=True
        ).stdout

    def test_head_covers_unstaged_staged_and_untracked(self):
        (self.repo / "app.py").write_text("x = 2\n")
        (self.repo / "new.py").write_text("print('hello new file')\n")
        (self.repo / "staged.py").write_text("y = 3\n")
        self.git("add", "staged.py")
        result = self.run_runner("ok", "--changes-since", "HEAD", cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        prompt = self.recorded()["prompt"]
        self.assertTrue(prompt.startswith("Review this."))
        self.assertIn("=== BEGIN CHANGES ===", prompt)
        self.assertIn("+x = 2", prompt)
        self.assertIn("+y = 3", prompt)
        self.assertIn("===== new.py =====\nprint('hello new file')", prompt)
        # Collecting changes must not touch the index.
        self.assertEqual(self.git("diff", "--cached", "--name-only").split(), ["staged.py"])

    def test_batch_base_includes_commits_since(self):
        (self.repo / "app.py").write_text("x = 3\n")
        self.git("commit", "-qam", "unit two")
        result = self.run_runner("ok", "--changes-since", self.base, cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        prompt = self.recorded()["prompt"]
        self.assertIn("unit two", prompt)
        self.assertIn("+x = 3", prompt)

    def test_large_changes_are_handed_over_as_a_file(self):
        (self.repo / "big.py").write_text("".join(f"line_{i} = {i}\n" for i in range(1200)))
        result = self.run_runner("ok", "--changes-since", "HEAD", "--keep", cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        prompt = self.recorded()["prompt"]
        self.assertNotIn("line_1100", prompt)
        self.assertIn("Do NOT run `git diff`", prompt)
        diff_file = self.run_dir(result.stderr) / "changes.diff"
        self.assertIn(str(diff_file), prompt)
        self.assertIn("line_1100 = 1100", diff_file.read_text())

    def test_large_changes_come_with_a_line_index(self):
        (self.repo / "app.py").write_text("x = 42\n")
        (self.repo / "big.py").write_text("".join(f"line_{i} = {i}\n" for i in range(1200)))
        result = self.run_runner("ok", "--changes-since", "HEAD", "--keep", cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        prompt = self.recorded()["prompt"]
        lines = (self.run_dir(result.stderr) / "changes.diff").read_text().split("\n")
        for name, first, last in (
            ("app.py", "diff --git a/app.py b/app.py", "+x = 42"),
            ("big.py", "===== big.py =====", "line_1199 = 1199"),
        ):
            start, end = map(int, re.search(rf"  {name}: lines (\d+)-(\d+)", prompt).groups())
            self.assertEqual(lines[start - 1], first, name)
            self.assertEqual(lines[end - 1], last, name)
        self.assertIn("read that file in slices".lower(), prompt.lower())

    def test_index_ignores_header_lookalikes_inside_files(self):
        # An untracked file whose own lines look like bundle headers.
        tricky = "".join(f"row_{i} = {i}\n" for i in range(600))
        tricky += "===== not_a_file.py =====\ndiff --git a/fake b/fake\n"
        tricky += "".join(f"tail_{i} = {i}\n" for i in range(600))
        (self.repo / "tricky.md").write_text(tricky)
        result = self.run_runner("ok", "--changes-since", "HEAD", "--keep", cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        prompt = self.recorded()["prompt"]
        self.assertNotIn("not_a_file.py:", prompt)
        self.assertNotIn("fake:", prompt)
        lines = (self.run_dir(result.stderr) / "changes.diff").read_text().split("\n")
        start, end = map(int, re.search(r"  tricky.md: lines (\d+)-(\d+)", prompt).groups())
        section = "\n".join(lines[start - 1:end])
        self.assertIn("row_0 = 0", section)
        self.assertIn("tail_599 = 599", section)

    def test_runs_from_a_subdirectory(self):
        (self.repo / "sub").mkdir()
        (self.repo / "sub" / "keep.txt").write_text("tracked\n")
        self.git("add", ".")
        self.git("commit", "-qm", "sub")
        (self.repo / "root_new.py").write_text("print('at the root')\n")
        result = self.run_runner("ok", "--changes-since", "HEAD", cwd=self.repo / "sub")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("===== root_new.py =====\nprint('at the root')", self.recorded()["prompt"])

    def test_does_not_write_the_index(self):
        # A stat-dirty file makes a plain `git status` refresh and rewrite the index.
        index = self.repo / ".git" / "index"
        future = time.time() + 120
        os.utime(self.repo / "app.py", (future, future))
        before = index.read_bytes()
        result = self.run_runner("ok", "--changes-since", "HEAD", cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(index.read_bytes(), before, "collecting changes rewrote the index")

    def test_untracked_symlinks_are_named_not_followed(self):
        secret = self.tmp / "outside.txt"
        secret.write_text("contents outside the repo\n")
        os.symlink(secret, self.repo / "link.txt")
        result = self.run_runner("ok", "--changes-since", "HEAD", cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        prompt = self.recorded()["prompt"]
        self.assertIn(f"===== link.txt (symlink -> {secret}) =====", prompt)
        self.assertNotIn("contents outside the repo", prompt)

    def test_one_huge_line_is_handed_over_as_a_file(self):
        (self.repo / "blob.json").write_text("[" + "1," * 80_000 + "1]\n")
        result = self.run_runner("ok", "--changes-since", "HEAD", "--keep", cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Do NOT run `git diff`", self.recorded()["prompt"])

    def test_bundle_only_prints_the_bundle_without_running_codex(self):
        (self.repo / "app.py").write_text("x = 5\n")
        result = self.run_runner("crash", "--changes-since", "HEAD", "--bundle-only", cwd=self.repo, prompt="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("=== BEGIN CHANGES ==="))
        self.assertIn("+x = 5", result.stdout)
        self.assertFalse(self.record.exists(), "codex must not run")

    def test_bundle_only_hands_large_changes_over_as_a_file(self):
        (self.repo / "big.py").write_text("".join(f"line_{i} = {i}\n" for i in range(1200)))
        result = self.run_runner("ok", "--changes-since", "HEAD", "--bundle-only", cwd=self.repo, prompt="")
        self.assertEqual(result.returncode, 0, result.stderr)
        path = re.search(r"in a file: (\S+)", result.stdout).group(1)
        self.assertIn("line_1100 = 1100", Path(path).read_text())
        self.assertEqual(self.run_runner("ok", "--bundle-only").returncode, 2)

    def test_oversized_untracked_files_tell_the_reviewer_to_read_them(self):
        (self.repo / "generated.py").write_text("x = 1\n" * 50_000)
        (self.repo / "logo.png").write_bytes(b"\x89PNG\0\0binary")
        result = self.run_runner("ok", "--changes-since", "HEAD", "--bundle-only", cwd=self.repo, prompt="")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("generated.py", "logo.png"):
            self.assertIn(f"===== {name} (not inlined:", result.stdout)
        self.assertIn("read it from the worktree before giving a verdict", result.stdout)
        self.assertNotIn("x = 1\nx = 1", result.stdout)

    def test_untracked_trailing_blank_lines_survive(self):
        (self.repo / "golden.txt").write_text("alpha\n\n\n")
        result = self.run_runner("ok", "--changes-since", "HEAD", "--bundle-only", cwd=self.repo, prompt="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("===== golden.txt =====\nalpha\n\n\n", result.stdout)

    def test_non_utf8_files_do_not_crash_the_bundle(self):
        (self.repo / "latin1.txt").write_bytes(b"caf\xe9\n")
        self.git("add", "latin1.txt")
        self.git("commit", "-qm", "latin1")
        (self.repo / "latin1.txt").write_bytes(b"caf\xe9 au lait\n")
        result = self.run_runner("ok", "--changes-since", "HEAD", "--bundle-only", cwd=self.repo, prompt="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("au lait", result.stdout)

    def test_index_names_survive_spaces_renames_and_deletions(self):
        tricky = self.repo / "dir b" / "name.py"
        tricky.parent.mkdir()
        tricky.write_text("a = 1\n")
        # A mode-only change has no ---/+++ lines: its name comes from the header alone.
        script = self.repo / "dir b" / "run.sh"
        script.write_text("echo hi\n")
        (self.repo / "old.py").write_text("\n".join(f"v{i} = {i}" for i in range(50)) + "\n")
        (self.repo / "gone.py").write_text("g = 1\n")
        self.git("add", ".")
        self.git("commit", "-qm", "names")
        tricky.write_text("a = 2\n")
        script.chmod(0o755)
        self.git("mv", "old.py", "new.py")
        self.git("rm", "-q", "gone.py")
        (self.repo / "filler.py").write_text("".join(f"f_{i} = {i}\n" for i in range(1000)))
        result = self.run_runner("ok", "--changes-since", "HEAD", "--keep", cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        index = dict(re.findall(r"^  (.+): lines (\d+-\d+)$", self.recorded()["prompt"], re.M))
        self.assertIn("dir b/name.py", index)
        self.assertIn("dir b/run.sh", index)
        self.assertIn("new.py", index)
        self.assertIn("gone.py", index)
        self.assertNotIn("name.py", index)

    def test_quoted_paths_keep_their_real_names_in_the_index(self):
        odd = self.repo / "tab\there.py"
        odd.write_text("t = 1\n")
        self.git("add", ".")
        self.git("commit", "-qm", "odd name")
        odd.write_text("t = 2\n")
        (self.repo / "filler.py").write_text("".join(f"f_{i} = {i}\n" for i in range(1000)))
        result = self.run_runner("ok", "--changes-since", "HEAD", "--keep", cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("  tab\there.py: lines ", self.recorded()["prompt"])

    def test_untracked_files_with_non_utf8_names_are_bundled(self):
        (self.repo / os.fsdecode(b"caf\xe9.py")).write_text("print('latin-1 name')\n")
        result = self.run_runner("ok", "--changes-since", "HEAD", "--bundle-only", cwd=self.repo, prompt="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("print('latin-1 name')", result.stdout)

    def test_textconv_filters_apply(self):
        (self.repo / ".gitattributes").write_text("*.up diff=upper\n")
        self.git("config", "diff.upper.textconv", "tr a-z A-Z <")
        (self.repo / "note.up").write_text("abc\n")
        self.git("add", ".")
        self.git("commit", "-qm", "textconv")
        (self.repo / "note.up").write_text("xyz\n")
        result = self.run_runner("ok", "--changes-since", "HEAD", cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("+XYZ", self.recorded()["prompt"])

    def test_unknown_ref_is_a_usage_error(self):
        result = self.run_runner("ok", "--changes-since", "no-such-ref", cwd=self.repo)
        self.assertEqual(result.returncode, 2, result.stderr)


if __name__ == "__main__":
    unittest.main()
