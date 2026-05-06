#!/usr/bin/env bash
# Lists NAMES of credential/API env variables from multiple sources.
# NEVER returns values — only names. Safe to share with Claude.
#
# Sources scanned (names only, values never read):
#   1. Process environment (vars exported in current shell)
#   2. ~/.claude/.env  (user-level Claude Code env file)
#   3. ./.env          (project-level env file in current directory)
#
# Auto-detects credential vars without needing updates: matches common
# credential keywords (KEY, TOKEN, SECRET, etc.) and known service prefixes.
#
# Usage:
#   list-env-keys.sh              # default credential pattern across all sources
#   list-env-keys.sh GEMINI       # filter by substring (case-insensitive)
#   list-env-keys.sh '.*'         # ALL env var names (noisy)
#   list-env-keys.sh '_KEY$'      # custom regex
#
# Exit codes:
#   0 = success (matches found or empty result)
#   1 = invalid input

set -euo pipefail

DEFAULT_INCLUDE='API|KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|CLIENT_ID|CLIENT_SECRET|DSN|CONNECTION_STRING|BUCKET|ACCOUNT_ID|PROJECT_ID|TENANT_ID|SUBSCRIPTION_ID|SERVICE_ACCOUNT|PRIVATE_KEY|ACCESS_KEY|REFRESH_TOKEN|SESSION_TOKEN|WEBHOOK|SIGNING|HMAC|SALT|^OPENAI_|^ANTHROPIC_|^GEMINI_|^GROQ_|^MISTRAL_|^TOGETHER_|^XAI_|^DEEPSEEK_|^STRIPE_|^TWILIO_|^SENDGRID_|^MAILGUN_|^GITHUB_TOKEN|^GITLAB_TOKEN|^DATABASE_URL|^SUPABASE_|^FIREBASE_|^AWS_|^AZURE_|^GCP_'

# Known non-credential env vars that match the include pattern but aren't actual credentials
EXCLUDE='^PWD$|^OLDPWD$|^XPC_|^TMPDIR$|^TERM_PROGRAM|^DISPLAY$|^LSCOLORS$|^LS_COLORS$'

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
    # Source 1: process environment
    env | cut -d= -f1

    # Source 2: ~/.claude/.env (user-level Claude env)
    extract_names_from_envfile "$HOME/.claude/.env"

    # Source 3: ./.env (project-level env in cwd)
    extract_names_from_envfile "./.env"
} | grep -iE "$PATTERN" | grep -ivE "$EXCLUDE" | sort -u
