#!/usr/bin/env python3
"""Claude Code status line whose layout adapts to the width of the terminal.

Claude Code writes the session as JSON to stdin and shows what this script prints. The fields, in four
groups:
  identity  model and effort, output style, project with worktree and git branch, active agent, and the
            account when Claude Code runs from a config folder other than ~/.claude
  money     session cost, tokens in and out (subagents included), session time (current run)
  context   a gauge of how full the context window is, turns, context growth per turn
  limits    5-hour and 7-day usage, each with its reset countdown

Layout. Claude Code captures the output, so the script cannot ask the terminal for its size: it reads
COLUMNS, which Claude Code sets before every run (80 when missing or invalid). Every field is a segment
with a priority and up to three forms (full, compact, minimal). A wide terminal gets two lines,
identity | money over context | limits. When those do not fit, the segments are packed in priority order
into as many lines as they need, at most five, in their compact forms; if five lines are not enough, the
least important segments switch to their minimal forms and, only then, are left out, least important
first. Model, context, 5-hour and 7-day usage are never left out. A segment wider than a whole line is
cut with an ellipsis.

Design choices:
- Grouping is done with whitespace, not glyphs. A wall of separators gives every field the same weight
  and buries the one number that actually needs attention.
- Identity is context you already know, so it stays quiet; the project name is the one part of it that
  is not dimmed. Reference data (cost, tokens, time) is permanently dim.
- Full forms pad numbers to fixed widths, so values stay in place as they grow.

Metrics. Turns, growth, session tokens and times come from the transcript and the transcripts of its
subagents. They are parsed incrementally with a per-session cache in <config>/cache/statusline/
(config is $CLAUDE_CONFIG_DIR or ~/.claude), so a render stays fast on transcripts of tens of megabytes.

Python 3.9+, standard library only, no jq. Missing fields or bad input give fewer segments, never a
traceback; a failure writes one line to stderr, which Claude Code does not display.

Registered in settings.json as
  "statusLine": {"type": "command", "command": "sh ~/.claude/scripts/python-launcher.sh quiet statusline.py"}
"""

import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime

RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
ORANGE = "\033[38;5;208m"
EFFORT_GREY = "\033[38;5;246m"
PIPE_GREY = "\033[38;5;103m"

# The dot separates fields within a group. The pipe marks the one real break in a line (identity | live
# numbers): muted enough not to shout, distinctly more present than the dot.
DOT = f"{DIM} · {RESET}"
PIPE = f"{PIPE_GREY} │ {RESET}"
SEPARATOR_WIDTH = 3

ANSI = re.compile(r"\033\[[0-9;]*m")
ANSI_OR_CHARACTER = re.compile(r"\033\[[0-9;]*m|.", re.DOTALL)
# Control characters in a name (an escape, a newline) would break the layout or recolour the line.
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")

DEFAULT_COLUMNS = 80
# Claude Code draws the status line inside its footer, which keeps two columns of padding on each side,
# and cuts every line that is wider than what is left (measured on Claude Code 2.1.282).
FOOTER_PADDING = 4
MIN_WIDTH = 10
MAX_LINES = 5
# Model, context, 5-hour and 7-day usage (priorities 0 to 3) are never left out.
LAST_ESSENTIAL = 3
GIT_TIMEOUT_SECONDS = 2
WEEK = 604800

MODEL_FAMILIES = ("fable", "mythos", "opus", "sonnet", "haiku")
EFFORTS = {"xhigh": "xh", "high": "h", "medium": "m", "low": "l", "max": "max"}

CACHE_FOLDER = ("cache", "statusline")
# Bump when the tracked fields change: a cache written by an older version would otherwise carry
# missing counters forward as zeros.
CACHE_VERSION = 1
CACHE_MAX_AGE_SECONDS = 14 * 86400
# A resumed session can bring a large transcript to parse in one go. The parse stops after this long,
# keeps its progress in the cache and continues on the next render; until it has caught up, the
# transcript metrics stay hidden rather than show partial counts.
SCAN_BUDGET_SECONDS = 0.4
SCAN_CHECK_EVERY = 64
# A jump in context this large is not one turn's growth (a resumed or restored context), so it is ignored.
GROWTH_CEILING = 400_000


# --------------------------------------------------------------------------------------------------
# Reading the input


def field(data, *path):
    """The value at `path`, or None when it is absent, null or false (like jq's `// empty`)."""
    node = data
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    if node is None or node is False:
        return None
    return node


def text(data, *path):
    """A field as display text, with control characters removed; objects and lists count as missing."""
    value = field(data, *path)
    if value is None or isinstance(value, (dict, list)):
        return ""
    if value is True:
        return "true"
    return CONTROL.sub("", str(value)).strip()


def number(value):
    """A finite float from a number or a numeric string, else None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        result = float(value)
    elif isinstance(value, str):
        try:
            result = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    if result != result or result in (float("inf"), float("-inf")):
        return None
    return result


def epoch_seconds(value):
    """A reset time as Unix seconds: from seconds, milliseconds, a numeric string or ISO 8601 text."""
    result = number(value)
    if result is not None:
        return result / 1000 if result > 1e12 else result
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def rounded(value):
    """Round half to even, like awk's printf "%.0f"."""
    return int(f"{value:.0f}")


def config_dir():
    raw = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join("~", ".claude")
    return os.path.abspath(os.path.expanduser(raw))


def terminal_columns():
    """COLUMNS as Claude Code sets it; a missing or invalid value counts as 80."""
    try:
        columns = int(os.environ.get("COLUMNS", "").strip())
    except ValueError:
        return DEFAULT_COLUMNS
    return columns if columns > 0 else DEFAULT_COLUMNS


def run_quietly(command):
    """The stdout of a command, or None when it cannot start, fails or outlives GIT_TIMEOUT_SECONDS.

    On macOS and Linux it is started with os.posix_spawnp: importing subprocess alone costs about a
    tenth of a render (measured), more than the git call itself. Elsewhere subprocess does it."""
    if not hasattr(os, "posix_spawnp"):
        import subprocess

        try:
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=GIT_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return result.stdout if result.returncode == 0 else None

    import select

    # Both descriptors are close-on-exec, so the child keeps only the copies made below.
    reader, writer = os.pipe()
    null = os.open(os.devnull, os.O_RDWR)
    try:
        child = os.posix_spawnp(command[0], command, os.environ, file_actions=[
            (os.POSIX_SPAWN_DUP2, null, 0),
            (os.POSIX_SPAWN_DUP2, writer, 1),
            (os.POSIX_SPAWN_DUP2, null, 2),
        ])
    except OSError:
        os.close(reader)
        return None
    finally:
        os.close(writer)
        os.close(null)
    output = b""
    deadline = time.monotonic() + GIT_TIMEOUT_SECONDS
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([reader], [], [], remaining)[0]:
                os.kill(child, 9)  # SIGKILL: it is taking too long
                os.waitpid(child, 0)
                return None
            chunk = os.read(reader, 65536)
            if not chunk:
                break
            output += chunk
    finally:
        os.close(reader)
    _, status = os.waitpid(child, 0)
    return output if os.waitstatus_to_exitcode(status) == 0 else None


def git_branch(project_dir):
    """The checked-out branch of project_dir, asked of git directly; empty when unknown."""
    if not project_dir or not os.path.isdir(project_dir):
        return ""
    output = run_quietly(["git", "-C", project_dir, "symbolic-ref", "--short", "HEAD"])
    return CONTROL.sub("", output.decode("utf-8", "replace")).strip() if output else ""


# --------------------------------------------------------------------------------------------------
# Transcript metrics


def fresh_state():
    return {
        "off": 0, "turns": 0, "solo_turns": 0, "prompt_ts": "", "first_ts": "", "max_ts": "",
        "tin": 0, "tout": 0, "last_ctx": 0, "gsum": 0, "gn": 0, "glast": 0, "lastid": "",
    }


def restored_state(cached):
    """A cached parse state, keeping only the fields of the expected type."""
    state = fresh_state()
    if isinstance(cached, dict):
        for key, default in state.items():
            value = cached.get(key)
            if type(value) is type(default):
                state[key] = value
    return state


def token_count(usage, key):
    value = usage.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def absorb(state, raw):
    """Fold one transcript line into the parse state."""
    line = raw.strip()
    if not line.startswith(b"{"):
        return
    try:
        record = json.loads(line)
    except ValueError:
        return
    if not isinstance(record, dict):
        return
    stamp = record.get("timestamp")
    # Anything but an ISO 8601 time would sort after every real one and stick as the latest activity.
    stamp = stamp if isinstance(stamp, str) and stamp[:4].isdigit() else ""
    # ISO 8601 UTC sorts correctly as a plain string, so tracking the latest activity costs no date
    # parsing until the very end.
    if stamp > state["max_ts"]:
        state["max_ts"] = stamp
    if stamp and not state["first_ts"]:
        state["first_ts"] = stamp
    message = record.get("message")
    message = message if isinstance(message, dict) else {}
    kind = record.get("type")

    if kind == "user":
        if record.get("isSidechain") or record.get("isMeta"):
            return
        # A prompt the user typed carries text. User records that carry only tool results are the
        # harness feeding results back, not the user typing.
        content = message.get("content")
        typed = isinstance(content, str) or (
            isinstance(content, list)
            and any(isinstance(block, dict) and block.get("type") == "text" for block in content)
        )
        if typed and stamp:
            state["prompt_ts"] = stamp
            state["solo_turns"] = 0
        return

    if kind != "assistant":
        return
    usage = message.get("usage")
    if not isinstance(usage, dict) or not usage:
        return
    message_id = message.get("id")
    message_id = message_id if isinstance(message_id, str) else ""
    if message_id and message_id == state["lastid"]:
        return  # another record of the same message, carrying the same usage
    state["lastid"] = message_id
    fresh = token_count(usage, "input_tokens") + token_count(usage, "cache_creation_input_tokens")
    state["tin"] += fresh
    state["tout"] += token_count(usage, "output_tokens")
    if record.get("isSidechain"):
        return  # a subagent's turns are not yours
    state["turns"] += 1
    state["solo_turns"] += 1
    context = fresh + token_count(usage, "cache_read_input_tokens")
    if state["last_ctx"] and context > state["last_ctx"]:
        growth = context - state["last_ctx"]
        if growth < GROWTH_CEILING:
            state["glast"] = growth
            state["gsum"] += growth
            state["gn"] += 1
    state["last_ctx"] = context


def scan(path, cached, deadline):
    """Parse a transcript from the cached byte offset. Returns (state, finished)."""
    state = restored_state(cached)
    try:
        size = os.path.getsize(path)
    except OSError:
        return state, True
    if state["off"] > size:
        state = fresh_state()  # the file was truncated or replaced: start over
    if state["off"] == size:
        return state, True
    with open(path, "rb") as stream:
        stream.seek(state["off"])
        for count, raw in enumerate(stream, 1):
            if not raw.endswith(b"\n"):
                break  # a line still being written; it is read in full next time
            state["off"] += len(raw)
            absorb(state, raw)
            if count % SCAN_CHECK_EVERY == 0 and time.monotonic() > deadline:
                return state, state["off"] >= size
    return state, True


def first_session_id(path):
    """The sessionId of a transcript's first record; None while that line is not fully written."""
    try:
        with open(path, "rb") as stream:
            head = stream.readline()
    except OSError:
        return None
    if not head.endswith(b"\n"):
        return None
    try:
        record = json.loads(head)
    except ValueError:
        return ""
    session = record.get("sessionId") if isinstance(record, dict) else None
    return session if isinstance(session, str) else ""


def agent_files(folder):
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return []
    return sorted(
        entry.path for entry in entries if entry.name.startswith("agent-") and entry.name.endswith(".jsonl")
    )


def subagent_transcripts(transcript, session, known):
    """The transcripts of this session's subagents. `known` caches which older-layout files belong."""
    folder = os.path.dirname(transcript)
    stem = os.path.splitext(os.path.basename(transcript))[0]
    paths = agent_files(os.path.join(folder, stem, "subagents"))
    # Older Claude Code versions wrote subagent transcripts next to the main one, naming the parent
    # session in their first record.
    for path in agent_files(folder):
        belongs = known.get(path)
        if not isinstance(belongs, bool):
            session_id = first_session_id(path)
            if session_id is None:
                continue
            belongs = bool(session) and session_id == session
            known[path] = belongs
        if belongs:
            paths.append(path)
    return paths


def parse_time(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def span(start, end):
    """Whole seconds from one ISO 8601 time to another; 0 when either is unknown."""
    if not start or not end or end <= start:
        return 0
    first, last = parse_time(start), parse_time(end)
    if first is None or last is None:
        return 0
    try:
        return max(int((last - first).total_seconds()), 0)
    except TypeError:
        return 0  # one time has a time zone and the other has none


def load_cache(path):
    try:
        with open(path, encoding="utf-8") as stream:
            cache = json.load(stream)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as error:
        report("reading the metrics cache", error)
        return {}
    return cache if isinstance(cache, dict) else {}


def prune_cache(folder, now):
    """Delete cache files of sessions untouched for two weeks, so the folder does not grow forever."""
    try:
        entries = list(os.scandir(folder))
    except OSError as error:
        report("pruning the metrics cache", error)
        return
    for entry in entries:
        try:
            if entry.is_file(follow_symlinks=False) and now - entry.stat().st_mtime > CACHE_MAX_AGE_SECONDS:
                os.remove(entry.path)
        except OSError as error:
            report("pruning the metrics cache", error)


def save_cache(folder, path, cache, prune):
    try:
        os.makedirs(folder, exist_ok=True)
        if prune:
            prune_cache(folder, time.time())
        temporary = f"{path}.{os.getpid()}.tmp"
        with open(temporary, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(cache, separators=(",", ":")))
        os.replace(temporary, path)
    except OSError as error:
        report("saving the metrics cache", error)


def session_metrics(data):
    """Turns, growth, tokens and times from the transcripts; None when unavailable or not caught up."""
    transcript = text(data, "transcript_path")
    if not transcript or not os.path.isfile(transcript):
        return None
    session = text(data, "session_id")
    key = re.sub(r"[^A-Za-z0-9._-]", "_", session or os.path.basename(transcript))[:120]
    folder = os.path.join(config_dir(), *CACHE_FOLDER)
    path = os.path.join(folder, key + ".json")
    loaded = load_cache(path)
    is_new = not loaded
    cache = loaded if loaded.get("v") == CACHE_VERSION else {}
    files = dict(cache["files"]) if isinstance(cache.get("files"), dict) else {}
    known = dict(cache["agents"]) if isinstance(cache.get("agents"), dict) else {}

    deadline = time.monotonic() + SCAN_BUDGET_SECONDS
    main, finished = scan(transcript, files.get(transcript), deadline)
    files[transcript] = main
    tokens_in, tokens_out, latest = main["tin"], main["tout"], main["max_ts"]
    for agent in subagent_transcripts(transcript, session, known):
        if time.monotonic() > deadline:
            finished = False
            break
        state, done = scan(agent, files.get(agent), deadline)
        files[agent] = state
        finished = finished and done
        tokens_in += state["tin"]
        tokens_out += state["tout"]
        # A background subagent keeps working while the main loop sits idle, so its activity counts
        # toward how long the session has run.
        latest = max(latest, state["max_ts"])
    updated = {"v": CACHE_VERSION, "files": files, "agents": known}
    if updated != loaded:  # most renders find nothing new in a quiet session
        save_cache(folder, path, updated, prune=is_new)
    if not finished:
        return None
    return {
        "turns": main["turns"],
        "solo_turns": main["solo_turns"],
        # Current run: from your last prompt to the latest activity anywhere, background subagents
        # included. Session: from the first record to that same point.
        "run_seconds": span(main["prompt_ts"], latest),
        "session_seconds": span(main["first_ts"], latest),
        "growth_last": main["glast"],
        "growth_average": main["gsum"] // main["gn"] if main["gn"] else 0,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }


# --------------------------------------------------------------------------------------------------
# Width and formatting


def char_width(character):
    if character < "\u0300":
        return 1  # everything below the combining marks is one column wide
    if unicodedata.category(character) in ("Mn", "Me", "Cf"):
        return 0
    return 2 if unicodedata.east_asian_width(character) in ("W", "F") else 1


def text_width(value):
    return len(value) if value.isascii() else sum(char_width(character) for character in value)


def visual_width(value):
    """Columns the text takes in the terminal: escape codes take none, wide characters take two."""
    return text_width(ANSI.sub("", value))


def truncate(value, width):
    """Cut coloured text to `width` columns, ending in an ellipsis."""
    if width <= 0:
        return ""
    pieces, used = [], 0
    for match in ANSI_OR_CHARACTER.finditer(value):
        piece = match.group()
        if piece.startswith("\033"):
            pieces.append(piece)
            continue
        size = char_width(piece)
        if used + size > width - 1:
            break
        pieces.append(piece)
        used += size
    return "".join(pieces) + "…" + RESET


def clip(value, limit):
    """Plain text cut to `limit` columns, ending in an ellipsis when it had to be cut."""
    if text_width(value) <= limit:
        return value
    if limit <= 0:
        return ""
    kept, used = "", 0
    for character in value:
        size = char_width(character)
        if used + size > limit - 1:
            break
        kept += character
        used += size
    return kept + "…"


def format_tokens(tokens):
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 1000:
        return f"{tokens / 1000:.0f}k"
    return str(int(tokens))


def duration(seconds, compact):
    """45s / 12m / 2h 07m (2h07m when compact)."""
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    gap = "" if compact else " "
    return f"{seconds // 3600}h{gap}{(seconds % 3600) // 60:02d}m"


def countdown(seconds, compact):
    """1h 57m / 3d 14h / 45m (1h57m, 3d14h when compact)."""
    if seconds <= 0:
        return "now"
    days, hours, minutes = seconds // 86400, (seconds % 86400) // 3600, (seconds % 3600) // 60
    gap = "" if compact else " "
    if days > 0:
        return f"{days}d{gap}{hours}h"
    if hours > 0:
        return f"{hours}h{gap}{minutes:02d}m"
    return f"{minutes}m"


def gauge(percent, cells):
    filled = min(max((percent * cells + 50) // 100, 0), cells)
    return "▓" * filled + "░" * (cells - filled)


def gauge_color(percent):
    if percent < 35:
        return GREEN
    if percent < 50:
        return YELLOW
    if percent < 65:
        return ORANGE
    return RED


def growth_color(growth):
    """Thresholds from measured data across about 30,000 turns: median 1,360, p75 2,901, p90 5,639.
    Below 1.5k is an ordinary turn and stays quiet."""
    if growth <= 1500:
        return DIM
    if growth <= 3000:
        return YELLOW
    if growth <= 6000:
        return ORANGE
    return RED


def parse_model(name):
    """("opus", "4.8") from "Claude Opus 4.8 (1M context)". The version matters: a silent fallback to an
    older model is otherwise invisible. An unknown family keeps the whole name and no version."""
    lowered = name.lower()
    family = next((known for known in MODEL_FAMILIES if known in lowered), lowered)
    match = re.search(re.escape(family) + r"[^0-9]*([0-9]+(?:\.[0-9]+)?)", lowered)
    return family, match.group(1) if match else ""


def model_color(family, version):
    """One colour per model, so a switch is visible without reading the name."""
    if family in ("fable", "mythos"):
        return "\033[38;5;213m"  # pink
    if family == "opus":
        return "\033[38;5;45m" if version.startswith("5") else "\033[38;5;33m"  # cyan, else blue
    if family == "sonnet":
        return "\033[38;5;78m" if version.startswith("5") else "\033[38;5;179m"  # green, else gold
    if family == "haiku":
        return "\033[38;5;245m"  # grey
    return DIM


# --------------------------------------------------------------------------------------------------
# Segments


class Segment:
    """One field: its priority (0 is the most important), its place in the two-line layout (line and
    group), and up to three forms, full, compact and minimal. `fit` shortens the field to a width when
    even its minimal form is too wide; without it the text is cut with an ellipsis."""

    __slots__ = ("priority", "line", "group", "forms", "widths", "fit")

    def __init__(self, priority, line, group, forms, fit=None):
        self.priority = priority
        self.line = line
        self.group = group
        self.forms = (forms,) if isinstance(forms, str) else tuple(forms)
        self.widths = tuple(visual_width(form) for form in self.forms)
        self.fit = fit

    def form(self, level):
        return self.forms[min(level, len(self.forms) - 1)]

    def has_minimal(self):
        return len(self.forms) > 2 and self.forms[2] != self.forms[1]

    def shown(self, level, width):
        """The form at `level`, or a more compact one when that is too wide; cut as a last resort."""
        for index in range(min(level, len(self.forms) - 1), len(self.forms)):
            if self.widths[index] <= width:
                return self.forms[index], self.widths[index]
        cut = self.fit(width) if self.fit else self.forms[-1]
        if visual_width(cut) > width:
            cut = truncate(cut, width)
        return cut, visual_width(cut)


def account_label(data):
    """The account, named after its config folder, when that is not the default ~/.claude."""
    folder = os.environ.get("CLAUDE_CONFIG_DIR", "")
    if not folder:
        # A transcript lives in <config>/projects/<project>/<session>.jsonl.
        projects = os.path.dirname(os.path.dirname(text(data, "transcript_path")))
        if os.path.basename(projects) != "projects":
            return ""
        folder = os.path.dirname(projects)
    normalized = os.path.normcase(os.path.abspath(os.path.expanduser(folder)))
    if normalized == os.path.normcase(os.path.abspath(os.path.expanduser(os.path.join("~", ".claude")))):
        return ""
    label = os.path.basename(folder.rstrip("/\\")).lstrip(".")
    if label.startswith("claude-"):
        label = label[len("claude-"):]
    return "" if label == "claude" else CONTROL.sub("", label)


def model_segment(data):
    name = text(data, "model", "display_name")
    if not name:
        # "claude-opus-5-5" reads as family opus, version 5.5.
        name = re.sub(r"(?<=\d)-(?=\d)", ".", text(data, "model", "id"))
    if not name:
        return None
    family, version = parse_model(name)
    shown = f"{model_color(family, version)}{family} {version}".rstrip() + RESET
    effort = text(data, "effort", "level")
    if effort:
        # Effort sits just below the model in weight: readable, not shouting.
        shown += f"{EFFORT_GREY} {EFFORTS.get(effort, effort)}{RESET}"
    return Segment(0, 0, "identity", shown)


def location_text(project, branch, worktree):
    shown = f"{BOLD}{project}{RESET}" if project else ""
    if worktree:
        shown += f"{DIM} wt:{worktree}{RESET}"
    if branch:
        shown += (" " if shown else "") + f"{MAGENTA}⎇ {branch}{RESET}"
    return shown


def location_segment(data):
    project_dir = text(data, "workspace", "project_dir")
    place = (project_dir or text(data, "workspace", "current_dir") or text(data, "cwd")).rstrip("/\\")
    project = re.split(r"[/\\]", place)[-1] if place else ""
    branch = git_branch(project_dir) or text(data, "worktree", "branch")
    if not project and not branch:
        return None
    worktree = text(data, "worktree", "name")

    def fit(width):
        # Shorten the longer name first, so both stay recognisable.
        budget = width - (3 if project and branch else 2 if branch else 0)
        project_width, branch_width = text_width(project), text_width(branch)
        project_limit = min(project_width, max(budget // 2, budget - branch_width))
        return location_text(clip(project, project_limit), clip(branch, budget - project_limit), "")

    compact = location_text(project, branch, "")
    return Segment(4, 0, "identity", (location_text(project, branch, worktree), compact, compact), fit)


def context_segment(data):
    percent = number(field(data, "context_window", "used_percentage"))
    if percent is None:
        return None
    whole = rounded(percent)
    color = gauge_color(whole)
    size = number(field(data, "context_window", "context_window_size")) or 0.0
    window = ""
    if size >= 1_000_000:
        window = f"{DIM} ({size / 1_000_000:.0f}M){RESET}"
    elif size > 0:
        window = f"{DIM} ({size / 1000:.0f}k){RESET}"
    bar = f"{color}{gauge(whole, 10)}{RESET}"
    return Segment(1, 1, "context", (
        f"{bar} {color}{BOLD}{whole:3d}%{RESET}{window}",
        f"{bar} {color}{BOLD}{whole}%{RESET}",
        f"{color}{gauge(whole, 5)}{RESET} {color}{BOLD}{whole}%{RESET}",
    ))


def five_hour_segment(data, now):
    """Dim while healthy, yellow from 50 percent, loud red from 80."""
    percent = number(field(data, "rate_limits", "five_hour", "used_percentage"))
    if percent is None:
        return None
    whole = rounded(percent)
    color = DIM if whole < 50 else YELLOW if whole < 80 else RED + BOLD
    reset = epoch_seconds(field(data, "rate_limits", "five_hour", "resets_at"))
    full = f"{DIM}5h{RESET} {color}{whole:3d}%{RESET}"
    compact = f"{DIM}5h{RESET} {color}{whole}%{RESET}"
    if reset is not None:
        full += f"{DIM} ({countdown(int(reset - now), False)}){RESET}"
        compact += f"{DIM} ({countdown(int(reset - now), True)}){RESET}"
    return Segment(2, 1, "limits", (full, compact, compact))


def seven_day_segment(data, now):
    """The weekly limit is the only field that escalates on its own, scaled by how far ahead of a linear
    pace it is: the share of the weekly budget used over the share of the week elapsed."""
    percent = number(field(data, "rate_limits", "seven_day", "used_percentage"))
    if percent is None:
        return None
    whole = rounded(percent)
    reset = epoch_seconds(field(data, "rate_limits", "seven_day", "resets_at"))
    color = DIM
    if reset is not None:
        elapsed = now - (reset - WEEK)
        if 0 < elapsed < WEEK:
            ratio = percent / (elapsed / WEEK * 100)
            # At or below 1.0 you are on pace and this stays quiet.
            color = DIM if ratio <= 1.0 else YELLOW if ratio <= 1.2 else ORANGE if ratio <= 1.5 else RED + BOLD
    if whole >= 90:
        color = RED + BOLD  # nearly out is loud regardless of pace
    full = f"{DIM}7d{RESET} {color}{whole:3d}%{RESET}"
    compact = minimal = f"{DIM}7d{RESET} {color}{whole}%{RESET}"
    if reset is not None:
        full += f"{DIM} ({countdown(int(reset - now), False)}){RESET}"
        compact += f"{DIM} ({countdown(int(reset - now), True)}){RESET}"
    return Segment(3, 1, "limits", (full, compact, minimal))


def build_segments(data, metrics, now):
    """Every segment there is data for, in the order of the two-line layout."""
    segments = []

    def add(segment):
        if segment is not None:
            segments.append(segment)

    # Identity: account, model, style, where you are, agent.
    account = account_label(data)
    if account:
        add(Segment(9, 0, "identity", f"{GREEN}◆ {account}{RESET}"))
    add(model_segment(data))
    style = text(data, "output_style", "name")
    if style and style != "default":
        add(Segment(8, 0, "identity", f"{DIM}{style}{RESET}"))
    add(location_segment(data))
    agent = text(data, "agent", "name")
    if agent:
        add(Segment(7, 0, "identity", f"{GREEN}▶ {agent}{RESET}"))

    # Money: cost, tokens in and out, time. Pure reference data, permanently dim.
    cost = number(field(data, "cost", "total_cost_usd"))
    if cost is not None:
        add(Segment(5, 0, "money", f"{DIM}${cost:.2f}{RESET}"))
    if metrics and (metrics["tokens_in"] or metrics["tokens_out"]):
        tokens = f"{format_tokens(metrics['tokens_in'])}↑ {format_tokens(metrics['tokens_out'])}↓"
        add(Segment(5, 0, "money", f"{DIM}{tokens}{RESET}"))
    if metrics and metrics["session_seconds"] > 0:
        # Whole session first, current run in brackets; both include background subagent activity.
        session, run = metrics["session_seconds"], metrics["run_seconds"]
        with_run = 0 < run < session
        full, compact = duration(session, False), duration(session, True)
        if with_run:
            full += f" ({duration(run, False)})"
            compact += f" ({duration(run, True)})"
        add(Segment(6, 0, "money", (f"{DIM}{full}{RESET}", f"{DIM}{compact}{RESET}",
                                    f"{DIM}{duration(session, True)}{RESET}")))

    # Context: gauge, turns, growth.
    add(context_segment(data))
    if metrics and metrics["turns"] > 0:
        # The turn total, and in brackets the turns since your last prompt.
        turns, solo = metrics["turns"], metrics["solo_turns"]
        full = f"turn {turns:>3}" + (f" ({solo:>2})" if solo > 0 else "")
        compact = f"turn {turns}" + (f" ({solo})" if solo > 0 else "")
        add(Segment(5, 1, "context", (f"{DIM}{full}{RESET}", f"{DIM}{compact}{RESET}",
                                      f"{DIM}turn {turns}{RESET}")))
    if metrics and metrics["growth_last"] > 0:
        # The last turn's growth, with the session average in brackets for comparison.
        last, average = metrics["growth_last"], metrics["growth_average"]
        color = growth_color(last)
        label = f"{DIM}/turn{RESET}"
        tail = f"{DIM} ({format_tokens(average)}){RESET}" if average > 0 else ""
        add(Segment(6, 1, "context", (
            f"{color}↑{format_tokens(last):>4}{RESET}{label}{tail}",
            f"{color}↑{format_tokens(last)}{RESET}{label}{tail}",
            f"{color}↑{format_tokens(last)}{RESET}{label}",
        )))

    # Limits: 5-hour and 7-day usage.
    add(five_hour_segment(data, now))
    add(seven_day_segment(data, now))
    return segments


# --------------------------------------------------------------------------------------------------
# Layout


def two_lines(segments, level, width):
    """identity | money over context | limits, all at one level; None when a line does not fit."""
    lines = []
    for line_index in (0, 1):
        shown, previous = "", None
        for segment in segments:
            if segment.line != line_index:
                continue
            if shown:
                shown += PIPE if segment.group != previous else DOT
            shown += segment.form(level)
            previous = segment.group
        if not shown:
            continue
        if visual_width(shown) > width:
            return None
        lines.append(shown)
    return lines


def pack(segments, levels, width):
    """Segments in order, broken into the fewest lines that hold them and, among those, the most even
    ones (the free columns of every line but the last, squared and summed, as small as possible), so a
    line is not left holding one stray field. best[start] is (line count, cost, next break) of the best
    layout of the segments from start on, filled in from the end."""
    shown = [segment.shown(level, width) for segment, level in zip(segments, levels)]
    count = len(shown)
    best = [None] * count + [(0, 0, count)]
    for start in reversed(range(count)):
        used = -SEPARATOR_WIDTH
        for end in range(start + 1, count + 1):
            used += SEPARATOR_WIDTH + shown[end - 1][1]
            if used > width and end > start + 1:
                break
            lines, cost, _ = best[end]
            slack = (width - used) ** 2 if end < count else 0
            candidate = (lines + 1, cost + slack, end)
            if best[start] is None or candidate[:2] < best[start][:2]:
                best[start] = candidate
    lines, start = [], 0
    while start < count:
        end = best[start][2]
        lines.append(DOT.join(text for text, _ in shown[start:end]))
        start = end
    return lines


def arrange(segments, width):
    for level in (0, 1):
        lines = two_lines(segments, level, width)
        if lines is not None:
            return lines
    ordered = sorted(segments, key=lambda segment: segment.priority)  # stable: layout order within a tie
    levels = [1] * len(ordered)
    lines = pack(ordered, levels, width)
    # Too many lines: the least important segments switch to their minimal forms first...
    for index in reversed(range(len(ordered))):
        if len(lines) <= MAX_LINES:
            break
        if ordered[index].has_minimal():
            levels[index] = 2
            lines = pack(ordered, levels, width)
    # ...and only then are left out, least important first, never the essential ones.
    while len(lines) > MAX_LINES and ordered and ordered[-1].priority > LAST_ESSENTIAL:
        ordered.pop()
        levels.pop()
        lines = pack(ordered, levels, width)
    # Most important first, take the compact form back wherever that costs no extra line.
    for index in range(len(ordered)):
        if levels[index] == 2:
            levels[index] = 1
            trial = pack(ordered, levels, width)
            if len(trial) <= len(lines):
                lines = trial
            else:
                levels[index] = 2
    return lines[:MAX_LINES]


def render(data, columns, now):
    try:
        metrics = session_metrics(data)
    except Exception as error:
        # The transcript metrics are extras: whatever breaks them, the rest of the status line still shows.
        report("reading the transcript", error)
        metrics = None
    segments = build_segments(data, metrics, now)
    return "\n".join(arrange(segments, max(columns - FOOTER_PADDING, MIN_WIDTH)))


# --------------------------------------------------------------------------------------------------
# Running


def report(where, error):
    """One line on stderr naming what failed. Claude Code does not show a status line's stderr, so this
    costs the user nothing, and it makes a failure diagnosable when the script is run by hand."""
    try:
        sys.stderr.write(f"statusline: {where}: {type(error).__name__}: {error}\n")
    except (OSError, ValueError):
        # stderr itself is closed or unusable, so there is nowhere left to report to.
        return


def emit(value):
    encoded = value.encode("utf-8", "replace")
    try:
        sys.stdout.buffer.write(encoded)
        sys.stdout.flush()
    except AttributeError:
        sys.stdout.write(value)
        sys.stdout.flush()
    except OSError as error:
        # Claude Code stopped reading (a newer refresh replaced this one); only stderr is left.
        report("writing the status line", error)


def main():
    data = {}
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        parsed = json.loads(raw) if raw.strip() else {}
        if isinstance(parsed, dict):
            data = parsed
    except (OSError, ValueError, AttributeError) as error:
        # Unreadable or malformed input still gets a (short) status line from what is known.
        report("reading the status line JSON", error)
        data = {}
    try:
        output = render(data, terminal_columns(), time.time())
    except Exception as error:
        # Degrade to the model name alone rather than show a traceback in the status line.
        report("rendering", error)
        output = text(data, "model", "display_name")
    emit(output)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Last line of defence: whatever went wrong, a status line prints nothing rather than a
        # traceback, and exits 0 so Claude Code keeps calling it.
        report("unexpected failure", error)
    sys.exit(0)
