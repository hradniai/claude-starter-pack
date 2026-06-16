#!/usr/bin/env python3
"""
Classify the VALUE-STATE of each variable in an env file WITHOUT ever emitting the value.

Output, one line per matching key:   NAME: <state>[ (<kind>)]
  state = empty | placeholder | filled
  kind  = (only when filled) api_key | jwt | private_key | connection_string |
          webhook_url | email | password | client_id | client_secret | token | other

HARD INVARIANT: the value is read ONLY to classify it. It is NEVER printed, logged,
or returned. Only the NAME and the derived label leave this script. This is the same
contract as list-env-keys.sh (which lists names only); this companion adds the state.

Heuristic classifier - occasional false positives/negatives are expected and tolerated.
Signatures sourced from gitleaks / detect-secrets / trufflehog (see
research/config-files-and-env-handling-research-2026-06-16.md in _AIOS).

Usage:
  env-key-classify.py <file> [name-filter-regex]
"""
import sys
import re
import math
from collections import Counter

# --- Provider-prefixed API keys: whole-value fullmatch, high confidence, no entropy needed ---
PROVIDER_KEY_PATTERNS = [
    r'(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}',          # GitHub
    r'github_pat_\w{82}',                                       # GitHub fine-grained PAT
    r'sk-(?:(?:proj|svcacct|service)-[A-Za-z0-9_-]+|[A-Za-z0-9]+)T3BlbkFJ[A-Za-z0-9_-]+',  # OpenAI
    r'sk-ant-(?:admin01|api03)-[\w-]{93}AA',                   # Anthropic
    r'xox[bpar]-[0-9]{10,13}-[0-9]{10,13}[A-Za-z0-9-]*',       # Slack token
    r'[rs]k_(?:live|test)_[A-Za-z0-9]{20,247}',                # Stripe
    r'(?:AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}',                    # AWS access key id
    r'AIzaSy[A-Za-z0-9_-]{33}',                                # Google API key
    r'(?:hf_|api_org_)[A-Za-z0-9]{34}',                        # HuggingFace
    r'SG\.[\w-]{20,24}\.[\w-]{39,50}',                         # SendGrid
    r'(?:AC|SK)[0-9a-f]{32}',                                  # Twilio
    r'key-[a-z0-9]{32}',                                       # Mailgun
    r'dp\.(?:pt|st|ct|sa|scim|audit)\.[A-Za-z0-9]{40,44}',     # Doppler
    r'glpat-[A-Za-z0-9_-]{20,300}',                            # GitLab PAT
    r'npm_[A-Za-z0-9]{36}',                                    # npm
    r'cf(?:k|ut|at)_[A-Za-z0-9_-]{40,}',                       # Cloudflare (unverified prefix)
    r'PMAK-[A-Fa-f0-9]{24}-[A-Fa-f0-9]{34}',                  # Postman
    r'shp(?:at|ss|pa|ca)_[A-Fa-f0-9]{32}',                    # Shopify
]
PROVIDER_KEY_RE = re.compile('|'.join(f'(?:{p})' for p in PROVIDER_KEY_PATTERNS))

PRIVATE_KEY_RE = re.compile(
    r'-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |)PRIVATE KEY(?: BLOCK)?-----'
    r'|PuTTY-User-Key-File-2')
JWT_RE = re.compile(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*')
CONN_STRING_RE = re.compile(
    r'^(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis(?:s)?|mssql|jdbc:[^:]+)://[^:]+:[^@]+@')
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
WEBHOOK_VALUE_RE = re.compile(
    r'https://hooks\.slack\.com/services/T[\w]+/B[\w]+/[\w]+'
    r'|https://discord(?:app)?\.com/api/webhooks/\d+/[\w-]+'
    r'|https?://\S+/(?:webhook|hook|trigger|notify)\b', re.IGNORECASE)

# --- Placeholder signals (high precision) ---
PLACEHOLDER_STRUCTURAL_RE = re.compile(
    r'^<[^>]+>$'                       # <API_KEY>
    r'|^\{\{[^}]*\}\}$'                # {{KEY}}
    r'|^\$\{?[A-Za-z_]\w*\}?$'         # ${KEY} / $KEY
    r'|^\[[^\]]+\]$'                   # [KEY]
    r'|^%[A-Za-z_]\w*%$'              # %KEY%
    r'|^@[A-Za-z_]\w*@$')             # @KEY@
PLACEHOLDER_KEYWORD_RE = re.compile(
    r'^(?:'
    r'x{3,}|changeme|change[-_]me|your[-_]?api[-_]?key(?:[-_]here)?|your[-_]?key|your[-_]?secret|'
    r'replace[-_]?me|insert[-_]?here|fill[-_]?me[-_]?in|put[-_]?your[-_]?key[-_]?here|add[-_]?your[-_]?key|'
    r'required|tbd|todo|fixme|not[-_]?set|unset|undefined|empty|missing|disabled|n/?a|'
    r'none|null|false|true|off|default|example|sample|demo|dummy|fake|mock|test|testing|'
    r'foobar|foo|bar|baz|qux|placeholder|password123|secret123|abc123|mypassword|mysecret|mykey|'
    r'12345+|abcdefg?h?'
    r')$', re.IGNORECASE)
PLACEHOLDER_REPEAT_RE = re.compile(r'^(.)\1{5,}$')          # aaaaaa, 111111, ------
KNOWN_DUMMY_RE = re.compile(r'EXAMPLE$', re.IGNORECASE)      # AKIAIOSFODNN7EXAMPLE etc.

# --- Name-based signals ---
NAME_PASSWORD_RE = re.compile(r'(?:_PASSWORD|_PASSWD|_PWD|_PASS)$|^(?:PGPASSWORD|PASSWORD|PASSWD)$', re.IGNORECASE)
NAME_CLIENT_ID_RE = re.compile(r'CLIENT_ID$', re.IGNORECASE)
NAME_CLIENT_SECRET_RE = re.compile(r'CLIENT_SECRET$', re.IGNORECASE)
NAME_TOKEN_RE = re.compile(r'(?:_TOKEN|_ACCESS_TOKEN|_REFRESH_TOKEN|_BEARER_TOKEN|_AUTH_TOKEN)$'
                           r'|^(?:BEARER|ACCESS_TOKEN|REFRESH_TOKEN|SESSION_TOKEN)$', re.IGNORECASE)
NAME_WEBHOOK_RE = re.compile(r'WEBHOOK|_HOOK_URL$|_HOOK$', re.IGNORECASE)
NAME_EMAIL_RE = re.compile(r'_EMAIL$|_MAIL$|^SMTP_|^IMAP_|^FROM_', re.IGNORECASE)
NAME_SECRETISH_RE = re.compile(r'(?:_KEY|_API_KEY|_SECRET|_SECRET_KEY|_ACCESS_KEY)$|API_KEY|SECRET', re.IGNORECASE)

ENTROPY_MIN = 3.5
LEN_MIN = 16


def shannon_entropy(s):
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def is_placeholder(value):
    return bool(
        PLACEHOLDER_STRUCTURAL_RE.match(value)
        or PLACEHOLDER_KEYWORD_RE.match(value)
        or PLACEHOLDER_REPEAT_RE.match(value)
        or KNOWN_DUMMY_RE.search(value)
    )


def classify(name, value):
    """Return (state, kind). kind is None unless state == 'filled'. Never returns the value."""
    if value == '':
        return ('empty', None)
    if is_placeholder(value):
        return ('placeholder', None)

    # Explicit, high-precision kinds (not overridden by length/entropy)
    if PRIVATE_KEY_RE.search(value):
        return ('filled', 'private_key')
    if JWT_RE.fullmatch(value) and len(value) >= 50:
        return ('filled', 'jwt')
    if CONN_STRING_RE.match(value):
        return ('filled', 'connection_string')
    # Webhook by name only counts when the value is actually a URL - otherwise a
    # name like WEBHOOK_CALLBACK_SECRET (a secret, not a URL) falls through to
    # secret detection below.
    if WEBHOOK_VALUE_RE.match(value) or (NAME_WEBHOOK_RE.search(name) and value.startswith(('http://', 'https://'))):
        return ('filled', 'webhook_url')
    if EMAIL_RE.fullmatch(value) or (NAME_EMAIL_RE.search(name) and EMAIL_RE.search(value)):
        return ('filled', 'email')
    if PROVIDER_KEY_RE.fullmatch(value):
        return ('filled', 'api_key')

    # Name-driven kinds
    if NAME_CLIENT_ID_RE.search(name):
        return ('filled', 'client_id')
    if NAME_CLIENT_SECRET_RE.search(name):
        return ('filled', 'client_secret')
    if NAME_PASSWORD_RE.search(name):
        return ('filled', 'password')
    if NAME_TOKEN_RE.search(name):
        return ('filled', 'token')

    # Secret-named, no explicit kind: use entropy+length to split real from dummy
    if NAME_SECRETISH_RE.search(name):
        if shannon_entropy(value) >= ENTROPY_MIN and len(value) >= LEN_MIN:
            return ('filled', 'api_key')
        return ('placeholder', None)

    return ('filled', 'other')


def strip_value(raw):
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        v = v[1:-1]
    return v


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: env-key-classify.py <file> [name-filter-regex]\n")
        sys.exit(1)
    path = sys.argv[1]
    name_filter = re.compile(sys.argv[2], re.IGNORECASE) if len(sys.argv) > 2 else None

    line_re = re.compile(r'^(?:export\s+)?([A-Z][A-Z0-9_]*)=(.*)$')
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            lines = fh.readlines()
    except FileNotFoundError:
        sys.stderr.write(f"Error: file not found: {path}\n")
        sys.exit(1)

    seen = set()
    out = []
    for line in lines:
        m = line_re.match(line.rstrip('\n'))
        if not m:
            continue
        name, raw = m.group(1), m.group(2)
        if name in seen:
            continue
        seen.add(name)
        if name_filter and not name_filter.search(name):
            continue
        state, kind = classify(name, strip_value(raw))
        out.append(f"{name}: {state}" + (f" ({kind})" if kind else ""))

    print('\n'.join(sorted(out)))


if __name__ == '__main__':
    main()
