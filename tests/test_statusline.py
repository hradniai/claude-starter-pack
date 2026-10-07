"""Tests for the status line script (kernel/scripts/statusline.py).

Run from the repository root: python3 -m unittest discover -s tests -p "test_statusline.py" -v
Hermetic: every run points HOME and CLAUDE_CONFIG_DIR at a temporary directory, so the metrics cache
never lands in the real ~/.claude, and transcripts are small fixtures written by the tests.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "kernel" / "scripts" / "statusline.py"
ANSI = re.compile(r"\033\[[0-9;]*m")
FOOTER_PADDING = 4  # Claude Code keeps two columns of padding on each side of the status line
WIDTHS = (40, 50, 60, 80, 120, 200)
SESSION = "sess-1234"
T0 = 1_790_000_000  # transcript times are fixed; only their differences matter


def load_module():
    spec = importlib.util.spec_from_file_location("statusline_under_test", str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def width_of(line):
    """Terminal columns of a line, measured independently of the script: wide characters take two."""
    total = 0
    for character in ANSI.sub("", line):
        if unicodedata.combining(character) or unicodedata.category(character) == "Cf":
            continue
        total += 2 if unicodedata.east_asian_width(character) in ("W", "F") else 1
    return total


def iso(offset):
    return datetime.fromtimestamp(T0 + offset, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def assistant(offset, message_id, fresh, created, read, output, sidechain=False, session=None):
    record = {
        "type": "assistant",
        "timestamp": iso(offset),
        "message": {"id": message_id, "usage": {
            "input_tokens": fresh, "cache_creation_input_tokens": created,
            "cache_read_input_tokens": read, "output_tokens": output,
        }},
    }
    if sidechain:
        record["isSidechain"] = True
    if session:
        record["sessionId"] = session
    return record


def subagent_prompt(offset, session):
    return {"type": "user", "isSidechain": True, "sessionId": session, "timestamp": iso(offset),
            "message": {"content": "task"}}


MAIN_RECORDS = [
    {"type": "user", "timestamp": iso(0), "message": {"role": "user", "content": "first prompt"}},
    assistant(5, "m1", 100, 1000, 0, 50),
    assistant(6, "m1", 100, 1000, 0, 50),  # another record of the same message: counted once
    {"type": "user", "timestamp": iso(10), "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
    assistant(20, "m2", 10, 2000, 1100, 70),  # context 3110, growth 2010
    {"type": "user", "timestamp": iso(60), "message": {"content": [{"type": "text", "text": "second prompt"}]}},
    {"type": "user", "isMeta": True, "timestamp": iso(61), "message": {"content": "injected, not typed"}},
    assistant(70, "m3", 5, 500, 3110, 30),  # context 3615, growth 505
    {"type": "attachment", "timestamp": iso(80)},
]
# 3615 + 1000 (subagent) + 7 (older-layout subagent) in; 150 + 400 + 3 out. The last activity is the
# subagent's at 200 s, so the session ran 200 s and the current run (from the prompt at 60 s) 140 s.
EXPECTED = {
    "turns": 3, "solo_turns": 1, "tokens_in": 4622, "tokens_out": 553, "growth_last": 505,
    "growth_average": 1257, "session_seconds": 200, "run_seconds": 140,
}


def jsonl(records):
    return "".join(json.dumps(record) + "\n" for record in records)


def write_transcripts(folder):
    """A main transcript with subagents in both layouts; returns its path."""
    folder.mkdir(parents=True, exist_ok=True)
    transcript = folder / f"{SESSION}.jsonl"
    # A garbage line is skipped; a trailing line without a newline is still being written.
    transcript.write_text(jsonl(MAIN_RECORDS) + "not json\n" + '{"type": "assistant", "timest', encoding="utf-8")
    subagents = folder / SESSION / "subagents"
    subagents.mkdir(parents=True)
    (subagents / "agent-a1.jsonl").write_text(
        jsonl([subagent_prompt(100, SESSION), assistant(200, "s1", 1000, 0, 0, 400, sidechain=True)]), encoding="utf-8"
    )
    (folder / "agent-old.jsonl").write_text(
        jsonl([subagent_prompt(90, SESSION), assistant(95, "o1", 7, 0, 0, 3, sidechain=True)]), encoding="utf-8"
    )
    (folder / "agent-other.jsonl").write_text(
        jsonl([subagent_prompt(90, "someone-else"), assistant(95, "x1", 999999, 0, 0, 999999, sidechain=True)]),
        encoding="utf-8",
    )
    return transcript


def payload(transcript=None, project_dir="/nonexistent/acme-portal", now=None, full=True):
    now = now or time.time()
    data = {
        "session_id": SESSION,
        "model": {"id": "claude-opus-5-5", "display_name": "Opus 5.5 (1M context)"},
        "effort": {"level": "xhigh"},
        "output_style": {"name": "default"},
        "workspace": {"project_dir": project_dir, "current_dir": project_dir},
        "cost": {"total_cost_usd": 4.18},
        "worktree": {"branch": "feature/login-form"},
        "context_window": {"context_window_size": 1_000_000, "used_percentage": 42.4},
        "rate_limits": {
            # 30 spare seconds so a countdown cannot drop a unit while the test runs.
            "five_hour": {"used_percentage": 63, "resets_at": int(now) + 2 * 3600 + 5 * 60 + 30},
            "seven_day": {"used_percentage": 71, "resets_at": int(now) + 3 * 86400 + 3600 + 30},
        },
    }
    if transcript:
        data["transcript_path"] = str(transcript)
    if full:
        data["output_style"] = {"name": "explanatory"}
        data["agent"] = {"name": "research-analyst"}
        data["worktree"] = {"name": "login-fix", "branch": "feature/login-form"}
    return data


def plain(output):
    return ANSI.sub("", output.decode("utf-8"))


class StatuslineTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.config = self.home / ".claude"
        self.config.mkdir(parents=True)
        self.cache = self.config / "cache" / "statusline"

    def tearDown(self):
        self._tmp.cleanup()

    def environment(self, columns="120", config=None):
        env = dict(os.environ)
        env["HOME"] = str(self.home)
        env["CLAUDE_CONFIG_DIR"] = str(config or self.config)
        env.pop("COLUMNS", None)
        if columns is not None:
            env["COLUMNS"] = columns
        return env

    def run_script(self, stdin, columns="120", config=None):
        if not isinstance(stdin, str):
            stdin = json.dumps(stdin)
        return subprocess.run(
            [sys.executable, str(SCRIPT)], input=stdin.encode("utf-8"), capture_output=True,
            env=self.environment(columns, config), timeout=30,
        )

    def lines(self, stdin, columns="120"):
        result = self.run_script(stdin, columns)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        return plain(result.stdout).split("\n")

    def transcript(self):
        return write_transcripts(self.config / "projects" / "-work-acme-portal")


class ResponsiveLayoutTest(StatuslineTestCase):
    def test_every_width_fits_and_keeps_the_top_values(self):
        data = payload(self.transcript())
        for columns in WIDTHS:
            with self.subTest(columns=columns):
                result = self.run_script(data, str(columns))
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, b"")
                lines = result.stdout.decode("utf-8").split("\n")
                self.assertLessEqual(len(lines), 5)
                for line in lines:
                    self.assertLessEqual(width_of(line), columns - FOOTER_PADDING, ANSI.sub("", line))
                shown = plain(result.stdout)
                self.assertIn("opus 5.5 xh", shown)
                self.assertIn("42%", shown)
                self.assertRegex(shown, r"5h +63% \(2h ?05m\)")
                self.assertRegex(shown, r"7d +71%")
                self.assertIn("acme-portal", shown)
                self.assertIn("feature/login-form", shown)

    def test_wide_terminal_gets_the_two_line_design(self):
        lines = self.lines(payload(self.transcript()), "200")
        self.assertEqual(len(lines), 2, lines)
        self.assertTrue(lines[0].startswith("opus 5.5 xh · explanatory · acme-portal wt:login-fix ⎇ feature/login-form"))
        self.assertIn(" │ $4.18 · 5k↑ 553↓ · 3m (2m)", lines[0])
        self.assertEqual(
            lines[1],
            "▓▓▓▓░░░░░░  42% (1M) · turn   3 ( 1) · ↑ 505/turn (1k) │ 5h  63% (2h 05m) · 7d  71% (3d 1h)",
        )

    def test_narrow_terminal_puts_the_essentials_first(self):
        lines = self.lines(payload(self.transcript()), "40")
        self.assertEqual(lines[0], "opus 5.5 xh · ▓▓▓▓░░░░░░ 42%")
        self.assertRegex(lines[1], r"^5h 63% \(2h05m\) · 7d 71% \(3d1h\)$")

    def test_least_important_segments_go_first_when_five_lines_are_not_enough(self):
        data = payload(self.transcript())
        data["agent"]["name"] = "a-very-long-agent-name-for-testing"
        data["output_style"]["name"] = "another-long-output-style"
        lines = self.lines(data, "40")
        self.assertEqual(len(lines), 5)
        shown = "\n".join(lines)
        self.assertNotIn("another-long-output-style", shown)
        for kept in ("opus 5.5", "42%", "5h 63%", "7d 71%", "acme-portal", "$4.18"):
            self.assertIn(kept, shown)

    def test_missing_or_invalid_columns_fall_back_to_80(self):
        data = payload(self.transcript())
        reference = self.run_script(data, "80").stdout
        for columns in (None, "", "abc", "0", "-3"):
            with self.subTest(columns=columns):
                self.assertEqual(self.run_script(data, columns).stdout, reference)

    def test_tiny_width_does_not_break(self):
        result = self.run_script(payload(self.transcript()), "12")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        lines = result.stdout.decode("utf-8").split("\n")
        self.assertLessEqual(len(lines), 5)
        for line in lines:
            self.assertLessEqual(width_of(line), 10)

    def test_long_names_are_shortened_with_an_ellipsis(self):
        data = payload(full=False)
        data["worktree"] = {"branch": "feature/" + "x" * 60}
        lines = self.lines(data, "40")
        location = next(line for line in lines if "acme-portal" in line)
        self.assertLessEqual(width_of(location), 36)
        self.assertIn("…", location)
        self.assertTrue(location.startswith("acme-portal ⎇ feature/x"))

    def test_wide_characters_count_twice(self):
        data = payload(full=False, project_dir="/nonexistent/" + "项目" * 12)
        for columns in (40, 60):
            with self.subTest(columns=columns):
                result = self.run_script(data, str(columns))
                for line in result.stdout.decode("utf-8").split("\n"):
                    self.assertLessEqual(width_of(line), columns - FOOTER_PADDING)
                self.assertIn("项目", plain(result.stdout))


class FieldsTest(StatuslineTestCase):
    def test_context_colors_follow_thresholds(self):
        for percent, color in ((10, "\033[32m"), (40, "\033[33m"), (60, "\033[38;5;208m"), (85, "\033[31m")):
            with self.subTest(percent=percent):
                data = {"model": {"display_name": "M"}, "context_window": {"used_percentage": percent, "context_window_size": 1000}}
                self.assertIn(f"{color}▓", self.run_script(data).stdout.decode("utf-8"))

    def test_five_hour_colors_follow_thresholds(self):
        for percent, color in ((10, "\033[2m"), (60, "\033[33m"), (85, "\033[31m\033[1m")):
            with self.subTest(percent=percent):
                data = {"rate_limits": {"five_hour": {"used_percentage": percent}}}
                self.assertIn(f"{color}{percent:3d}%", self.run_script(data, "200").stdout.decode("utf-8"))

    def test_seven_day_color_follows_the_pace(self):
        now = time.time()
        half_week_left = int(now) + 302400
        for percent, color in ((40, "\033[2m"), (55, "\033[33m"), (70, "\033[38;5;208m"), (80, "\033[31m\033[1m")):
            with self.subTest(percent=percent):
                data = {"rate_limits": {"seven_day": {"used_percentage": percent, "resets_at": half_week_left}}}
                self.assertIn(f"{color}{percent:3d}%", self.run_script(data, "200").stdout.decode("utf-8"))

    def test_model_names_and_colors(self):
        cases = (
            ({"display_name": "Claude Opus 4.8 (1M context)"}, "opus 4.8", "\033[38;5;33m"),
            ({"display_name": "Opus 5"}, "opus 5", "\033[38;5;45m"),
            ({"display_name": "Sonnet 4.6"}, "sonnet 4.6", "\033[38;5;179m"),
            ({"id": "claude-sonnet-5-1"}, "sonnet 5.1", "\033[38;5;78m"),
            ({"display_name": "Haiku 4.5"}, "haiku 4.5", "\033[38;5;245m"),
            ({"display_name": "Local-Model"}, "local-model", "\033[2m"),
        )
        for model, shown, color in cases:
            with self.subTest(model=model):
                output = self.run_script({"model": model, "effort": {"level": "medium"}}).stdout.decode("utf-8")
                self.assertIn(f"{color}{shown}\033[0m\033[38;5;246m m\033[0m", output)

    def test_default_output_style_is_hidden(self):
        data = {"model": {"display_name": "Opus 5"}, "output_style": {"name": "default"}}
        self.assertEqual(self.lines(data), ["opus 5"])
        data["output_style"]["name"] = "explanatory"
        self.assertEqual(self.lines(data), ["opus 5 · explanatory"])

    def test_account_is_shown_only_for_another_config_folder(self):
        data = {"model": {"display_name": "Opus 5"}}
        other = self.home / ".claude-work"
        other.mkdir()
        self.assertEqual(plain(self.run_script(data, config=other).stdout), "◆ work · opus 5")
        self.assertEqual(plain(self.run_script(data).stdout), "opus 5")

    def test_iso_reset_time(self):
        data = {"rate_limits": {"five_hour": {"used_percentage": 5, "resets_at": "2999-01-01T00:00:00Z"}}}
        self.assertRegex(plain(self.run_script(data).stdout), r"5h +5% \(\d+d \d+h\)")

    def test_control_characters_in_names_are_removed(self):
        data = {"model": {"display_name": "Opus 5"}, "agent": {"name": "evil\033[31m\nname"}}
        output = self.run_script(data).stdout.decode("utf-8")
        self.assertNotIn("\n", output)
        self.assertIn("▶ evil[31mname", plain(self.run_script(data).stdout))

    @unittest.skipUnless(shutil.which("git"), "git is required for the branch test")
    def test_branch_comes_from_git(self):
        repository = self.root / "repo"
        subprocess.run(["git", "init", "-q", str(repository)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repository), "symbolic-ref", "HEAD", "refs/heads/from-git"], check=True, capture_output=True)
        self.assertIn("repo ⎇ from-git", plain(self.run_script(payload(project_dir=str(repository), full=False)).stdout))

    def test_branch_falls_back_to_the_worktree_field(self):
        not_a_repository = self.root / "plain-folder"
        not_a_repository.mkdir()
        shown = plain(self.run_script(payload(project_dir=str(not_a_repository), full=False)).stdout)
        self.assertIn("plain-folder ⎇ feature/login-form", shown)

    @unittest.skipUnless(hasattr(os, "posix_spawnp") and shutil.which("sleep"), "POSIX only")
    def test_a_hanging_command_is_stopped(self):
        module = load_module()
        module.GIT_TIMEOUT_SECONDS = 0.2
        start = time.monotonic()
        self.assertIsNone(module.run_quietly(["sleep", "5"]))
        self.assertLess(time.monotonic() - start, 2)
        self.assertIsNone(module.run_quietly(["no-such-command-for-the-status-line-test"]))
        self.assertEqual(module.run_quietly([sys.executable, "-c", "print('ok')"]).strip(), b"ok")
        self.assertIsNone(module.run_quietly([sys.executable, "-c", "raise SystemExit(3)"]))

    @unittest.skipUnless(shutil.which("sleep"), "needs a sleep command")
    def test_without_posix_spawn_subprocess_does_the_same(self):
        """The path Windows takes, exercised here by hiding os.posix_spawnp for the length of the test."""
        module = load_module()
        module.GIT_TIMEOUT_SECONDS = 0.2
        spawn = getattr(os, "posix_spawnp", None)
        if spawn is not None:
            del os.posix_spawnp
            self.addCleanup(setattr, os, "posix_spawnp", spawn)
        self.assertIsNone(module.run_quietly(["sleep", "5"]))
        self.assertIsNone(module.run_quietly(["no-such-command-for-the-status-line-test"]))
        self.assertEqual(module.run_quietly([sys.executable, "-c", "print('ok')"]).strip(), b"ok")
        self.assertIsNone(module.run_quietly([sys.executable, "-c", "raise SystemExit(3)"]))


class RobustnessTest(StatuslineTestCase):
    def test_empty_object(self):
        result = self.run_script("{}")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(result.stdout, b"")

    def test_garbage_input(self):
        for stdin in ("not json at all", "[1, 2, 3]", "", '{"model": "just a string"}', "\x00\xff", "null"):
            with self.subTest(stdin=stdin):
                result = self.run_script(stdin)
                self.assertEqual(result.returncode, 0)
                self.assertNotIn(b"Traceback", result.stderr)

    def test_bad_input_is_reported_on_stderr(self):
        result = self.run_script("not json at all")
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"statusline: reading the status line JSON: JSONDecodeError", result.stderr)

    def test_wrong_types_degrade(self):
        data = {
            "model": {"display_name": ["x"]},
            "cost": {"total_cost_usd": "abc"},
            "context_window": {"used_percentage": "n/a", "context_window_size": {}},
            "rate_limits": {"five_hour": {"used_percentage": 50, "resets_at": "not a time"}, "seven_day": 7},
            "workspace": {"project_dir": 42},
            "transcript_path": {"not": "a path"},
            "session_id": 5,
        }
        result = self.run_script(data)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertIn("5h  50%", plain(result.stdout))

    def test_render_failure_degrades_and_reports_on_stderr(self):
        program = (
            "import importlib.util, sys\n"
            f"spec = importlib.util.spec_from_file_location('statusline', {str(SCRIPT)!r})\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "def boom(*args):\n"
            "    raise RuntimeError('boom')\n"
            "module.render = boom\n"
            "module.main()\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", program], input=json.dumps(payload()).encode("utf-8"), capture_output=True,
            env=self.environment(), timeout=30,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(plain(result.stdout), "Opus 5.5 (1M context)")
        self.assertEqual(result.stderr.decode("utf-8"), "statusline: rendering: RuntimeError: boom\n")

    def test_unwritable_cache_still_shows_the_metrics(self):
        blocker = self.root / "not-a-folder"
        blocker.write_text("x", encoding="utf-8")
        result = self.run_script(payload(self.transcript()), "200", config=blocker)
        self.assertEqual(result.returncode, 0)
        self.assertIn("turn   3", plain(result.stdout))
        self.assertIn(b"statusline: saving the metrics cache:", result.stderr)


class MetricsTest(StatuslineTestCase):
    """Transcript metrics, computed in-process against the fixture transcripts."""

    def setUp(self):
        super().setUp()
        self.module = load_module()
        patcher = mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.config), "HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.path = self.transcript()
        self.data = {"session_id": SESSION, "transcript_path": str(self.path)}

    def cache_file(self):
        return self.cache / f"{SESSION}.json"

    def test_metrics_from_the_fixture(self):
        self.assertEqual(self.module.session_metrics(self.data), EXPECTED)
        self.assertTrue(self.cache_file().is_file())

    def test_cache_is_reused_and_extended_incrementally(self):
        self.module.session_metrics(self.data)
        cache = json.loads(self.cache_file().read_text(encoding="utf-8"))
        cache["files"][str(self.path)]["turns"] = 42  # only a reused cache can report this
        self.cache_file().write_text(json.dumps(cache), encoding="utf-8")
        self.assertEqual(self.module.session_metrics(self.data)["turns"], 42)

        with open(self.path, "a", encoding="utf-8") as stream:
            stream.write(f'amp": "{iso(290)}"}}\n')  # completes the half-written line: a record without usage
            stream.write(json.dumps(assistant(300, "m4", 1, 10, 3615, 5)) + "\n")
        metrics = self.module.session_metrics(self.data)
        self.assertEqual(metrics["turns"], 43)
        self.assertEqual(metrics["tokens_in"], EXPECTED["tokens_in"] + 11)

    def test_unchanged_transcripts_do_not_rewrite_the_cache(self):
        self.module.session_metrics(self.data)
        before = self.cache_file().stat().st_mtime_ns
        time.sleep(0.05)
        self.module.session_metrics(self.data)
        self.assertEqual(self.cache_file().stat().st_mtime_ns, before)

    def test_a_replaced_transcript_is_read_again(self):
        self.module.session_metrics(self.data)
        self.path.write_text(jsonl(MAIN_RECORDS[:2]), encoding="utf-8")
        self.assertEqual(self.module.session_metrics(self.data)["turns"], 1)

    def test_a_cache_from_another_version_is_ignored(self):
        self.cache.mkdir(parents=True)
        self.cache_file().write_text(json.dumps({"v": 0, "files": {str(self.path): {"off": 10**9}}}), encoding="utf-8")
        self.assertEqual(self.module.session_metrics(self.data), EXPECTED)

    def test_a_damaged_cache_is_replaced(self):
        self.cache.mkdir(parents=True)
        self.cache_file().write_text("{broken", encoding="utf-8")
        with mock.patch.object(self.module, "report") as report:
            self.assertEqual(self.module.session_metrics(self.data), EXPECTED)
        report.assert_called_once()
        json.loads(self.cache_file().read_text(encoding="utf-8"))

    def test_old_cache_files_are_pruned_when_a_session_starts(self):
        self.cache.mkdir(parents=True)
        old, recent = self.cache / "old-session.json", self.cache / "recent-session.json"
        for path in (old, recent):
            path.write_text("{}", encoding="utf-8")
        month_ago = time.time() - 30 * 86400
        os.utime(old, (month_ago, month_ago))
        self.module.session_metrics(self.data)
        self.assertFalse(old.exists())
        self.assertTrue(recent.exists())

    def test_a_long_parse_continues_on_the_next_render(self):
        folder = self.config / "projects" / "-long"
        folder.mkdir(parents=True)
        path = folder / "long-session.jsonl"
        records = [MAIN_RECORDS[0]] + [assistant(10 + index, f"n{index}", 1, 10, 0, 1) for index in range(300)]
        path.write_text(jsonl(records), encoding="utf-8")
        data = {"session_id": "long-session", "transcript_path": str(path)}
        self.module.SCAN_BUDGET_SECONDS = -1  # every render stops after its first batch of lines
        results = [self.module.session_metrics(data) for _ in range(8)]
        self.assertIsNone(results[0], "partial counts are not shown")
        finished = [result for result in results if result is not None]
        self.assertTrue(finished)
        self.assertEqual(finished[0]["turns"], 300)

    def test_no_transcript_means_no_metrics(self):
        self.assertIsNone(self.module.session_metrics({"transcript_path": str(self.root / "missing.jsonl")}))
        self.assertIsNone(self.module.session_metrics({}))
        self.assertFalse(self.cache.exists())


if __name__ == "__main__":
    unittest.main()
