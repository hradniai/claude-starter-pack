#!/usr/bin/env python3
"""
PreToolUse hook for Read.

Warns the user before Claude loads a file that would consume a large share of
the context window. Vibe-coders sometimes ask Claude to "read this CSV" without
realizing the file is 80MB — that one Read can blow out a multi-hour session.

Heuristic:
- Estimate token count as bytes / 4 (rough rule of thumb for English/code text).
- Files under WARN_TOKENS pass silently.
- Files over WARN_TOKENS prompt the user with a re-confirm message and exit 2.
- Files over HARD_TOKENS are blocked outright and the user is told to use head /
  grep / a chunked approach instead.

Exit codes:
  0 = allow
  2 = block with explanation (Claude must re-confirm with the user)

This is intentionally a soft brake, not a hard limit. The pack does not enforce
any token cap on Claude itself — but Read is the highest-leverage way to waste
context, so it gets one extra checkpoint.

To bypass for a specific Read: tell Claude explicitly ("yes, load the whole
file") and Claude will retry — but the user has to confirm in the prompt, not
the hook.
"""
import json
import os
import sys

WARN_TOKENS = 50_000   # ~200 KB of text. Prompts the user.
HARD_TOKENS = 200_000  # ~800 KB. Blocks outright.

BYTES_PER_TOKEN = 4    # Rough heuristic. Binary/dense files vary; this is a safe overestimate.


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if data.get('tool_name') != 'Read':
        sys.exit(0)

    tool_input = data.get('tool_input', {}) or {}
    file_path = tool_input.get('file_path', '')
    if not file_path:
        sys.exit(0)

    # Respect explicit offset/limit — if Claude is already chunking, don't second-guess.
    if tool_input.get('offset') is not None or tool_input.get('limit') is not None:
        sys.exit(0)

    try:
        size_bytes = os.path.getsize(file_path)
    except OSError:
        sys.exit(0)  # File doesn't exist or unreadable — let Read handle the error itself.

    est_tokens = size_bytes // BYTES_PER_TOKEN

    if est_tokens >= HARD_TOKENS:
        print(
            f"BLOCKED: {file_path} is approximately {est_tokens:,} tokens "
            f"(~{size_bytes:,} bytes). That's larger than the hard ceiling of "
            f"{HARD_TOKENS:,} tokens for a single Read.",
            file=sys.stderr,
        )
        print(
            "Reading this file whole would consume most of the context window "
            "and likely cause the rest of the session to degrade.",
            file=sys.stderr,
        )
        print(
            "Use one of: `head -n 200 <file>` via Bash, `grep <pattern> <file>`, "
            "the `offset`/`limit` arguments on Read, or split the file before reading.",
            file=sys.stderr,
        )
        sys.exit(2)

    if est_tokens >= WARN_TOKENS:
        print(
            f"STOP: {file_path} is approximately {est_tokens:,} tokens "
            f"(~{size_bytes:,} bytes). Loading it will consume a meaningful share "
            f"of the context window.",
            file=sys.stderr,
        )
        print(
            "Are you sure you need the whole file? Cheaper alternatives:",
            file=sys.stderr,
        )
        print(
            "  - `head -n 200 <file>` or `tail -n 200 <file>` via Bash",
            file=sys.stderr,
        )
        print(
            "  - `grep <pattern> <file>` to find the part you actually need",
            file=sys.stderr,
        )
        print(
            "  - Read with explicit `offset` and `limit` arguments",
            file=sys.stderr,
        )
        print(
            "If you genuinely need the whole file, ask the user to confirm and retry. "
            "Do NOT silently re-issue the same Read.",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
