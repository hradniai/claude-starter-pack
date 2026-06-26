---
type: notes
title: "business-claude"
status: approved
summary: "Directory structure for internal business work including projects, education, research, documentation, and scripts with specific naming and organization conventions."
created: 2026-05-07 17:13
updated: 2026-05-07 17:13
owner: Šimon Hradní
client: ~
path: kernel/templates/business-claude.md
tags: [note]
version: "1.0.0"
release: latest
---

<purpose>
{{BUSINESS_CONTEXT}}: your own business work — offers you produce, content you create, internal projects, education materials, your own tooling.

Distinct from `_CLIENTS/` (per-engagement) and `_APPS/` (tools you build for reuse).
</purpose>

<scope>
## What lives here
- **`projects/`** — internal initiatives (rebrand, new offering, ops automation)
- **`education/`** — learning materials you create or consume (courses, talks, workshops)
- **`research/`** — generic research outputs (market scans, competitor analysis, technology evaluations)
- **`docs/`** — internal documentation (your own playbooks, processes, templates)
- **`scripts/`** — small utilities for your own workflow
- **`notes.md`** — brain dump (auto-research workflow active per `notes-convention.md`)
</scope>

<conventions>
- Per-project documentation in `projects/{name}/` — each project gets its own AGENTS.md if it grows beyond a single file
- Research files: `{topic}-research-{YYYY-MM-DD}.md` per `subagent-rules.md`
- Versioned content (offers, talks): use `vN-` prefix or date in filename, archive older versions in subdirectory
- Never expose this content to client deliverables verbatim — internal voice differs from client-facing
</conventions>

<documentation>
README.md and WORKSTATE.md per the `documentation-standard.md` rule. Update WORKSTATE.md after each logical step; delete it when work is fully reflected in README.md.
</documentation>
