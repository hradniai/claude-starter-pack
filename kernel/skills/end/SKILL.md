---
name: end
description: Close a work session - turn the captured TODO notes into BUGS.md / TECH-DEBT.md / decision-log entries, write the worklog row and log block, refresh WORKSTATE.md, make one local commit of the session's files, ask before any push, and post an honest summary. Use when the user types /end or says "let's wrap up", "end the session", "we're done for today", "close out".
metadata:
  type: core
  status: active
  summary: "Session close: materialize Pending docs notes, worklog row and log block, WORKSTATE refresh, one local commit, push only after a yes, and an honest closing summary."
  created: 2026-06-17
  updated: 2026-10-06
  created_by: claude-starter-pack
  client: ~
  tags: [skill, documentation, git, claude-code]
---

# /end

Write the session down so the next session (or a stranger) can pick it up, commit it locally, and tell the user honestly what happened. Steps 1-6 run without stopping to ask; the only questions come in step 7: the push, because a push leaves the machine, and any file that mixes this session's changes with earlier ones, because only the user can say whether those go in. File formats come from `~/.claude/rules/documentation-standard.md`.

## Step 1: Timestamp and project folder

Run `date '+%Y-%m-%d %H:%M'` and use that exact value everywhere. The project folder is the git repository root (`git rev-parse --show-toplevel`), or the current directory outside a repository; if the session's work was in a sub-project with its own `WORKSTATE.md`, use that sub-project's journals. If that would be your home folder, `~/Documents` or a workspace root such as `~/Documents/_CLIENTS`, ask which project the session belongs to. Create a missing `worklog.md` or `WORKSTATE.md` from `~/.claude/templates/worklog.md` / `workstate.md` (placeholders: `{{PROJECT}}` the folder name, `{{DATE}}` today, `{{AUTHOR}}` the user's first name as a lowercase slug, else `claude`).

## Step 2: Turn the Pending docs notes into entries

Read the WHOLE `## Pending docs` section of WORKSTATE, not just the lines this session added: every line still starting with `BUG-TODO:`, `DEBT-TODO:` or `DECISION-TODO:` is open, whichever session wrote it. For each, write the real entry, then rewrite the note into a pointer such as `- BUG-004 <title> -> BUGS.md (YYYY-MM-DD)`. A pointer is how a note is closed; never delete one. Create a file on first use with minimal frontmatter per the frontmatter standard (`BUGS.md`: `type: core`, tag `bugs`; `TECH-DEBT.md`: `type: core`, tag `tech-debt`; `docs/decision-log.md`: `type: core`, tag `decision-log`), and add a link to it under WORKSTATE `## Related context`.

- `BUG-TODO:` -> `BUGS.md`, newest entry first, next free number, never deleted (only its Status changes):
  ```
  ## BUG-NNN <short title> - Status: open (YYYY-MM-DD)
  - Where: <file:line or area>
  - Observed: <what happens>
  - Expected: <what should happen>
  - Found while: <task>
  ```
- `DEBT-TODO:` -> `TECH-DEBT.md`, same discipline: `## DEBT-NNN <title> - Status: open (YYYY-MM-DD)` with Where / What / Risk if left / Found while.
- `DECISION-TODO:` -> a row in `docs/decision-log.md`: `| D<n> | <decision> | YYYY-MM-DD | <why> | <detail> |`. If a decision also meets the ADR bar in the documentation standard, do not write the ADR now: name it in the summary and offer to write it.

## Step 3: worklog.md

Never read the whole worklog. Find the line number of the table's last row with `awk '/^## Log/{exit} /^[|]/{n=NR} END{print n}' worklog.md`, read around it, and insert the end row directly below it (oldest first):
```
| YYYY-MM-DD HH:MM | end | <2-3 sentences: goal, outcome, what remains> | <relative paths of files touched this session> |
```
Then insert a block right under the `## Log` heading (create the heading if missing), above older blocks:
```
### YYYY-MM-DD HH:MM - <what the session did>
<what was done, why, decisions taken (with D-numbers), what is still open>
```

## Step 4: WORKSTATE.md

Read it whole (it is small) and refresh it in place: `## Focus` = the next concrete step, `## Current state` = where things stand now, `updated:` in the frontmatter = today. No history in WORKSTATE; that went into the worklog.

## Step 5: Decision log

Add a `docs/decision-log.md` row for every directional decision made this session that is not logged yet (create the file with the header `| # | Decision | Date | Why | Detail |` if missing).

## Step 6: Local commit

Skip if this is not a git repository (`git rev-parse --is-inside-work-tree`) or `git status --porcelain` is empty. A commit claims authorship of everything in it, so it holds this session's changes and nothing the user had going before: neither their uncommitted edits nor what they staged themselves.

1. **Note what is already staged:** `git diff --cached --name-only`. That staging is the user's choice: never unstage it and never commit it for them.
2. **Check each session file before staging it.** Session files are the paths in the end row plus every file steps 2-5 wrote. Read each one's whole change with `git diff HEAD -- <path>` (staged and unstaged together; for an untracked file, or before the first commit, the whole file is the change). A file is *clean* when every change in it is this session's work. When it also holds changes from before this session (the user's own edits, an earlier session's uncommitted work), it is *mixed*: do not stage it; it goes to the question in step 7. Interactive `git add -p` is not available to you, so a mixed file is never split or committed silently. When unsure whose a change is, treat it as not this session's.
3. Secret guard: never stage a `.env` / `.env.*` file (other than a placeholder template: `.env.example`, `.env.sample`, `.env.template`, `.env.dist`), an `.envrc`, a `*.pem`, a `*.key` or an SSH private key; leave it out and warn the user. If one is among the files the user had staged, leave it staged and warn them that their next commit would include it.
4. Stage the clean files, each with `git add -- <path>`. Never `git add -A` or `git add .`: changes that were already lying in the folder do not belong to this session.
5. Review `git diff --cached -- <clean paths>`: it must show exactly the changes you checked. If it shows anything else, stop and report it instead of committing.
6. Commit only those paths, naming them: `git commit -m "<type>(<scope>): <subject>" -- <clean paths>`, a Conventional Commits message summarizing the session, English, imperative, lowercase. With the paths named, git commits exactly those files; whatever the user staged stays staged and out of the commit.
7. If the commit fails, report the exact error. Never retry with `--no-verify` or any other way around a hook.
8. Never unstage, restore or reset anything here: the user's staging and working files stay exactly as they were. Changed files that were not this session's stay uncommitted and are listed in the summary, so nothing is swept in and nothing goes unnoticed.

## Step 7: Mixed files and push - ask first

**Mixed files** (from step 6), if any: name each with what it holds besides this session's work, in a few words, and ask whether to commit it as it is, earlier changes included, or leave it to the user. On "commit": `git add -- <path>`, then `git commit -m "<type>(<scope>): <subject>" -- <path>`. Otherwise leave it untouched. Ask this together with the push question below, and settle it before pushing.

**Push.** Show what would leave the machine: the commits with the files each one changes, `git log @{u}..HEAD --stat --oneline` if the branch has an upstream, else `git log --stat --oneline -n 10`. Point out any file that looks like a secret or does not belong, and offer the full diff (`git diff @{u}..HEAD`) if the user wants to read it. If there is no remote (`git remote` prints nothing), say the commits are local only and stop here. Otherwise ask: `Push N commits to <remote>/<branch>? (y/n)`, and push only on a yes. On `main` or `master` the pack's push guard blocks a direct push on purpose: offer to move the work to a branch (`git switch -c <branch-name>`, then `git push -u origin <branch-name>`) and open a pull request, or to leave the commits local. Never try to get around the guard.

## Step 8: Summary

One short closing message, in this order:

1. **Written** - one line per file actually changed by this skill (worklog, WORKSTATE, BUGS, TECH-DEBT, decision log).
2. **Git** - the commit subject(s), the push result, and any files left uncommitted with the reason (mixed and left to the user, staged by the user and left staged, or not this session's).
3. **Open items** - new bugs and debt, highest impact first, one line each; any ADR worth writing.
4. **Next** - the Focus line from WORKSTATE.

Report only what actually happened: a step that was skipped or failed is named as skipped or failed, with the reason, never presented as done. No reflections, no essays.

## Rules

- Do not re-read the whole conversation; use the checkpoints and recent context.
- Timestamp from `date`, never guessed.
- Every file written here is English and never contains a secret value.
- README.md is not a journal: this skill does not update it.
