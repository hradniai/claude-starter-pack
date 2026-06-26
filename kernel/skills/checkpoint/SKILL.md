---
name: checkpoint
description: Write a short progress checkpoint - a worklog row, a WORKSTATE engineering-log block, and a local git commit. Use during an active work session to lock in what was just done so it survives autocompact. ~10s, keep it terse.
status: approved
version: "1.0.0"
release: latest
owner: Šimon Hradní
client: ~
path: kernel/skills/checkpoint/SKILL.md
type: notes
tags: [note]
title: "/checkpoint"
summary: "A fast checkpoint: record what was done since the last checkpoint or session start, then commit it locally. KEEP IT SHORT. Target ~10 seconds. No analysis, no commentary."
created: 2026-06-17 14:25
updated: 2026-06-17 14:28
---

# /checkpoint

A fast checkpoint: record what was done since the last checkpoint or session start, then commit it locally. KEEP IT SHORT. Target ~10 seconds. No analysis, no commentary.

## Steps

1. **Capture the timestamp** by running `date '+%Y-%m-%d %H:%M'`. Use that exact value for every entry below. Never estimate the time.

2. **Find the project root** (the git repo root, or the current working directory if not a repo). All files below live there.

3. **Append a row to `worklog.md`** at the project root (create the file with a header if it does not exist):
   ```
   | YYYY-MM-DD HH:MM | checkpoint | SHORT_DESCRIPTION | RELATIVE_FILE_PATHS |
   ```
   - SHORT_DESCRIPTION: max ~10 words, what was done, not how.
   - RELATIVE_FILE_PATHS: the files touched since the last checkpoint.

4. **Update WORKSTATE.md** (only if something material changed - skip for a pure read or test-only pass):
   - Refresh the `## Focus` / `## Current state` header in place.
   - PREPEND one dated `### YYYY-MM-DD HH:MM` block to the engineering log (newest first): what was done and why.
   - Never read the whole WORKSTATE. Edit the header in place, prepend the log block.

5. **Capture incidental items in WORKSTATE "Pending docs"** - if a directional decision, an unrelated bug, or costly-but-working code surfaced since the last checkpoint, drop ONE line each (do not write the real artifact now, `/end` does that):
   - `DECISION-TODO: <decision + why / rejected alternatives>`
   - `BUG-TODO: <where (file:line) + observed vs expected + found while X>`
   - `DEBT-TODO: <where (file:line) + what + risk if left>`
   What counts as each is in the `documentation-standard` rule.

6. **If a clear directional decision was made this checkpoint**, you may instead write it straight to `docs/decision-log.md` as a row (create the file if missing). Either path is fine - a row now, or a `DECISION-TODO` for `/end`.

7. **Local git commit (no push)**:
   - Skip silently if the current directory is not a git repo (`git rev-parse --is-inside-work-tree`) or `git status --porcelain` is empty.
   - **Secret guard:** if a non-ignored `.env` / `.env.*` file (other than `.env.example` / `.env.sample`) would be staged, STOP, warn, do NOT commit.
   - Otherwise `git add -A` and make ONE commit with a Conventional Commits message derived from the description (`feat` / `fix` / `docs` / `chore` / `refactor` ... ; imperative, lowercase, English subject).
   - Never push from a checkpoint. Local commits are reversible, so do this without asking.
   - Report one line only: `Committed locally: <type>(<scope>): <subject>`.

## Rules

- Max ~10 words in the worklog description. What, not how.
- No essays. Append the row, refresh the header, commit, confirm. Done.
- Do NOT read back the entire worklog or WORKSTATE.
- Timestamp via `date '+%Y-%m-%d %H:%M'`, 24-hour, never guessed.
