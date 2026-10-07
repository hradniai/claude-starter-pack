"""Tests for the helper scripts in kernel/scripts/: list-env-keys.sh, env-key-classify.py,
inject-current-time.sh and git-autosave.sh.

Run from the repository root: python3 -m unittest discover -s tests -v
Hermetic: HOME points at a temporary directory and every env file is a fake fixture.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "kernel" / "scripts"
BASH = shutil.which("bash") or "/bin/bash"

# A fixture whose values span lines. Every string in VALUE_TEXT appears only inside a value; none of
# them may ever reach the output of the names-only or the classify mode.
ENV_FIXTURE = """# comment line
PLAIN_KEY=plainvalue123
export EXPORTED_TOKEN="tok-abcdef"
MULTI_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
LEAKLINEONE=AAAABBBBCCCC
INNERFAKE_KEY=notakey
-----END RSA PRIVATE KEY-----"
SINGLE_QUOTED_SECRET='first line
SECOND_LEAK_KEY=valuepart
'
lower_case_api_key=lowervalue
SPACED_KEY = spacedvalue
AFTER_MULTI_KEY=aftervalue
UNTERMINATED_SECRET="starts here
NEVER_A_NAME_KEY=leakleak
"""
EXPECTED_NAMES = {"PLAIN_KEY", "EXPORTED_TOKEN", "MULTI_PRIVATE_KEY", "SINGLE_QUOTED_SECRET",
                  "lower_case_api_key", "SPACED_KEY", "AFTER_MULTI_KEY", "UNTERMINATED_SECRET"}
VALUE_TEXT = ["plainvalue123", "tok-abcdef", "BEGIN", "LEAKLINEONE", "AAAABBBB", "INNERFAKE", "notakey",
              "first line", "SECOND_LEAK", "valuepart", "lowervalue", "spacedvalue", "aftervalue",
              "starts here", "NEVER_A_NAME", "leakleak"]


class HelperScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="helper-scripts-test-")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.home, ".claude"))
        self.work = os.path.join(self.tmp, "work")
        os.makedirs(self.work)
        self.env_file = os.path.join(self.work, ".env")
        with open(self.env_file, "w") as fh:
            fh.write(ENV_FIXTURE)
        self.env = {"HOME": self.home, "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8"}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_script(self, args, env=None, cwd=None):
        return subprocess.run(args, capture_output=True, text=True, env=env or self.env, cwd=cwd or self.work,
                              timeout=60)

    def assert_no_value_text(self, output):
        for text in VALUE_TEXT:
            self.assertNotIn(text, output, "value text %r leaked into the output" % text)

    # ---- list-env-keys.sh / env-key-classify.py -------------------------------------------------
    def test_names_from_multiline_file_leak_no_value_text(self):
        r = self.run_script([BASH, str(SCRIPTS / "list-env-keys.sh"), "--from", self.env_file, ".*"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(set(r.stdout.split()), EXPECTED_NAMES)
        self.assert_no_value_text(r.stdout + r.stderr)

    def test_default_pattern_filters_names(self):
        r = self.run_script([BASH, str(SCRIPTS / "list-env-keys.sh"), "--from", self.env_file])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("MULTI_PRIVATE_KEY", r.stdout.split())
        self.assertIn("EXPORTED_TOKEN", r.stdout.split())
        self.assert_no_value_text(r.stdout)

    def test_no_match_is_an_empty_success(self):
        r = self.run_script([BASH, str(SCRIPTS / "list-env-keys.sh"), "--from", self.env_file, "NOTHING_MATCHES_THIS"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "")

    def test_classify_reports_state_without_values(self):
        r = self.run_script([BASH, str(SCRIPTS / "list-env-keys.sh"), "--from", self.env_file, "--classify", ".*"])
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = dict(line.split(": ", 1) for line in r.stdout.strip().splitlines())
        self.assertEqual(set(lines), EXPECTED_NAMES)
        self.assertEqual(lines["MULTI_PRIVATE_KEY"], "filled (private_key)")
        self.assert_no_value_text(r.stdout + r.stderr)

    def test_repeated_key_takes_the_last_value_like_dotenv(self):
        with open(self.env_file, "w") as fh:
            fh.write("DUP_API_KEY=\nOTHER=1 # trailing comment\nDUP_API_KEY=sk-live-aB3dE5fG7hJ9kL1mN3pQ5rS7\n")
        r = self.run_script([sys.executable, "-W", "error", str(SCRIPTS / "env-key-classify.py"), self.env_file, ".*"])
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = dict(line.split(": ", 1) for line in r.stdout.strip().splitlines())
        self.assertEqual(lines["DUP_API_KEY"], "filled (api_key)")
        self.assertEqual(r.stdout.count("DUP_API_KEY"), 1)
        names = self.run_script([sys.executable, str(SCRIPTS / "env-key-classify.py"), "--names", self.env_file])
        self.assertEqual(names.stdout.split(), ["DUP_API_KEY", "OTHER"])

    def test_process_environment_multiline_value_does_not_leak(self):
        env = dict(self.env, MULTILINE_SECRET_KEY="header\nPROC_LEAK_LINE=topsecretvalue\nTOKEN tail text")
        cwd = os.path.join(self.tmp, "empty")
        os.makedirs(cwd)
        r = self.run_script([BASH, str(SCRIPTS / "list-env-keys.sh")], env=env, cwd=cwd)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("MULTILINE_SECRET_KEY", r.stdout.split())
        for text in ("PROC_LEAK_LINE", "topsecretvalue", "TOKEN tail", "header"):
            self.assertNotIn(text, r.stdout)

    def test_default_sources_include_project_and_global_env(self):
        with open(os.path.join(self.home, ".claude", ".env"), "w") as fh:
            fh.write('GLOBAL_API_KEY="multi\nGLOBAL_LEAK_KEY=x\n"\n')
        r = self.run_script([BASH, str(SCRIPTS / "list-env-keys.sh"), "_KEY$"])
        self.assertEqual(r.returncode, 0, r.stderr)
        names = set(r.stdout.split())
        self.assertIn("GLOBAL_API_KEY", names)
        self.assertIn("MULTI_PRIVATE_KEY", names)
        self.assertNotIn("GLOBAL_LEAK_KEY", names)
        self.assertNotIn("LEAKLINEONE", names)

    # ---- inject-current-time.sh --------------------------------------------------------------
    def test_inject_current_time_emits_valid_hook_json(self):
        r = self.run_script([BASH, str(SCRIPTS / "inject-current-time.sh")])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "UserPromptSubmit")
        self.assertRegex(out["additionalContext"], r"^Current local time: \d{4}-\d{2}-\d{2} \d{2}:\d{2} ")

    # ---- git-autosave.sh ---------------------------------------------------------------------
    @unittest.skipUnless(shutil.which("git"), "git is required")
    def test_git_autosave_ensure_inside_documents(self):
        proj = os.path.join(self.home, "Documents", "proj")
        os.makedirs(proj)
        r = self.run_script([BASH, str(SCRIPTS / "git-autosave.sh"), "ensure"], cwd=proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isdir(os.path.join(proj, ".git")))
        with open(os.path.join(proj, ".gitignore")) as fh:
            written = fh.read().splitlines()                # the fallback: no template in this fake home
        for name in (".env", ".env.*", ".envrc"):
            self.assertIn(name, written)
        log = subprocess.run(["git", "-C", proj, "log", "--oneline"], capture_output=True, text=True,
                             env=self.env)
        self.assertNotEqual(log.returncode, 0, "ensure must never commit")

    @unittest.skipUnless(shutil.which("git"), "git is required")
    def test_git_autosave_keeps_an_existing_gitignore(self):
        proj = os.path.join(self.home, "Documents", "kept")
        os.makedirs(proj)
        with open(os.path.join(proj, ".gitignore"), "w") as fh:
            fh.write("mine/\n")
        r = self.run_script([BASH, str(SCRIPTS / "git-autosave.sh"), "ensure"], cwd=proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(proj, ".gitignore")) as fh:
            self.assertEqual(fh.read(), "mine/\n")

    @unittest.skipUnless(shutil.which("git"), "git is required")
    def test_git_autosave_workspace_from_env_and_from_file(self):
        # A documents folder somewhere else (OneDrive on Windows): named by the variable, or by the
        # one-line file the installer writes, CRLF and ~ included. ~/Documents then stops counting.
        onedrive = os.path.join(self.home, "OneDrive", "Documents")
        inside = os.path.join(onedrive, "client-a")
        documents = os.path.join(self.home, "Documents", "other")
        for d in (inside, documents):
            os.makedirs(d)
        ensure = [BASH, str(SCRIPTS / "git-autosave.sh"), "ensure"]
        r = self.run_script(ensure, env=dict(self.env, CLAUDE_WORKSPACE_ROOT=onedrive), cwd=inside)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isdir(os.path.join(inside, ".git")))
        r = self.run_script(ensure, env=dict(self.env, CLAUDE_WORKSPACE_ROOT=onedrive), cwd=documents)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(documents, ".git")))
        shutil.rmtree(os.path.join(inside, ".git"))
        with open(os.path.join(self.home, ".claude", "workspace-root"), "w", newline="") as fh:
            fh.write("~/OneDrive/Documents/\r\n")
        r = self.run_script(ensure, cwd=inside)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isdir(os.path.join(inside, ".git")))
        container = os.path.join(onedrive, "_CLIENTS")
        os.makedirs(container)
        r = self.run_script(ensure, cwd=container)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(container, ".git")))

    def test_git_autosave_reads_windows_paths_and_ignores_case_where_the_os_does(self):
        # The two helpers, run on their own: a C:\\... path from the installer becomes Git Bash's
        # /c/..., and paths compare in lower case on macOS and Windows only.
        source = (SCRIPTS / "git-autosave.sh").read_text(encoding="utf-8")
        functions = "\n".join(re.findall(r"^(?:workspace_root|comparable)\(\) \{\n.*?^\}$", source, re.M | re.S))
        self.assertEqual(functions.count("() {"), 2)
        with open(os.path.join(self.home, ".claude", "workspace-root"), "w", newline="") as fh:
            fh.write("C:\\Users\\Me\\OneDrive - Acme\\Documents\r\n")
        script = functions + '\nworkspace_root; echo; OSTYPE=darwin22; comparable "/Users/Me/X"; echo; ' \
                             'OSTYPE=msys; comparable "/c/Users/Me"; echo; OSTYPE=linux-gnu; comparable "/home/Me"'
        r = self.run_script([BASH, "-c", script])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(), ["/c/Users/Me/OneDrive - Acme/Documents", "/users/me/x",
                                                 "/c/users/me", "/home/Me"])

    @unittest.skipUnless(shutil.which("git") and shutil.which("ps"), "git and ps are required")
    def test_git_autosave_skips_headless_claude_sessions(self):
        # A fake `claude -p` runs the Bash tool's shell, which runs the script: claude is the
        # grandparent, the way Claude Code really starts it.
        proj = os.path.join(self.home, "Documents", "headless")
        os.makedirs(proj)
        env = dict(self.env, GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.invalid",
                   GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.invalid")
        bindir = os.path.join(self.tmp, "bin")
        os.makedirs(bindir)
        os.symlink(sys.executable, os.path.join(bindir, "claude"))
        launcher = ("import subprocess, sys; sys.exit(subprocess.run(['%s', '-c', 'bash %s ensure']).returncode)"
                    % (BASH, SCRIPTS / "git-autosave.sh"))
        for flag, expect_repo in (("-p", False), ("--print", False), ("--resume", True)):
            with self.subTest(flag=flag):
                shutil.rmtree(os.path.join(proj, ".git"), ignore_errors=True)
                r = subprocess.run([os.path.join(bindir, "claude"), "-c", launcher, flag, "prompt"],
                                   capture_output=True, text=True, env=env, cwd=proj, timeout=60)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(os.path.isdir(os.path.join(proj, ".git")), expect_repo)

    @unittest.skipUnless(shutil.which("git"), "git is required")
    def test_git_autosave_is_a_no_op_outside_documents(self):
        r = self.run_script([BASH, str(SCRIPTS / "git-autosave.sh"), "ensure"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.work, ".git")))

    @unittest.skipUnless(shutil.which("git"), "git is required")
    def test_git_autosave_never_makes_a_container_root_a_repository(self):
        root = os.path.join(self.home, "Documents", "_CLIENTS")
        os.makedirs(root)
        r = self.run_script([BASH, str(SCRIPTS / "git-autosave.sh"), "ensure"], cwd=root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(root, ".git")))

    def test_git_autosave_rejects_unknown_mode(self):
        r = self.run_script([BASH, str(SCRIPTS / "git-autosave.sh"), "bogus"],
                            cwd=os.path.join(self.home))
        self.assertEqual(r.returncode, 0)  # outside ~/Documents it exits before reading the mode
        os.makedirs(os.path.join(self.home, "Documents", "p"))
        r = self.run_script([BASH, str(SCRIPTS / "git-autosave.sh"), "bogus"],
                            cwd=os.path.join(self.home, "Documents", "p"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("usage", r.stderr)


class ShippedFilesTests(unittest.TestCase):
    """Static checks on what this repo installs into ~/.claude/scripts and settings.json."""

    def test_python_scripts_parse_as_python_39(self):
        import ast
        shipped = sorted(SCRIPTS.glob("*.py")) + sorted((REPO_ROOT / "kernel" / "workflows").rglob("*.py"))
        self.assertIn(SCRIPTS / "check_source.py", shipped)
        for path in shipped:
            with self.subTest(script=path.name):
                ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))

    def test_no_em_dash_or_horizontal_bar(self):
        targets = list(SCRIPTS.iterdir()) + [REPO_ROOT / "kernel" / "settings.json"] + list(
            (REPO_ROOT / "tests").glob("test_*.py"))
        for path in targets:
            if path.is_file():
                with self.subTest(file=path.name):
                    text = path.read_text(encoding="utf-8")
                    self.assertNotIn("\u2014", text)
                    self.assertNotIn("\u2015", text)

    def test_kernel_files_have_lf_line_endings(self):
        # A CRLF python-launcher.sh is a syntax error for sh (exit 2), so every command would be blocked;
        # .gitattributes keeps a Windows checkout (core.autocrlf=true) from converting the files.
        for path in sorted((REPO_ROOT / "kernel").rglob("*")):
            if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts:
                with self.subTest(file=str(path.relative_to(REPO_ROOT))):
                    self.assertNotIn(b"\r", path.read_bytes())
        rules = [line.split() for line in (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
                 if line.strip() and not line.startswith("#")]
        self.assertIn(["*", "text=auto", "eol=lf"], rules)
        if shutil.which("git") and (REPO_ROOT / ".git").exists():
            r = subprocess.run(["git", "-C", str(REPO_ROOT), "check-attr", "eol", "--",
                                "kernel/scripts/python-launcher.sh", "kernel/settings.json"],
                               capture_output=True, text=True)
            self.assertEqual(r.stdout.count(": eol: lf"), 2, r.stdout + r.stderr)

    def test_settings_hooks_point_at_shipped_scripts(self):
        settings = json.loads((REPO_ROOT / "kernel" / "settings.json").read_text(encoding="utf-8"))
        commands = [h["command"] for groups in settings["hooks"].values() for g in groups for h in g["hooks"]]
        commands.append(settings["statusLine"]["command"])
        for command in commands:
            with self.subTest(command=command):
                script = re.search(r"~/\.claude/scripts/(\S+)", command).group(1)
                self.assertTrue((SCRIPTS / script).is_file(), "%s is not shipped in kernel/scripts" % script)
                self.assertNotRegex(command, r"^python3? ", "Python must start through python-launcher.sh")
                launched = re.match(r"^sh ~/\.claude/scripts/python-launcher\.sh (guard|quiet|plain) (\S+\.py)$",
                                    command)
                if script == "python-launcher.sh":
                    self.assertIsNotNone(launched, command)
                    self.assertTrue((SCRIPTS / launched.group(2)).is_file(), launched.group(2))
        guards = [h["command"] for g in settings["hooks"]["PreToolUse"] for h in g["hooks"]]
        self.assertTrue(guards and all(" guard " in c for c in guards), "a safety hook must fail closed")
        self.assertIn(" quiet ", settings["statusLine"]["command"])

    def test_launcher_half_parses_on_old_pythons(self):
        # python-launcher.py must reach its version check on any Python, so no newer syntax may slip in
        # (ast cannot parse as Python 2; 3.4 is the oldest grammar it offers, and the file has no f-strings).
        import ast
        text = (SCRIPTS / "python-launcher.py").read_text(encoding="utf-8")
        ast.parse(text, feature_version=(3, 4))
        self.assertNotRegex(text, r"\bf['\"]|\bnonlocal\b|\basync\b|:=")
        self.assertLess(text.index("sys.exit(86)"), text.index("import os"))


def write_executable(path, text):
    with open(path, "w") as fh:
        fh.write(text)
    os.chmod(path, 0o755)


class LauncherTests(unittest.TestCase):
    """python-launcher.sh picks a Python 3.9+ from fake interpreters on a PATH that holds nothing else:
    a real one, a Microsoft Store placeholder (prints an install hint, exit 9009), an old one (a real
    Python that reports version 3.8, so python-launcher.py's own check is what turns it down), a py
    launcher, and one that gets killed. Runs against a copy of kernel/scripts, so the bytecode cache it
    writes stays out of the repository."""

    SH = shutil.which("sh") or "/bin/sh"

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="launcher-test-")
        self.scripts = os.path.join(self.tmp, "scripts")
        shutil.copytree(str(SCRIPTS), self.scripts, ignore=shutil.ignore_patterns("__pycache__"))
        write_executable(os.path.join(self.scripts, "probe.py"), (
            "import json, sys\n"
            "data = sys.stdin.read()\n"
            "print(json.dumps({'argv': sys.argv[1:], 'stdin': data, 'out': sys.stdout.encoding,\n"
            "                  'errors': [sys.stdin.errors, sys.stdout.errors, sys.stderr.errors]}))\n"
            "if sys.argv[1:2] == ['raise']:\n"
            "    raise RuntimeError('boom')\n"
            "sys.exit(int(sys.argv[1]) if sys.argv[1:] and sys.argv[1].isdigit() else 0)\n"))
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.home, "proj"))
        self.marks = os.path.join(self.tmp, "marks")
        os.makedirs(self.marks)
        self.kinds = {
            "real": '#!/bin/sh\necho "$0" >> "%s/ran"\nexec "%s" "$@"\n' % (self.marks, sys.executable),
            "store": '#!/bin/sh\necho "Python was not found; run without arguments to install from the '
                     'Microsoft Store" >&2\nexit 9009\n',
            "old": '#!/bin/sh\nexec "%s" -c "import sys; sys.version_info = (3, 8, 18); p = sys.argv[3]; '
                   'sys.argv = sys.argv[3:]; exec(compile(open(p).read(), p, \'exec\'), '
                   '{\'__name__\': \'__main__\', \'__file__\': p})" "$@"\n' % sys.executable,
            "py": '#!/bin/sh\n[ "$1" = -3 ] || exit 103\nshift\necho py >> "%s/ran"\nexec "%s" "$@"\n'
                  % (self.marks, sys.executable),
            "killed": '#!/bin/sh\nkill -9 $$\n',
        }

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path_with(self, **names):
        """A bin folder holding only the named fake interpreters, e.g. python3='store', python='real'."""
        bindir = tempfile.mkdtemp(prefix="bin-", dir=self.tmp)
        for name, kind in names.items():
            write_executable(os.path.join(bindir, name), self.kinds[kind])
        return bindir

    def launch(self, mode, script, args=(), stdin="", path=None, extra_env=None):
        # LC_ALL=C and PYTHONIOENCODING=latin-1 would make a plain Python print ASCII or Latin-1; the
        # launcher has to deliver UTF-8 anyway, as it must on a Windows console code page.
        env = {"HOME": self.home, "PATH": path if path is not None else self.path_with(python3="real"),
               "LC_ALL": "C", "PYTHONIOENCODING": "latin-1"}
        env.update(extra_env or {})
        return subprocess.run([self.SH, os.path.join(self.scripts, "python-launcher.sh"), mode, script] + list(args),
                              input=stdin, capture_output=True, text=True, encoding="utf-8", env=env,
                              cwd=os.path.join(self.home, "proj"), timeout=60)

    def ran(self):
        try:
            with open(os.path.join(self.marks, "ran")) as fh:
                return [os.path.basename(line.strip()) for line in fh]
        except OSError:
            return []

    def hook_payload(self, command):
        return json.dumps({"tool_name": "Bash", "tool_input": {"command": command},
                           "cwd": os.path.join(self.home, "proj")})

    def test_runs_the_script_and_passes_exit_codes_through(self):
        r = self.launch("plain", "probe.py", ["0", "ä"], stdin="payload ř")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["argv"], ["0", "ä"])
        self.assertEqual(out["stdin"], "payload ř")
        self.assertEqual(out["out"], "utf-8", "stdout must be UTF-8 whatever the locale says")
        self.assertEqual(out["errors"], ["replace", "backslashreplace", "backslashreplace"],
                         "the launcher set up the streams itself, not the locale")
        for code in (1, 2, 3):
            self.assertEqual(self.launch("guard", "probe.py", [str(code)]).returncode, code)
        self.assertEqual(self.launch("guard", "probe.py", ["55"]).returncode, 1, "55 is reserved for a crash")
        self.assertEqual(self.ran(), ["python3"] * 5, "one interpreter start per call")
        cached = os.listdir(os.path.join(self.scripts, "__pycache__"))
        self.assertTrue(any(name.startswith("probe.") and name.endswith(".pyc") for name in cached), cached)

    def test_a_crashing_guard_fails_closed(self):
        # Claude Code lets a call through on any exit code but 2, so a hook that fails to load or
        # crashes must block in guard mode; the status line and helpers keep exit 1.
        write_executable(os.path.join(self.scripts, "broken.py"), "def (:\n")
        write_executable(os.path.join(self.scripts, "missing-import.py"), "import no_such_module_here\n")
        path = self.path_with(python3="real", python="real")
        for script, args, error in (("probe.py", ["raise"], "RuntimeError: boom"),
                                    ("broken.py", [], "SyntaxError"),
                                    ("missing-import.py", [], "ModuleNotFoundError")):
            with self.subTest(script=script):
                guard = self.launch("guard", script, args, stdin=self.hook_payload("ls"), path=path)
                self.assertEqual(guard.returncode, 2, guard.stderr)
                self.assertIn(error, guard.stderr)
                self.assertIn("BLOCKED by the safety layer", guard.stderr)
                self.assertIn("Do not try to run this action another way", guard.stderr)
                self.assertNotIn("Python 3.9", guard.stderr, "a crash is not a missing Python")
                for mode in ("plain", "quiet"):
                    other = self.launch(mode, script, args, path=path)
                    self.assertEqual(other.returncode, 1, other.stderr)
                    self.assertNotIn("BLOCKED", other.stderr)
        self.assertEqual(self.ran(), ["python3"] * 9, "a crash is never retried with another Python")

    def test_streams_become_utf8_whatever_the_code_page(self):
        # A Windows console hands Python its ANSI code page (cp1252 here), which cannot print every path.
        import importlib.util
        import io
        from unittest import mock
        spec = importlib.util.spec_from_file_location("launcher_half", str(SCRIPTS / "python-launcher.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        streams = dict((name, io.TextIOWrapper(io.BytesIO(), encoding="cp1252")) for name in ("stdin", "stdout", "stderr"))
        with mock.patch.multiple(sys, **streams):
            module.utf8_streams()
            sys.stdout.write("klíč ř\n")
            sys.stdout.flush()
        self.assertEqual([s.encoding for s in streams.values()], ["utf-8"] * 3)
        self.assertEqual(streams["stdout"].buffer.getvalue(), "klíč ř\n".encode("utf-8"))

    def test_safety_hook_allows_and_blocks_through_the_launcher(self):
        allow = self.launch("guard", "bash-safety-extended.py", stdin=self.hook_payload("ls -la"))
        self.assertEqual(allow.returncode, 0, allow.stderr)
        block = self.launch("guard", "bash-safety-extended.py", stdin=self.hook_payload("cat ~/.ssh/id_rsa"))
        self.assertEqual(block.returncode, 2, block.stderr)
        self.assertIn("BLOCKED by bash-safety-extended", block.stderr)

    def test_install_check_payloads_give_the_documented_results(self):
        # INSTRUCTIONS.md 1.4 feeds these files to the installed hooks; the guide states these results.
        checks = REPO_ROOT / "tests" / "fixtures" / "hook-checks"
        for name, script, code, needle in (("allow-ls.json", "bash-safety-extended.py", 0, ""),
                                           ("block-rm-rf.json", "bash-safety-extended.py", 2,
                                            "BLOCKED by bash-safety-extended"),
                                           ("push-main.json", "git-push-guard.py", 2, "BLOCKED by git-push-guard")):
            with self.subTest(payload=name):
                r = self.launch("guard", script, stdin=(checks / name).read_text(encoding="utf-8"))
                self.assertEqual(r.returncode, code, r.stderr)
                self.assertIn(needle, r.stderr)
                self.assertIn(name, (REPO_ROOT / "INSTRUCTIONS.md").read_text(encoding="utf-8"))

    def test_store_placeholder_and_old_python_are_skipped(self):
        for python3 in ("store", "old"):
            with self.subTest(python3=python3):
                path = self.path_with(python3=python3, python="real")
                block = self.launch("guard", "bash-safety-extended.py", path=path,
                                    stdin=self.hook_payload("cat ~/.aws/credentials"))
                self.assertEqual(block.returncode, 2, block.stderr)
                self.assertIn("~/.aws/credentials", block.stderr, "the hook input reached the second candidate")
                allow = self.launch("guard", "bash-safety-extended.py", path=path, stdin=self.hook_payload("ls"))
                self.assertEqual(allow.returncode, 0, allow.stderr)

    def test_no_usable_python_fails_closed_for_guards_only(self):
        for path in (self.path_with(), self.path_with(python3="store", python="old")):
            with self.subTest(path=sorted(os.listdir(path))):
                guard = self.launch("guard", "bash-safety-extended.py", path=path, stdin=self.hook_payload("ls"))
                self.assertEqual(guard.returncode, 2)
                self.assertIn("Python 3.9", guard.stderr)
                self.assertIn("bash-safety-extended.py could not run", guard.stderr)
                self.assertIn("Do not try to run this action another way", guard.stderr)
                quiet = self.launch("quiet", "statusline.py", path=path, stdin="{}")
                self.assertEqual((quiet.returncode, quiet.stdout), (0, ""))
                self.assertNotIn("could not run", quiet.stderr)
                plain = self.launch("plain", "env-key-classify.py", ["--names", "x"], path=path)
                self.assertEqual(plain.returncode, 1)
                self.assertIn("could not run", plain.stderr)
        r = self.launch("guard", "probe.py", path=self.path_with(python3="store", python="old"))
        self.assertIn("python3 (did not run, exit 49)", r.stderr)
        self.assertIn("python (older than 3.9)", r.stderr)
        self.assertIn("python3 (not found)", self.launch("guard", "probe.py", path=self.path_with()).stderr)

    def test_windows_prefers_the_py_launcher(self):
        path = self.path_with(py="py", python3="store", python="real")
        r = self.launch("plain", "probe.py", ["0"], path=path, extra_env={"OS": "Windows_NT"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.ran(), ["py"])
        r = self.launch("guard", "probe.py", path=self.path_with(), extra_env={"OS": "Windows_NT"})
        self.assertIn("py (not found); python (not found); python3 (not found);", r.stderr)
        self.assertIn("Add python.exe to PATH", r.stderr)

    def test_a_killed_interpreter_is_not_retried(self):
        path = self.path_with(python3="killed", python="real")
        r = self.launch("guard", "bash-safety-extended.py", path=path, stdin=self.hook_payload("ls"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("stopped", r.stderr)
        self.assertEqual(self.ran(), [], "the hook input may already be consumed; no second run")
        self.assertEqual(self.launch("quiet", "statusline.py", path=path).returncode, 0)

    def test_bad_arguments(self):
        for mode, code in (("guard", 2), ("quiet", 0), ("plain", 1)):
            with self.subTest(mode=mode):
                for script in ("no-such-script.py", "../probe.py"):
                    r = self.launch(mode, script)
                    self.assertEqual(r.returncode, code)
                    self.assertNotIn("Fix:", r.stderr, "a bad script name is not a missing Python")
                    self.assertNotIn("Python 3.9", r.stderr)
        r = self.launch("bogus", "probe.py")
        self.assertEqual(r.returncode, 1)
        self.assertIn("usage", r.stderr)


if __name__ == "__main__":
    unittest.main()
