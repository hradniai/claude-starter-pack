---
type: core
title: "_CONTEXT"
status: active
summary: "Your persistent context across all projects: your profile, your own best practices, and the model lineup with its prompting guide."
created: 2026-05-01
updated: 2026-10-05
created_by: claude-starter-pack
client: ~
path: _CONTEXT/README.md
tags: [readme]
version: "1.0.0"
---

# _CONTEXT

Context about you and your way of working that Claude uses in every project.

| Path | What it is | How Claude uses it |
|------|------------|--------------------|
| `user-profile.md` | Who you are, what you do, how you like to collaborate | Imported into every session by `~/.claude/CLAUDE.md` |
| `best-practices/` | Your own approach per recurring topic, one file each | Checked before generic advice when a topic comes up |
| `llms/model-lineup.md` | Current models: IDs, prices, limits, which for what, with sources and a date | Read before any model recommendation |
| `llms/model-reference-prompting.md` | How each model wants to be prompted; how to build skills and plugins | Read when Claude writes a prompt, skill or agent |

Keep `user-profile.md` current: an outdated profile is worse than none. Add a best-practices file only when a stable approach of your own emerges ([best-practices/README.md](best-practices/README.md) has the format). The two `llms/` files are dated; when they are more than a month old, Claude confirms model facts on the vendors' pages.

If you move or rename this folder, update the paths in `~/.claude/` that point here (see `docs/customization.md` in the pack repository).
