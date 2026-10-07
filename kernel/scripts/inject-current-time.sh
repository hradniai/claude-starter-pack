#!/usr/bin/env bash
# inject-current-time.sh - UserPromptSubmit hook.
#
# Claude Code's harness auto-injects today's date (`# currentDate`) into
# context but does NOT inject the current time. Without it, Claude tends
# to guess, often wrongly - visible as wrong timestamps in journals and
# other dated files.
#
# This hook fills the gap by adding the current local time to context on
# every user prompt. Token cost: ~20 tokens per turn. `date` format flags
# used here are POSIX, so GNU (Linux) and BSD (macOS) date agree.

set -uo pipefail

CURRENT_TIME=$(date '+%Y-%m-%d %H:%M')

cat <<JSON
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Current local time: $CURRENT_TIME (use this for timestamps in worklogs and other dated files)"
  }
}
JSON
