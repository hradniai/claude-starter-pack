#!/usr/bin/env bash
# Lists NAMES of credential/API env variables from multiple sources.
# NEVER returns values - only names. Safe to share with Claude.
#
# Default sources scanned (names only; no value text is ever printed):
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

# Python runs through python-launcher.sh, which finds Python 3.9+ on macOS, Linux and Windows (Git Bash),
# where `python3` may be missing or a Microsoft Store placeholder.
HERE="$(dirname "$0")"

DEFAULT_INCLUDE='API|KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|CLIENT_ID|CLIENT_SECRET|DSN|CONNECTION_STRING|BUCKET|ACCOUNT_ID|PROJECT_ID|TENANT_ID|SUBSCRIPTION_ID|SERVICE_ACCOUNT|PRIVATE_KEY|ACCESS_KEY|REFRESH_TOKEN|SESSION_TOKEN|WEBHOOK|SIGNING|HMAC|SALT|^OPENAI_|^ANTHROPIC_|^GEMINI_|^GROQ_|^MISTRAL_|^TOGETHER_|^XAI_|^DEEPSEEK_|^STRIPE_|^TWILIO_|^SENDGRID_|^MAILGUN_|^GITHUB_TOKEN|^GITLAB_TOKEN|^DATABASE_URL|^SUPABASE_|^FIREBASE_|^AWS_|^AZURE_|^GCP_|(^|_)PAT($|_)|(^|_)ICAL($|_)|GITHUB|^GH_'

# Known non-credential env vars that match the include pattern but aren't actual credentials
EXCLUDE='^PWD$|^OLDPWD$|^XPC_|^TMPDIR$|^TERM_PROGRAM|^DISPLAY$|^LSCOLORS$|^LS_COLORS$'

# Parse leading flags: --from <path> / -f <path> and --classify / -c, in any order,
# before the optional pattern arg.
TARGET_FILE=""
CLASSIFY=0
while [ $# -gt 0 ]; do
    case "${1:-}" in
        --from|-f)
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
            ;;
        --classify|-c)
            CLASSIFY=1
            shift
            ;;
        *)
            break
            ;;
    esac
done

PATTERN="${1:-$DEFAULT_INCLUDE}"

# Classify mode: delegate to the Python classifier, which reports each key's
# value-STATE (empty / placeholder / filled + kind) WITHOUT ever emitting the value.
# Names-only mode (default, below) is unchanged.
if [ "$CLASSIFY" = "1" ]; then
    CLASSIFY_FILE="${TARGET_FILE:-./.env}"
    if [ ! -f "$CLASSIFY_FILE" ]; then
        echo "Error: file not found: $CLASSIFY_FILE" >&2
        exit 1
    fi
    exec sh "$HERE/python-launcher.sh" plain env-key-classify.py "$CLASSIFY_FILE" "$PATTERN"
fi

# Extract variable NAMES from an env-style file. Parsing is quote-aware (env-key-classify.py
# --names): a quoted value may span lines, and those lines are never mistaken for names, so no
# fragment of a multi-line value (a PEM key, a JSON blob) can reach the output.
extract_names_from_envfile() {
    local file="$1"
    [ -f "$file" ] || return 0
    sh "$HERE/python-launcher.sh" plain env-key-classify.py --names "$file"
}

{
    if [ -n "$TARGET_FILE" ]; then
        # Single-file mode: scan only the requested file
        extract_names_from_envfile "$TARGET_FILE"
    else
        # Default mode: process env + ~/.claude/.env + ./.env
        # compgen -e lists exported names only; `env | cut` would turn lines of a multi-line value into names
        compgen -e
        extract_names_from_envfile "$HOME/.claude/.env"
        extract_names_from_envfile "./.env"
    fi
} | { grep -iE -e "$PATTERN" || [ $? -eq 1 ]; } | { grep -ivE -e "$EXCLUDE" || [ $? -eq 1 ]; } | sort -u
