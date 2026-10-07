---
type: core
title: "client-claude"
status: active
summary: "CLAUDE.md seed for a client engagement: client and scope blocks, the folder structure, and the constraints for client work."
created: 2026-05-07
updated: 2026-10-06
created_by: claude-starter-pack
client: ~
tags: [template, agents-manifest]
---

<purpose>
Client project: {{CLIENT_NAME}}
{{ONE_LINE_DESCRIPTION}}
</purpose>

<client>
- Company: {{CLIENT_NAME}}
- Industry/segment: {{INDUSTRY}}
- Engagement type: {{ENGAGEMENT_TYPE - e.g. fractional advisor, project-based, retainer}}
- Key contacts: {{CONTACTS}}
- Communication language: {{LANGUAGE}} (with the client; internal docs stay English)
</client>

<scope>
## What we're building/doing
{{DESCRIPTION}}

## Tech stack (this project)
{{TECH_STACK}}
</scope>

## Structure

| Path | Purpose |
|------|---------|
| `docs/knowledge-base/` | Knowledge about the client - AI reads as source of truth |
| `docs/knowledge-base/drafts/` | Unreviewed extracts (e.g. a summary of a client document) - AI MUST NOT read as source of truth until promoted |
| `docs/meetings/transcripts/` | Raw meeting transcripts |
| `docs/assets/` | Logos, images, active visual materials |
| `docs/presales/` | Proposals, discovery, scope |
| `docs/strategy/` | Strategic documents (versioned) |
| `docs/strategy/archive/` | Previous major versions |
| `docs/review/` | Documents waiting for review before they go to the client |
| `docs/final/` | Finalized deliverables |
| `projects/` | Concrete projects (each in its own subfolder, with its own `research/`) |
| `research/` | Client-level research outside any project (`{topic}-research-{YYYY-MM-DD}.md`) |
| `docs.md` | Index of finalized documents with links |
| `meetings.md` | Meeting index - when, topic, key points |
| `WORKSTATE.md` | Live state of the engagement: focus, next step, captured TODO notes |
| `worklog.md` | Work history, one row per checkpoint plus dated notes - basis for invoicing |

<constraints>
- Shared methodology and personal profile: `~/Documents/_CONTEXT/` (a workspace root: `_` and capitals sort it first in Finder; the profile in it is imported by your global `~/.claude/CLAUDE.md`)
- Communication language with the client: set per engagement - see the `<client>` block above
- Never expose internal tooling, pricing, or other personal context to client-facing outputs
- This client's material stays in this folder: never reuse it in another client's work or in general files
- Anything that goes to the client is reviewed by you first; Claude prepares it, you send it
- `docs/knowledge-base/drafts/` is staging - AI must NOT read it as source of truth, only review and promote
</constraints>

<documentation>
WORKSTATE.md and worklog.md per the `documentation-standard` rule. A project in `projects/` is a sub-project with its own WORKSTATE.md and worklog.md; this file stays the only CLAUDE.md.
Doc changes belong in the same commit as the work they describe.
</documentation>
