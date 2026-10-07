---
type: core
title: "business-claude"
status: active
summary: "CLAUDE.md seed for your own business work: what lives in projects, education, research, docs and scripts, and the conventions there."
created: 2026-05-07
updated: 2026-10-06
created_by: claude-starter-pack
client: ~
tags: [template, agents-manifest]
---

<purpose>
{{BUSINESS_CONTEXT}}: your own business work - offers you produce, content you create, internal projects, education materials, your own tooling.

Distinct from `_CLIENTS/` (per-engagement) and `_APPS/` (tools you build for reuse). Workspace roots start with `_` and capitals so they sort first in Finder; everything inside them is named in lowercase kebab-case.
</purpose>

<scope>
## What lives here
- **`projects/`** - internal initiatives (rebrand, new offering, ops automation)
- **`education/`** - learning materials you create or consume (courses, talks, workshops)
- **`research/`** - generic research outputs (market scans, competitor analysis, technology evaluations)
- **`docs/`** - internal documentation (your own playbooks, processes, templates)
- **`scripts/`** - small utilities for your own workflow
</scope>

<conventions>
- Each folder in `projects/{name}/` is its own project: once it outgrows a single file, run `/setup` there (type Business) so it gets its own CLAUDE.md, WORKSTATE.md and worklog.md
- Research files: `{topic}-research-{YYYY-MM-DD}.md`, written by the `research` skill
- Versioned content (offers, talks): use `vN-` prefix or date in filename, archive older versions in subdirectory
- Never expose this content to client deliverables verbatim - internal voice differs from client-facing
</conventions>

<documentation>
WORKSTATE.md (live state) and worklog.md (history) per the `documentation-standard` rule; `/checkpoint` and `/end` keep them current.
</documentation>
