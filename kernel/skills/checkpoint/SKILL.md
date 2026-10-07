---
name: checkpoint
description: Save a quick mid-session checkpoint - one worklog.md row, a short dated log block, a refreshed WORKSTATE.md, one-line TODO notes for anything found along the way, and a local git commit (never a push). Use when the user types /checkpoint or says "checkpoint", "save progress", "log what we did so far", "commit this progress", and before a risky step or a break. Takes about ten seconds; no analysis.
metadata:
  type: core
  status: active
  summary: "Mid-session checkpoint: a worklog row and log block, a refreshed WORKSTATE head, captured TODO notes, and one local commit of only this session's files."
  created: 2026-06-17
  updated: 2026-10-06
  created_by: claude-starter-pack
  client: ~
  tags: [skill, documentation, git, claude-code]
---

# /checkpoint

Lock in what was done since the last checkpoint (or the session start) so it survives autocompaction and a closed terminal. Keep it short: about ten seconds, no analysis, no commentary. Where the journals live and what goes in them is defined in `~/.claude/rules/documentation-standard.md`; this skill is the fast path through it.

## Steps

1. **Timestamp.** Run `date '+%Y-%m-%d %H:%M'` and use that exact value everywhere below. Never estimate the time.

2. **Project folder.** The git repository root (`git rev-parse --show-toplevel`), or the current directory when it is not a repository. If this session's work happened in a sub-project that keeps its own `WORKSTATE.md`, use that sub-project's journals: the nearest WORKSTATE wins. If that would be your home folder, `~/Documents` itself or a workspace root such as `~/Documents/_CLIENTS`, ask which project the work belongs to instead of writing there.

3. **Create missing journals.** If `worklog.md` or `WORKSTATE.md` is missing in the project folder, create it from `~/.claude/templates/worklog.md` or `~/.claude/templates/workstate.md`, filling the placeholders: `{{PROJECT}}` the folder name, `{{DATE}}` today, `{{AUTHOR}}` the user's first name as a lowercase slug (from the user profile, else `claude`), `{{FOCUS}}` and `{{CURRENT_STATE}}` one line each.

4. **worklog.md row.** Never read the whole worklog. Find the line number of the table's last row with `awk '/^## Log/{exit} /^[|]/{n=NR} END{print n}' worklog.md`, read a few lines around it, and insert directly below it (the table is oldest first):
   ```
   | YYYY-MM-DD HH:MM | checkpoint | <what was done, at most ~10 words> | <relative paths of files touched> |
   ```

5. **worklog.md log block** - only if something material changed (skip for a pure read or test pass). Insert right under the `## Log` heading (create the heading at the end of the file if it is missing), above any older block, so the newest is first:
   ```
   ### YYYY-MM-DD HH:MM - <what>
   <2-5 lines: what was done, why, and any decision taken>
   ```

6. **WORKSTATE.md.** Read it whole (it is small). Refresh `## Focus` (what is in progress, the next step) and `## Current state` in place, and set `updated:` in its frontmatter to today. Never put a log or history into WORKSTATE.

7. **Capture, do not detour.** If something surfaced since the last checkpoint that is not this task, add ONE line under `## Pending docs` in WORKSTATE and keep going; `/end` turns each line into a real entry:
   - `BUG-TODO: <where (file:line)> - <observed vs expected> - found while <task>`
   - `DEBT-TODO: <where> - <what works but is costly or risky> - <risk if left>`
   - `DECISION-TODO: <the decision> - <why, alternatives rejected>`
   A clear directional decision may instead go straight into `docs/decision-log.md` as a row `| D<n> | <decision> | YYYY-MM-DD | <why> | <detail> |` (if the file is missing, create it with the header `| # | Decision | Date | Why | Detail |` and the short journal header: `type: core`, tag `decision-log`).

8. **Local commit of this session's changes only, never a push.** A commit claims authorship of everything in it, so it holds this session's changes and nothing the user had going before: neither their uncommitted edits nor what they staged themselves.
   - Skip silently if this is not a git repository (`git rev-parse --is-inside-work-tree`) or `git status --porcelain` is empty.
   - **Note what is already staged:** `git diff --cached --name-only`. That staging is the user's choice: never unstage it and never commit it for them.
   - **Check each session file before staging it.** Session files are the paths in the worklog row plus the journals you just wrote. Read each one's whole change with `git diff HEAD -- <path>` (staged and unstaged together; for an untracked file, or before the first commit, the whole file is the change). A file is *clean* when every change in it is this session's work. When it also holds changes from before this session (the user's own edits, an earlier session's uncommitted work), it is *mixed*: do not stage it; ask about it in the report. Interactive `git add -p` is not available to you, so a mixed file is never split or committed silently. When unsure whose a change is, treat it as not this session's.
   - Secret guard: never stage a `.env` / `.env.*` file (other than a placeholder template: `.env.example`, `.env.sample`, `.env.template`, `.env.dist`), an `.envrc`, a `*.pem`, a `*.key` or an SSH private key; leave it out and tell the user. If one is among the files the user had staged, leave it staged and warn them that their next commit would include it.
   - Stage the clean files, each with `git add -- <path>`. Never `git add -A` or `git add .`: that sweeps in whatever else was lying in the folder, and the commit then claims work it did not do.
   - Review `git diff --cached -- <clean paths>`: it must show exactly the changes you checked. If it shows anything else, stop and report it instead of committing.
   - Commit only those paths, naming them: `git commit -m "<type>(<scope>): <subject>" -- <clean paths>`. With the paths named, git commits exactly those files; whatever the user staged stays staged and out of the commit. The message is Conventional Commits derived from the row, type `feat` / `fix` / `docs` / `chore` / `refactor` / `test`, English, imperative, lowercase.
   - If the commit fails, report the exact error. Never retry with `--no-verify` or any other way around a hook.
   - Never push from a checkpoint. A local commit is reversible, so it needs no confirmation.

## Report

One line: `Committed locally: <type>(<scope>): <subject>` (or why nothing was committed). Then one line for each of these that applies:
- **A mixed file:** `<path> also holds changes from before this session (<what they are, in a few words>), so it was not committed. Commit it as it is, earlier changes included, or leave it to you?` On "commit": `git add -- <path>`, then `git commit -m "<type>(<scope>): <subject>" -- <path>`. Otherwise leave it as it is.
- **Files the user had staged:** their paths; still staged, not in this commit.
- **Other changed files:** their paths; not this session's work, left uncommitted.

## Rules

- Never unstage, restore or reset anything: the user's staging and working files stay exactly as they were. The only change to the index is staging the clean session files.
- At most ~10 words in the worklog description: what, not how.
- Never read the whole worklog: locate the line you need (awk or grep), then read around it.
- Timestamp from `date`, 24-hour, never guessed.
- No essays. Write the row, refresh the head, commit, report one line plus one per leftover.
