#!/usr/bin/env python3
"""
PreToolUse safety hook for Bash + Read.

Blocks dangerous patterns that plain deny rules miss:
- two-step download-and-execute, pipe-to-shell, subshell/eval bypasses
- reading secret files (.env, ssh, aws, gnupg, git-credentials, browser data)
- docker host-root mount, --privileged, sensitive host mount
- disk ops on physical devices, fork bombs

Env read policy (the important one):
- Claude must never load SECRET env VALUES into context, via ANY command
  (cat/cut/source/redirection/python -c/docker mount/...).
- The ONLY file whose real values Claude may read is `.env.local` - the
  deliberate, single channel for handing Claude an API key/token.
- Non-secret templates (.env.example/.sample/.template/.dist) are also readable.
- For any other `.env`/`.env.<name>`: values blocked; use
  `list-env-keys.sh --from <path>` to list key NAMES only.

Exit codes:
  0 = allow (no match, command continues to permission engine)
  2 = block with stderr message
"""
import json
import os
import re
import sys

# --- env-file read protection -------------------------------------------------
# Capture group 1 = the env filename token (.env, .env.production, ...).
# Prefix must be a shell/path separator so we don't match inside a longer word
# (e.g. ".environment"). Trailing negative lookahead ensures we captured the
# whole dotted filename.
ENV_TOKEN = re.compile(
    r"""(?:^|[\s'"=:(<>|&;,/])(\.env(?:\.[A-Za-z0-9_-]+)*)(?![\w./-])""",
    re.IGNORECASE,
)
ENV_READ_OK = {'.env.local', '.env.example', '.env.sample', '.env.template', '.env.dist'}
HELPER = 'list-env-keys.sh'


def env_block_reason_bash(command):
    """Return a block reason if a bash command reads a protected env file."""
    for seg in re.split(r'&&|\|\||[|;&\n]', command):
        protected = [t for t in ENV_TOKEN.findall(seg) if t.lower() not in ENV_READ_OK]
        if not protected:
            continue
        # The names-only helper is the sanctioned way to inspect a protected env.
        if HELPER in seg:
            continue
        return (
            "reading a protected env file (%s) - secret VALUES must not enter "
            "context. Use `%s --from <path>` for key NAMES only, or use "
            "`.env.local` for a deliberate key handoff." % (protected[0], HELPER)
        )
    return None


DANGEROUS = [
    (r'(curl|wget)\s+[^|;&]*\s*(-o\s*\S+|>\s*\S+).*(?:&&|;|\|\|).*\b(bash|sh|zsh)\b\s+\S+',
     'two-step download-then-execute (curl/wget to file, then exec)'),
    (r'(curl|wget)[^|]+\|\s*(bash|sh|zsh|fish)\b',
     'piping curl/wget directly to shell'),
    (r'\b(bash|sh|zsh)\s+-c\s+["\'][^"\']*\b(rm\s+-[a-zA-Z]*[rf]|curl|wget|chmod\s+(?:777|666|\+s)|sudo)\b',
     'subshell -c bypass with destructive command'),
    (r'\beval\s+["\'][^"\']*\b(rm\s+-[a-zA-Z]*[rf]|curl|wget|chmod\s+(?:777|666|\+s)|sudo)\b',
     'eval bypass with destructive command'),
    (r'\b(cat|less|more|head|tail|bat|nl|xxd|od)\s+[^|;&]*\.ssh/(id_|authorized_keys|known_hosts)',
     'reading SSH keys/config via bash'),
    (r'\b(cat|less|more|head|tail|bat|nl|xxd|od)\s+[^|;&]*\.aws/credentials',
     'reading AWS credentials via bash'),
    (r'\b(cat|less|more|head|tail|bat|nl|xxd|od)\s+[^|;&]*\.gnupg/',
     'reading GPG keyring via bash'),
    (r'\b(cat|less|more|head|tail|bat|nl|xxd|od)\s+[^|;&]*\.git-credentials\b',
     'reading git credentials via bash'),
    (r'\bdd\s+(if|of)=/dev/(disk|sd[a-z]|nvme|hd[a-z])',
     'dd targeting physical disk device'),
    (r'\bmkfs\.[a-z0-9]+\s+/dev/',
     'filesystem format on device'),
    (r'\bfdisk\s+/dev/',
     'fdisk on device'),
    (r':\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:',
     'fork bomb'),
    (r'docker\s+run\s+[^#\n]*-v\s+/:(\s|/)',
     'docker mounting host root filesystem'),
    (r'docker\s+run\s+[^#\n]*--privileged\b',
     'docker --privileged flag'),
    (r'docker\s+(run|create)\s+[^#\n]*-v\s+\S*(\.ssh|\.aws|\.gnupg|\.kube|\.docker|\.config/gh)\b',
     'docker mounting a sensitive host path (ssh/aws/gnupg/kube/docker/gh)'),
    (r'\b(cat|less|more|head|tail|bat|nl|xxd|od|grep|egrep|fgrep|rg|ag|sqlite3)\s+[^|;&]*Library/(Cookies|Safari|Application Support/Google/Chrome|Application Support/Chromium|Application Support/Firefox|Application Support/BraveSoftware|Application Support/Microsoft Edge|Application Support/Arc)/',
     'reading browser data (cookies/history/sessions) via bash'),
    (r'\b(cat|less|more|head|tail|bat|nl|xxd|od|grep|egrep|fgrep|rg|ag|sqlite3)\s+[^|;&]*\.(mozilla|config/google-chrome|config/chromium)/',
     'reading browser data on Linux via bash'),
    (r'\bpython3?\s+-c\s+["\'][^"\']*\b(os\.system|subprocess\.|shutil\.rmtree|os\.remove|os\.unlink|os\.rmdir|os\.path\.expanduser.*\.(ssh|aws|gnupg))',
     'python -c bypass invoking shell or touching sensitive paths'),
]


def block(reason, command=None):
    print(f"BLOCKED by extended safety hook: {reason}", file=sys.stderr)
    if command:
        print(f"Command: {command}", file=sys.stderr)
    print("This is a hard safety boundary. Do NOT retry with a workaround.", file=sys.stderr)
    sys.exit(2)


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool = data.get('tool_name')
    tool_input = data.get('tool_input', {}) or {}

    # Read tool: block reading protected env files; allow .env.local + templates.
    if tool == 'Read':
        fp = tool_input.get('file_path', '') or ''
        base = os.path.basename(fp).lower()
        if base == '.env' or base.startswith('.env.'):
            if base in ENV_READ_OK:
                sys.exit(0)
            block("reading a protected env file via Read tool (%s) - use "
                  "`%s --from %s` for key NAMES only, or read `.env.local`."
                  % (os.path.basename(fp), HELPER, fp))
        sys.exit(0)

    if tool != 'Bash':
        sys.exit(0)

    command = tool_input.get('command', '')
    if not command:
        sys.exit(0)

    reason = env_block_reason_bash(command)
    if reason:
        block(reason, command)

    for pattern, why in DANGEROUS:
        if re.search(pattern, command, re.IGNORECASE):
            block(why, command)

    sys.exit(0)


if __name__ == '__main__':
    main()
