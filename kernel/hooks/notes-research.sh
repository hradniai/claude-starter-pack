#!/usr/bin/env bash
# notes-research.sh
# Hook for PostToolUse on Edit|Write events.
# When a notes.md file is edited and the latest entry contains "→ research",
# dispatches a research call to the Anthropic API in the background.
#
# Configuration (read from ~/.claude/.env):
#   ANTHROPIC_API_KEY  — required. Without it, this hook is a silent no-op.
#   ANTHROPIC_MODEL    — optional, defaults to claude-haiku-4-5-20251001
#
# Output: {project}/research/{topic-slug}-research-{YYYY-MM-DD}.md
# notes.md is appended with a reference to the research output file.
#
# To disable: comment out this hook in ~/.claude/settings.json
#             or remove ANTHROPIC_API_KEY from ~/.claude/.env.

set -euo pipefail

# --- Source credentials from user-level env file ---
[ -f "$HOME/.claude/.env" ] && { set -a; . "$HOME/.claude/.env"; set +a; }

ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-claude-haiku-4-5-20251001}"

# --- Parse hook input from stdin ---
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# --- Guard clauses: only act on notes.md files that exist ---
[ -z "$FILE_PATH" ] && exit 0
[ "$(basename "$FILE_PATH")" != "notes.md" ] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

# --- Extract latest entry: text after the last `## YYYY-MM-DD HH:MM` header ---
LAST_ENTRY=$(awk '
  /^## [0-9]{4}-[0-9]{2}-[0-9]{2}/ { entry = $0; next }
  { entry = entry "\n" $0 }
  END { print entry }
' "$FILE_PATH")

# --- Only proceed if the marker is present in the latest entry ---
echo "$LAST_ENTRY" | grep -q "→ research" || exit 0

# --- API key required; silent no-op if missing ---
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  exit 0
fi

# --- Generate output filename ---
PROJECT_DIR=$(dirname "$FILE_PATH")
RESEARCH_DIR="$PROJECT_DIR/research"
mkdir -p "$RESEARCH_DIR"

SLUG=$(echo "$LAST_ENTRY" | grep -v '^## ' | grep -v '^$' | head -1 \
       | tr -cd 'a-zA-Z0-9 ' | tr ' ' '-' | tr '[:upper:]' '[:lower:]' \
       | cut -c1-50 | sed 's/^-*//;s/-*$//')
SLUG=${SLUG:-note}
DATE=$(date +%Y-%m-%d)
OUTPUT_FILE="$RESEARCH_DIR/${SLUG}-research-${DATE}.md"

# --- Append marker to notes.md immediately so the user sees status ---
{
  echo ""
  echo "  → research dispatched at $(date '+%H:%M'); output: \`$OUTPUT_FILE\`"
} >> "$FILE_PATH"

# --- Background API call; never block the user's edit ---
(
  PROMPT_JSON=$(printf '%s' "$LAST_ENTRY" | jq -Rs .)
  SYSTEM_PROMPT='You are a research assistant. Conduct thorough research on the topic and produce a comprehensive markdown report. Lead with a brief verdict, then detailed findings. Cite specific sources where possible. Be specific, anti-hype, and explicit about uncertainty. Acknowledge what you do not know rather than fabricate.'
  SYSTEM_JSON=$(printf '%s' "$SYSTEM_PROMPT" | jq -Rs .)

  REQUEST_BODY=$(jq -n \
    --arg model "$ANTHROPIC_MODEL" \
    --argjson system "$SYSTEM_JSON" \
    --argjson prompt "$PROMPT_JSON" \
    '{
      model: $model,
      max_tokens: 4096,
      system: $system,
      messages: [{role: "user", content: $prompt}]
    }')

  RESPONSE=$(curl -sS https://api.anthropic.com/v1/messages \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d "$REQUEST_BODY" 2>&1)

  TEXT=$(echo "$RESPONSE" | jq -r '.content[]? | select(.type == "text") | .text' 2>/dev/null || true)

  if [ -z "$TEXT" ]; then
    {
      echo "# Research dispatch failed"
      echo ""
      echo "**Date:** $DATE"
      echo "**Model:** $ANTHROPIC_MODEL"
      echo ""
      echo "## Source note"
      echo ""
      echo "$LAST_ENTRY"
      echo ""
      echo "## API response (raw — could not parse text content)"
      echo ""
      echo '```'
      echo "$RESPONSE"
      echo '```'
    } > "$OUTPUT_FILE"
  else
    {
      echo "# ${SLUG//-/ }"
      echo ""
      echo "**Date:** $DATE"
      echo "**Triggered by:** \`notes.md\` entry with \`→ research\` marker"
      echo "**Model:** $ANTHROPIC_MODEL"
      echo ""
      echo "---"
      echo ""
      echo "## Source note"
      echo ""
      echo "$LAST_ENTRY"
      echo ""
      echo "---"
      echo ""
      echo "## Research"
      echo ""
      echo "$TEXT"
    } > "$OUTPUT_FILE"
  fi
) > /dev/null 2>&1 &

exit 0
