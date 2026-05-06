<purpose>
Client project: {{CLIENT_NAME}}
{{ONE_LINE_DESCRIPTION}}
</purpose>

<client>
- Company: {{CLIENT_NAME}}
- Industry/segment: {{INDUSTRY}}
- Engagement type: {{ENGAGEMENT_TYPE — e.g. fractional ATO, project-based, advisory}}
- Key contacts: {{CONTACTS}}
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
| `docs/knowledge-base/` | Knowledge about the client — AI reads as source of truth |
| `docs/knowledge-base/drafts/` | Staging area from inbox processing — AI MUST NOT read as source of truth |
| `docs/meetings/transcripts/` | Raw meeting transcripts |
| `docs/assets/` | Logos, images, active visual materials |
| `docs/inbox/` | Client materials (PDFs, presentations) → auto-processed to KB/drafts |
| `docs/inbox/done/` | Processed inbox files |
| `docs/presales/` | Proposals, discovery, scope |
| `docs/strategy/` | Strategic documents (versioned) |
| `docs/strategy/archive/` | Previous major versions |
| `docs/research/` | Per-topic research outputs |
| `docs/review/` | Documents for Council review → triggers A2 |
| `docs/final/` | Finalized documents → triggers MD-Converter to Google Docs |
| `projects/` | Concrete projects (each in own subfolder) |
| `research/` | Research outputs |
| `notes.md` | Brain dump, ideas — new notes trigger auto-research |
| `log.md` | Audit trail of automations |
| `docs.md` | Index of finalized documents with Google Drive URLs |
| `meetings.md` | Meeting index — when, topic, key points |
| `worklog.md` | Work log — basis for invoicing |

<constraints>
- Shared methodology and personal profile: `~/Documents/_CONTEXT/` (referenced from your global AGENTS.md)
- Communication language with the client: set per engagement — see the `<client>` block above
- Never expose internal tooling, pricing, or other personal context to client-facing outputs
- `docs/knowledge-base/drafts/` is staging — AI must NOT read as source of truth, only review and promote
- `docs/inbox/` is for processing only, not for context
</constraints>

<documentation>
Per-feature documentation in docs/ — every concern gets its own file.
Doc changes belong in the same commit as code changes when applicable.
</documentation>
