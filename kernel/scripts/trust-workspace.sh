#!/usr/bin/env bash
# trust-workspace.sh - pre-approve directories for Claude Code's workspace-trust gate.
#
# WHY THIS EXISTS
# On first launch in a directory, Claude Code shows the "Do you trust the files in
# this folder?" dialog. There is NO settings.json key and no safe/documented env var
# to turn this off (verified against the current settings schema; Anthropic has the
# feature request open but unimplemented). The ONLY supported mechanism is the
# per-directory flag inside ~/.claude.json. This script merges that flag in safely.
#
# It does NOT touch normal permission prompting and does NOT enable bypass mode.
# The safety baseline (disableBypassPermissionsMode: "disable") stays fully intact -
# this only says "I trust files in directories I deliberately listed", which is the
# same thing as clicking "Yes" in the dialog, just persisted up front.
#
# USAGE
#   trust-workspace.sh <dir> [<dir> ...]   # trust specific directories
#   trust-workspace.sh --all               # trust every directory Claude already knows
#
# CAVEAT (important)
# Run this with NO Claude Code session open against this ~/.claude.json, or the
# running session may overwrite the change when it exits. If the trust prompt comes
# back, close all sessions and run the command once more from a plain terminal.

set -euo pipefail

CONFIG="$HOME/.claude.json"
[ -f "$CONFIG" ] || { echo "No $CONFIG found - start Claude Code once first."; exit 1; }

if pgrep -x claude >/dev/null 2>&1; then
  echo "WARNING: a 'claude' process is running. It may overwrite this change on exit."
  echo "         Close all Claude Code sessions, then re-run if the prompt returns."
fi

BACKUP="$CONFIG.bak.$(date +%Y%m%d-%H%M%S)"
cp "$CONFIG" "$BACKUP"
echo "Backed up to $BACKUP"

TMP="$(mktemp)"
trap 'rm -f "$TMP" "$TMP.next"' EXIT

if [ "${1:-}" = "--all" ]; then
  jq '
    .projects |= with_entries(
      .value.hasTrustDialogAccepted = true
      | .value.hasTrustDialogHooksAccepted = true
    )
  ' "$CONFIG" > "$TMP"
  echo "Trusted ALL known project directories."
else
  [ "$#" -ge 1 ] || { echo "Usage: trust-workspace.sh <dir> [<dir> ...] | --all"; exit 1; }
  cp "$CONFIG" "$TMP"
  for d in "$@"; do
    abs="$(cd "$d" 2>/dev/null && pwd || echo "$d")"
    jq --arg d "$abs" '
      .projects[$d] = ((.projects[$d] // {})
        + {hasTrustDialogAccepted: true, hasTrustDialogHooksAccepted: true})
    ' "$TMP" > "$TMP.next" && mv "$TMP.next" "$TMP"
    echo "Trusted: $abs"
  done
fi

jq -e . "$TMP" >/dev/null || { echo "ERROR: produced invalid JSON, aborting."; exit 1; }
mv "$TMP" "$CONFIG"
echo "Done. Restart Claude Code; the folder-trust prompt should no longer appear for these directories."
