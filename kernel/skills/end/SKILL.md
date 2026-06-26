---
name: end
description: End a work session. Autonomously materializes captured bugs/tech-debt/decisions, updates WORKSTATE, README, decision-log and worklog, syncs feature docs, then commits and asks before pushing. Use when finishing a work session.
status: approved
version: "1.0.0"
release: latest
owner: Šimon Hradní
client: ~
path: kernel/skills/end/SKILL.md
type: notes
tags: [note]
title: "/end"
summary: "Close out a session by writing every document up to date, then committing. This runs autonomously - the only thing that waits for a human is the final push confirmation (push goes outward). No ADR ste"
created: 2026-06-17 14:26
updated: 2026-06-17 14:28
---

# /end

Close out a session by writing every document up to date, then committing. This runs autonomously - the only thing that waits for a human is the final push confirmation (push goes outward). No ADR step, no proposals - just write it all.

## Step 1: Capture the timestamp

Run `date '+%Y-%m-%d %H:%M'`. Use that exact value for every entry below. Never estimate.

## Step 2: Materialize the WORKSTATE "Pending docs" notes

For each note in the WORKSTATE "Pending docs" area, write the real entry, then rewrite the note into a pointer to what was written (the only sanctioned WORKSTATE rewrite). Create any file on first use at the project root and add a one-line pointer to it in the WORKSTATE Related context.

- **`BUG-TODO:` -> `BUGS.md`** (newest first, never delete an entry, track Status in place):
  ```
  ## BUG-NNN <short title>  -  Status: open | fixed | wontfix  (YYYY-MM-DD)
  - Where: <file:line or area>
  - Observed: <what happens>
  - Expected: <what should happen>
  - Found while: <context>
  ```
- **`DEBT-TODO:` -> `TECH-DEBT.md`** (same discipline):
  ```
  ## DEBT-NNN <short title>  -  Status: open | resolved  (YYYY-MM-DD)
  - Where: <file:line or area>
  - What: <the debt>
  - Risk if left: <cost / risk>
  - Found while: <context>
  ```
- **`DECISION-TODO:` -> `docs/decision-log.md`** as a table row: `| D# | <decision> | YYYY-MM-DD | <why> | <detail> |`.

After writing, surface the new open bugs and debt in chat, highest impact first, one line each.

## Step 3: Update worklog.md (project root)

Append an end row:
```
| YYYY-MM-DD HH:MM | end | SESSION_SUMMARY | RELATIVE_FILE_PATHS |
```
SESSION_SUMMARY: 2-3 sentences (goal, outcome, what remains). If a `start` row exists earlier in the worklog, you may add the duration `Xh Ym`; otherwise omit it.

## Step 4: Update WORKSTATE.md (append-only)

Refresh the `## Focus` / `## Current state` header in place, and PREPEND one dated `### YYYY-MM-DD HH:MM` block to the engineering log (newest first). Never delete prior content. Do not read the whole file.

## Step 5: Update README.md

Add a dated changelog entry and refresh current state / features / known issues so a cold reader sees the real current state.

## Step 6: Update docs/decision-log.md

A row per directional decision made this session that is not already logged (the `DECISION-TODO` ones were handled in Step 2).

## Step 7: Sync feature docs (only if a features dir exists)

If the repo has `docs/features/` or `features/`, delegate to the `features-documenter` agent (via the Agent tool) to sync feature docs to the changed code. It self-scopes via git diff and no-ops if nothing relevant changed. Skip this step entirely if no features dir exists. Run it last so feature docs are the final artifact before the commit.

## Step 8: Git commit + push

Skip silently if the current directory is not a git repo.

1. **Commit:** if `git status --porcelain` shows changes - secret guard first (if a non-ignored `.env` / `.env.*` other than `.env.example` / `.env.sample` would be staged, STOP and warn, do not commit), else `git add -A` and commit with a Conventional Commits message derived from the summary (English subject).
2. **Show the session's commits:** `git log @{u}..HEAD --oneline` if an upstream exists, else `git log --oneline -n 10`.
3. **Push - ASK FIRST:** if there is a remote with unpushed commits, ask `Push N commits to <remote>? (y/n)`. On yes, `git push`; on no, leave them. Never auto-push.

## Rules

- Steps 1-7 are autonomous - do not stop to ask. Only Step 8's push waits for confirmation.
- Do NOT re-read the entire conversation - use the checkpoints and recent context.
- Timestamp via `date`, never guessed.
- No reflections or essays. Data only.
- Every document written here is English. Never write a secret value into any of them.
