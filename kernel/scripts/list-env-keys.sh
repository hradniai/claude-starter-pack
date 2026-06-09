#!/usr/bin/env bash
# Lists NAMES of credential/API env variables from multiple sources.
# NEVER returns values — only names. Safe to share with Claude.
#
# Default sources scanned (names only, values never read):
#   1. Process environment (vars exported in current shell)
#   2. ~/.claude/.env  (user-level Claude Code env file)
#   3. ./.env          (project-level env file in current directory)
#
# Or scan a SINGLE specific file via --from <path> (skips all default sources).
#
# Auto-detects credential vars without needing updates: matches common
# credential keywords (KEY, TOKEN, SECRET, etc.) and known service prefixes.
#
# Usage:
#   list-env-keys.sh                              # default sources, credential pattern
#   list-env-keys.sh GEMINI                       # filter by substring (case-insensitive)
#   list-env-keys.sh '.*'                         # ALL env var names (noisy)
#   list-env-keys.sh '_KEY$'                      # custom regex
#   list-env-keys.sh --from /path/to/.env         # scan ONLY that file
#   list-env-keys.sh --from /path/to/.env GEMINI  # scan that file + filter
#
# Exit codes:
#   0 = success (matches found or empty result)
#   1 = invalid input

set -euo pipefail

DEFAULT_INCLUDE='API|KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|CLIENT_ID|CLIENT_SECRET|DSN|CONNECTION_STRING|BUCKET|ACCOUNT_ID|PROJECT_ID|TENANT_ID|SUBSCRIPTION_ID|SERVICE_ACCOUNT|PRIVATE_KEY|ACCESS_KEY|REFRESH_TOKEN|SESSION_TOKEN|WEBHOOK|SIGNING|HMAC|SALT|^OPENAI_|^ANTHROPIC_|^GEMINI_|^GROQ_|^MISTRAL_|^TOGETHER_|^XAI_|^DEEPSEEK_|^STRIPE_|^TWILIO_|^SENDGRID_|^MAILGUN_|^GITHUB_TOKEN|^GITLAB_TOKEN|^DATABASE_URL|^SUPABASE_|^FIREBASE_|^AWS_|^AZURE_|^GCP_'

# Known non-credential env vars that match the include pattern but aren't actual credentials
EXCLUDE='^PWD$|^OLDPWD$|^XPC_|^TMPDIR$|^TERM_PROGRAM|^DISPLAY$|^LSCOLORS$|^LS_COLORS$'

# Parse --from flag (consumes 2 args if present) before pattern arg
TARGET_FILE=""
if [ "${1:-}" = "--from" ] || [ "${1:-}" = "-f" ]; then
    if [ -z "${2:-}" ]; then
        echo "Error: --from requires a path argument" >&2
        exit 1
    fi
    TARGET_FILE="$2"
    shift 2
    if [ ! -f "$TARGET_FILE" ]; then
        echo "Error: file not found: $TARGET_FILE" >&2
        exit 1
    fi
fi

PATTERN="${1:-$DEFAULT_INCLUDE}"

# Extract variable names (LHS of =) from an env-style file; never reads values.
extract_names_from_envfile() {
    local file="$1"
    [ -f "$file" ] || return 0
    # Match lines like: NAME=value or export NAME=value
    # Output only the NAME part. Skips comments and blanks.
    grep -E '^(export[[:space:]]+)?[A-Z][A-Z0-9_]*=' "$file" 2>/dev/null \
        | sed -E 's/^(export[[:space:]]+)?([A-Z][A-Z0-9_]*)=.*/\2/'
}

{
    if [ -n "$TARGET_FILE" ]; then
        # Single-file mode: scan only the requested file
        extract_names_from_envfile "$TARGET_FILE"
    else
        # Default mode: process env + ~/.claude/.env + ./.env
        env | cut -d= -f1
        extract_names_from_envfile "$HOME/.claude/.env"
        extract_names_from_envfile "./.env"
    fi
} | grep -iE "$PATTERN" | grep -ivE "$EXCLUDE" | sort -u
