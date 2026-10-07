#!/bin/sh
# python-launcher.sh - runs one of this folder's Python scripts under Python 3.9 or newer, the same
# way on macOS, Linux and Windows (Git Bash), so settings.json names one command for every system.
#
# Usage:  sh ~/.claude/scripts/python-launcher.sh MODE SCRIPT [ARGS...]
#   MODE guard   a safety hook. With no usable Python, or when the hook fails to load or crashes, it
#                blocks the tool call (exit 2) and says why: Claude Code lets a call through on every
#                exit code except 2, so a safety check that cannot run would otherwise wave
#                everything through. The hook's own deliberate exit codes pass through unchanged.
#   MODE quiet   the status line. With no usable Python it prints nothing and exits 0.
#   MODE plain   a helper run by Claude or by hand. With no usable Python it says so and exits 1.
#   SCRIPT       a file name in this folder, for example bash-safety-extended.py.
#
# Why a launcher. `python3` is missing on most Windows machines, or is a Microsoft Store placeholder
# that only prints an install hint; `python` is still Python 2 on some old systems; /usr/bin/python3
# on a Mac without the Command Line Tools opens an install dialog instead of running.
#
# How a candidate is judged without starting Python twice. Candidates are tried in order (Windows:
# py -3, python, python3; elsewhere: python3, python). Each runs python-launcher.py, which exits 86 on a
# Python older than 3.9 and otherwise runs SCRIPT and adds 200 to its exit code (255 when SCRIPT failed
# to load or crashed, see crashed below). So an exit code of 200 or more proves the script really ran
# under a usable Python; 128-199 means it was killed while running
# (nothing is retried, because it may already have read its input); anything else means "this
# candidate is unusable, try the next". An unusable candidate never reads stdin, so the next one still
# gets the hook's input. POSIX sh only, and no subshells: on Windows every extra process costs time.

mode=${1:-}
script=${2:-}
[ $# -ge 2 ] && shift 2

case $0 in
  */*) here=${0%/*} ;;
  *) here=. ;;
esac
entry=$here/python-launcher.py
tried=

on_windows=
[ "${OS:-}" = Windows_NT ] && on_windows=1

fix_hint() {
  if [ -n "$on_windows" ]; then
    echo "Fix: install Python from https://www.python.org/downloads/ (tick \"Add python.exe to PATH\"), then open a new terminal and restart Claude Code."
  elif [ -x /usr/bin/xcode-select ]; then
    echo "Fix: run \`xcode-select --install\` in Terminal (or install Python from https://www.python.org/downloads/), then restart Claude Code."
  else
    echo "Fix: install python3 with the package manager (for example \`sudo apt install python3\`), then restart Claude Code."
  fi
}

give_up() {   # $1 = what went wrong; $tried is set once a Python was looked for
  case $mode in
    guard)
      {
        echo "BLOCKED by the safety layer: $1, so the safety check $script could not run, and an action it cannot check is not let through."
        if [ -n "$tried" ]; then
          echo "Tried:$tried"
          fix_hint
          echo "Tell the user that Python 3.9 or newer is needed. Do not try to run this action another way."
        else
          echo "Tell the user that the safety layer's installation needs repair. Do not try to run this action another way."
        fi
      } >&2
      exit 2 ;;
    quiet)
      exit 0 ;;
    *)
      {
        echo "python-launcher: $1, so $script could not run."
        [ -n "$tried" ] && echo "Tried:$tried" && fix_hint
      } >&2
      exit 1 ;;
  esac
}

crashed() {   # python-launcher.py exit 255: the script failed to load or stopped on an unhandled error
  if [ "$mode" = guard ]; then
    echo "BLOCKED by the safety layer: the safety check $script stopped with an error (shown above), so this action was not checked and is not let through. Tell the user that the safety layer needs repair. Do not try to run this action another way." >&2
    exit 2
  fi
  exit 1
}

case $mode in
  guard|quiet|plain) ;;
  *) mode=plain; give_up "usage is python-launcher.sh guard|quiet|plain SCRIPT [ARGS...]" ;;
esac
case $script in
  ''|*/*) give_up "the script must be a file name in $here" ;;
esac
[ -f "$here/$script" ] || give_up "$here/$script is missing"
[ -f "$entry" ] || give_up "$entry is missing"

# The first $1 on PATH, without starting a process (a $(command -v) subshell is a fork).
first_on_path() {
  found=
  saved_ifs=$IFS
  IFS=:
  for dir in $PATH; do
    if [ -x "${dir:-.}/$1" ]; then
      found=${dir:-.}/$1
      break
    fi
  done
  IFS=$saved_ifs
}

# A Mac without the Command Line Tools (and without Xcode) has only a placeholder /usr/bin/python3
# that pops up an install dialog on every call. Skip it there instead of nagging on every hook.
mac_placeholder() {
  [ "$1" = python3 ] && [ -x /usr/bin/xcode-select ] || return 1
  first_on_path python3
  [ "$found" = /usr/bin/python3 ] || return 1
  [ -x /Library/Developer/CommandLineTools/usr/bin/python3 ] && return 1
  for app in /Applications/Xcode*.app; do
    [ -d "$app" ] && return 1
  done
  return 0
}

if [ -n "$on_windows" ]; then
  candidates="py python python3"
else
  candidates="python3 python"
fi

for candidate in $candidates; do
  if ! command -v "$candidate" >/dev/null 2>&1; then
    tried="$tried $candidate (not found);"
    continue
  fi
  if mac_placeholder "$candidate"; then
    tried="$tried $candidate (macOS placeholder, Command Line Tools not installed);"
    continue
  fi
  if [ "$candidate" = py ]; then
    py -3 -E -s "$entry" "$script" "$@"
  else
    "$candidate" -E -s "$entry" "$script" "$@"
  fi
  rc=$?
  if [ "$rc" -ge 200 ]; then
    [ "$rc" -eq 255 ] && crashed
    exit $((rc - 200))
  fi
  if [ "$rc" -ge 128 ]; then
    tried="$tried $candidate (stopped by signal $((rc - 128)) while running);"
    give_up "the Python running it was stopped"
  fi
  if [ "$rc" -eq 86 ]; then
    tried="$tried $candidate (older than 3.9);"
  else
    tried="$tried $candidate (did not run, exit $rc);"
  fi
done

give_up "no working Python 3.9 or newer was found"
