---
type: core
title: "Documentation standard"
status: active
summary: "The small file set every project keeps so work survives compaction and new sessions: WORKSTATE.md for live state, worklog.md for history, a decision log, captured bugs and debt, research files. Their shapes, when to write them, and how to write them truthfully."
created: 2026-06-13
updated: 2026-10-06
created_by: claude-starter-pack
client: ~
tags: [rule, standard, documentation]
---

<documentation_standard>

# Project documentation

Long sessions get compacted and every new session starts empty: what is not in a file is gone. A few small files per project carry the work across sessions. You keep them current as you work; the `/checkpoint` and `/end` skills do the routine writing.

## Hard triggers
1. **First edit in a project of the user's own** (a folder in their workspace, or one they asked you to keep journals for; not a repository they cloned to change one thing): create `WORKSTATE.md` and `worklog.md` at the project root if they are missing, from `~/.claude/templates/workstate.md` and `worklog.md`.
2. **Session start, or after a compaction:** read `WORKSTATE.md` whole (it is small on purpose). For recent history read the top of `## Log` in `worklog.md`, never the whole file.
3. **Before you call a piece of work done:** `WORKSTATE.md`, and `docs/decision-log.md` if a decision was made, say what is now true.

## The file set

| File | What it holds |
|---|---|
| `CLAUDE.md` | At the root of a project: purpose, stack, structure, constraints. Claude Code loads it into every session started in the project. The `setup` skill creates it. |
| `WORKSTATE.md` | Live state only: what is going on and what is next. Kept current in place; no history. |
| `worklog.md` | History: one row per checkpoint, dated prose below. Append-only. |
| `docs/decision-log.md` | Smaller directional decisions. Append-only. |
| `docs/decisions/NNNN-<title>.md` | ADRs (architecture decision records): one big, hard-to-reverse decision with the alternatives rejected. Never rewritten; a later ADR supersedes it. |
| `BUGS.md`, `TECH-DEBT.md` | Written by `/end` from captured notes. Entries are never deleted; their status changes in place. |
| `research/` | Research files, `{topic}-research-{YYYY-MM-DD}.md`, written by the `research` skill. In a client folder: `projects/<project>/research/` for project work, the client's `research/` for research outside any project, never loose in the client root. |
| `docs/features/` | Apps and dev projects: one page per feature, updated in the same commit as the code. |

`README.md` is not a journal. Write one when the project has a human reader (the users of an app, someone you hand a repository to) and keep its facts true; history stays in `worklog.md`.

## WORKSTATE.md

```
# WORKSTATE: <project>
## Focus                     what is being worked on now, and the next step
## Current state             where things stand, what is blocked, open questions
## Related context           optional: a few files worth reading to get oriented (not CLAUDE.md, it loads anyway)
## Pending docs              captured one-line notes, see Incidental capture
## Sub-project work states   only when sub-projects exist: one pointer line each
```

Rewrite the sections in place so they stay true and short enough to read whole. Never delete a Pending docs line: `/end` turns it into a pointer to the entry it wrote.

## worklog.md

```
# Worklog

| Timestamp | Type | Description | Files |
|-----------|------|-------------|-------|
| 2026-10-06 14:05 | checkpoint | what was done, up to ~10 words | files touched |

## Log

### 2026-10-06 14:05 - <what was done>
What was done and why, decisions taken, links to them.
```

Table rows run oldest first: `/checkpoint` and `/end` append one each (type `checkpoint` or `end`) at the end of the table. Log blocks run newest first, inserted right under `## Log`. Take timestamps from `date '+%Y-%m-%d %H:%M'`, never guess them. Never rewrite or delete an entry.

## docs/decision-log.md

One per project, in `docs/` so the project root stays uncluttered. A one-line purpose header, then a table: `| # | Decision | Date | Why | Detail |`, IDs `D1`, `D2`, and so on. Append-only. A decision that is hard to reverse and had real alternatives becomes an ADR instead, and its log row points to the ADR.

## Incidental capture

Something you notice while working on something else becomes ONE line under `## Pending docs`, never a detour from the task. Carry the essentials inline, so `/end` can act after this conversation is gone:
- `BUG-TODO:` broken behavior: where (file:line), observed versus expected, found while doing what.
- `DEBT-TODO:` works but is costly or risky: where, what, the risk if left.
- `DECISION-TODO:` a directional decision: what, why, the alternatives rejected.

`/end` writes the real entries (`BUGS.md`, `TECH-DEBT.md`, `docs/decision-log.md`). Fix the thing on the spot only when the user asks.

## Sub-projects

A folder with its own purpose inside a project (a project inside a client folder, a separate part of an app) gets its own `WORKSTATE.md`, `worklog.md` and `docs/decision-log.md`, but no `CLAUDE.md` of its own. Write detail into the nearest one; the parent's WORKSTATE gets one pointer line under `## Sub-project work states`, never a copy.

## Writing it right
- **Only what is true.** A fact has a source (a file, a command's output, a URL), a decision is what the user said, and anything you inferred is labelled as an assumption.
- **Documents Claude reads** (CLAUDE.md, rules, skills, agent files): XML tags around the major sections with Markdown inside, the hardest constraints at the top and repeated at the end, the reason next to each constraint, and nothing that does not change behavior.
- **Frontmatter:** documents carry the small YAML header defined in `frontmatter-standard.md`, which loads when you work on markdown.
- **Commits:** Conventional Commits (`type(scope): subject`), English, imperative, one logical change each. Local commits need no permission; a push does. A commit holds only your own changes: stage files by path (never `git add -A`) and name them in the commit (`git commit -m "..." -- <paths>`), so the user's uncommitted edits and their own staging stay theirs. Never commit an `.env*` file other than a placeholder template such as `.env.example`, and never a credential.
- **Idea files** are written only on an explicit ask, through the `idea-file-creator` skill, which owns their format and location.
- No secrets in any document, and no real client or person names in system files (rules, skills, templates): use placeholders such as `<client>`.

Bottom line: `WORKSTATE.md` is the live state, read whole; `worklog.md` is the history, never read whole; decisions go to `docs/decision-log.md`, side findings to Pending docs. Files are what survives a session.

</documentation_standard>
