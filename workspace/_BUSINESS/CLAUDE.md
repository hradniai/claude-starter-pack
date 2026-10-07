---
type: core
title: "CLAUDE"
status: active
summary: "Your own business work: projects, education, research, internal docs and scripts, with naming and versioning conventions."
created: 2026-05-01
updated: 2026-10-06
created_by: claude-starter-pack
client: ~
path: _BUSINESS/CLAUDE.md
tags: [agents-manifest]
version: "1.0.0"
---

<purpose>
Your own business work - offers you produce, content you create, internal projects, education materials, your own tooling.

Distinct from `_CLIENTS/` (which is per-engagement) and `_APPS/` (which is for tools you build).
</purpose>

<scope>
## What lives here
- **`projects/`** - internal projects (rebrand, new offering, ops automation, etc.)
- **`education/`** - learning materials you create or consume (courses, talks, workshops)
- **`research/`** - generic research outputs (market scans, competitor analysis, technology evaluations)
- **`docs/`** - internal documentation (your own playbooks, processes, templates)
- **`scripts/`** - small utilities for your own workflow
</scope>

<conventions>
- Per-project documentation in `projects/{name}/` - each project gets its own CLAUDE.md if it grows beyond a single file
- Research files: `{topic}-research-{YYYY-MM-DD}.md` written by the `research` skill
- Versioned content (offers, talks): use `vN-` prefix or date in filename, archive old versions in subdirectory
</conventions>
