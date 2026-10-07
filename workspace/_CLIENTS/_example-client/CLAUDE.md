---
type: core
title: "CLAUDE"
status: active
summary: "Example client engagement: client and scope placeholders, the folder structure for knowledge base, meetings, projects and research, and the constraints for client work."
created: 2026-05-01
updated: 2026-10-06
created_by: claude-starter-pack
client: ~
path: _CLIENTS/_example-client/CLAUDE.md
tags: [agents-manifest]
version: "1.0.0"
---

<purpose>
Client engagement: {{CLIENT_NAME}}.

Replace this placeholder with a one-line description of what you're doing for this client.
</purpose>

<client>
- **Company:** {{CLIENT_NAME}}
- **Industry / segment:** {{INDUSTRY}}
- **Engagement type:** {{ENGAGEMENT_TYPE}}  (e.g. fractional advisory, project-based, retainer)
- **Key contacts:** {{NAMES_AND_ROLES}}
- **Communication language:** {{LANGUAGE}}  (e.g. the client's language with the client; English in internal docs)
</client>

<scope>
## What this engagement covers

{{HIGH_LEVEL_SCOPE}}

## Tech stack (if relevant)

{{TECH_STACK}}
</scope>

<structure>
| Path | Purpose |
|------|---------|
| `docs/knowledge-base/` | Curated knowledge about the client - Claude reads it as source of truth |
| `docs/knowledge-base/drafts/` | Unreviewed extracts - review before promoting |
| `docs/meetings/` | Meeting transcripts and summaries |
| `projects/` | Concrete client projects (one subfolder each, each with its own `research/`) |
| `research/` | Client-level research outside any project (`{topic}-research-{YYYY-MM-DD}.md`) |
| `worklog.md` | One row per checkpoint |
</structure>

<constraints>
- Never expose internal pricing, prompts, or tooling to client-facing outputs
- `docs/knowledge-base/drafts/` is staging - Claude must NOT read it as source of truth, only review
- Communication with the client follows the language set above
</constraints>

<documentation>
Per-feature / per-project docs live inside `projects/{project}/docs/`. Top-level `docs/` is for client-level knowledge that crosses projects.
</documentation>
