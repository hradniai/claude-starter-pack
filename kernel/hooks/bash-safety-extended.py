#!/usr/bin/env python3
"""
PreToolUse safety hook for Bash commands.

Blocks dangerous patterns that simple deny rules miss:
- two-step download-and-execute (curl URL > file && bash file)
- subshell bypasses (bash -c, sh -c, eval with destructive payload)
- reading sensitive files via bash (cat .env, cat ~/.ssh/id_rsa)
- docker host-root mount, --privileged
- disk operations on physical devices (dd, mkfs, fdisk)
- fork bombs

Exit codes:
  0 = allow (no match, command continues to permission engine)
  2 = block with stderr message
"""
import json
import re
import sys

DANGEROUS = [
    (r'(curl|wget)\s+[^|;&]*\s*(-o\s*\S+|>\s*\S+).*(?:&&|;|\|\|).*\b(bash|sh|zsh)\b\s+\S+',
     'two-step download-then-execute (curl/wget to file, then exec)'),
    (r'(curl|wget)[^|]+\|\s*(bash|sh|zsh|fish)\b',
     'piping curl/wget directly to shell'),
    (r'\b(bash|sh|zsh)\s+-c\s+["\'][^"\']*\b(rm\s+-[a-zA-Z]*[rf]|curl|wget|chmod\s+(?:777|666|\+s)|sudo)\b',
     'subshell -c bypass with destructive command'),
    (r'\beval\s+["\'][^"\']*\b(rm\s+-[a-zA-Z]*[rf]|curl|wget|chmod\s+(?:777|666|\+s)|sudo)\b',
     'eval bypass with destructive command'),
    (r'\b(cat|less|more|head|tail|bat|nl|xxd|od|grep|egrep|fgrep|rg|ag|awk|sed|cut|tr|wc|file|sort|uniq|tee)\s+[^|;&]*\.env(\b|\.|\s|$)',
     'reading .env via bash (bypasses Read deny)'),
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
    (r'\b(cat|less|more|head|tail|bat|nl|xxd|od|grep|egrep|fgrep|rg|ag|sqlite3)\s+[^|;&]*Library/(Cookies|Safari|Application Support/Google/Chrome|Application Support/Chromium|Application Support/Firefox|Application Support/BraveSoftware|Application Support/Microsoft Edge|Application Support/Arc)/',
     'reading browser data (cookies/history/sessions) via bash'),
    (r'\b(cat|less|more|head|tail|bat|nl|xxd|od|grep|egrep|fgrep|rg|ag|sqlite3)\s+[^|;&]*\.(mozilla|config/google-chrome|config/chromium)/',
     'reading browser data on Linux via bash'),
    (r'\bpython3?\s+-c\s+["\'][^"\']*\b(os\.system|subprocess\.|shutil\.rmtree|os\.remove|os\.unlink|os\.rmdir|os\.path\.expanduser.*\.(env|ssh|aws|gnupg))',
     'python -c bypass invoking shell or touching sensitive paths'),
]


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if data.get('tool_name') != 'Bash':
        sys.exit(0)

    command = data.get('tool_input', {}).get('command', '')
    if not command:
        sys.exit(0)

    for pattern, reason in DANGEROUS:
        if re.search(pattern, command, re.IGNORECASE):
            print(f"BLOCKED by extended safety hook: {reason}", file=sys.stderr)
            print(f"Command: {command}", file=sys.stderr)
            print("This is a hard safety boundary. Do NOT retry with a workaround.", file=sys.stderr)
            sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
