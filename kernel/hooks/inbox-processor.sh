#!/usr/bin/env bash
# inbox-processor.sh
# Hook for PostToolUse on Edit|Write events.
# When a markdown or text file lands in a `docs/inbox/` directory (anywhere
# in a project), dispatches a summarization call to the Anthropic API and
# writes the extracted knowledge to `docs/knowledge-base/drafts/`.
#
# Original file is moved to `docs/inbox/done/` after successful extraction.
#
# Configuration (read from ~/.claude/.env):
#   ANTHROPIC_API_KEY  — required. Without it, this hook is a silent no-op.
#   ANTHROPIC_MODEL    — optional, defaults to claude-haiku-4-5-20251001
#
# Limitations:
# - Only processes .md and .txt files. PDFs/binaries need separate tooling.
# - Truncates input to 50,000 chars to bound cost.
# - Does NOT fire for files dropped manually outside Claude (only for files
#   created/edited via Claude's Edit or Write tools).
#
# To disable: comment out this hook in ~/.claude/settings.json
#             or remove ANTHROPIC_API_KEY from ~/.claude/.env.

set -euo pipefail

# --- Source credentials from user-level env file ---
[ -f "$HOME/.claude/.env" ] && { set -a; . "$HOME/.claude/.env"; set +a; }

ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-claude-haiku-4-5-20251001}"
MAX_INPUT_CHARS=50000

# --- Parse hook input from stdin ---
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# --- Guard clauses ---
[ -z "$FILE_PATH" ] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

# Only act on files inside a `docs/inbox/` directory (but not in inbox/done/)
case "$FILE_PATH" in
  */docs/inbox/done/*) exit 0 ;;
  */docs/inbox/*) ;;
  *) exit 0 ;;
esac

# Only process .md and .txt files
case "$FILE_PATH" in
  *.md|*.txt) ;;
  *) exit 0 ;;
esac

# --- API key required; silent no-op if missing ---
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  exit 0
fi

# --- Resolve project root and target paths ---
INBOX_DIR=$(dirname "$FILE_PATH")
PROJECT_DOCS_DIR=$(dirname "$INBOX_DIR")
PROJECT_DIR=$(dirname "$PROJECT_DOCS_DIR")
DRAFTS_DIR="$PROJECT_DOCS_DIR/knowledge-base/drafts"
DONE_DIR="$INBOX_DIR/done"
mkdir -p "$DRAFTS_DIR" "$DONE_DIR"

ORIG_NAME=$(basename "$FILE_PATH")
BASENAME="${ORIG_NAME%.*}"
DATE=$(date +%Y-%m-%d)
DRAFT_FILE="$DRAFTS_DIR/${BASENAME}-extract-${DATE}.md"
LOG_FILE="$PROJECT_DIR/log.md"

# --- Background processing; never block the user ---
(
  CONTENT=$(head -c "$MAX_INPUT_CHARS" "$FILE_PATH")
  CONTENT_JSON=$(printf '%s' "$CONTENT" | jq -Rs .)
  SYSTEM_PROMPT='You extract reusable knowledge from inbox documents into clean markdown for a knowledge base. Output: a structured markdown summary with a brief overview, key facts, decisions/commitments, action items, and any notable quotes (with attribution if visible). Be specific. Preserve names, dates, numbers verbatim. Mark uncertain interpretations with [?].'
  SYSTEM_JSON=$(printf '%s' "$SYSTEM_PROMPT" | jq -Rs .)

  REQUEST_BODY=$(jq -n \
    --arg model "$ANTHROPIC_MODEL" \
    --argjson system "$SYSTEM_JSON" \
    --argjson content "$CONTENT_JSON" \
    '{
      model: $model,
      max_tokens: 4096,
      system: $system,
      messages: [{role: "user", content: $content}]
    }')

  RESPONSE=$(curl -sS https://api.anthropic.com/v1/messages \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d "$REQUEST_BODY" 2>&1)

  TEXT=$(echo "$RESPONSE" | jq -r '.content[]? | select(.type == "text") | .text' 2>/dev/null || true)

  if [ -z "$TEXT" ]; then
    # Failure: don't move original, write error draft so user knows
    {
      echo "# [Failed extraction] $ORIG_NAME"
      echo ""
      echo "**Date:** $DATE"
      echo "**Source:** \`$FILE_PATH\`"
      echo ""
      echo "Inbox processing failed. API response:"
      echo ""
      echo '```'
      echo "$RESPONSE" | head -c 2000
      echo '```'
    } > "$DRAFT_FILE"
    exit 0
  fi

  # Success: write draft, move original to done/, append to log
  {
    echo "# Extract: $ORIG_NAME"
    echo ""
    echo "**Date:** $DATE"
    echo "**Source:** \`$FILE_PATH\`"
    echo "**Model:** $ANTHROPIC_MODEL"
    echo ""
    echo "> Status: DRAFT — review and promote to \`knowledge-base/\` if useful."
    echo ""
    echo "---"
    echo ""
    echo "$TEXT"
  } > "$DRAFT_FILE"

  mv "$FILE_PATH" "$DONE_DIR/$ORIG_NAME"

  if [ -f "$LOG_FILE" ]; then
    {
      echo ""
      echo "## $(date '+%Y-%m-%d %H:%M') — inbox-processor"
      echo "- Processed: \`$ORIG_NAME\`"
      echo "- Draft: \`$DRAFT_FILE\`"
      echo "- Original moved to: \`$DONE_DIR/$ORIG_NAME\`"
    } >> "$LOG_FILE"
  fi
) > /dev/null 2>&1 &

exit 0
