<purpose>
Client engagement: {{CLIENT_NAME}}.

Replace this placeholder with a one-line description of what you're doing for this client.
</purpose>

<client>
- **Company:** {{CLIENT_NAME}}
- **Industry / segment:** {{INDUSTRY}}
- **Engagement type:** {{ENGAGEMENT_TYPE}}  (e.g. fractional advisory, project-based, retainer)
- **Key contacts:** {{NAMES_AND_ROLES}}
- **Communication language:** {{LANGUAGE}}  (e.g. Czech with client; English in internal docs)
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
| `docs/knowledge-base/` | Curated knowledge about the client — Claude reads as source of truth |
| `docs/knowledge-base/drafts/` | Staging from inbox-processor — review before promoting |
| `docs/meetings/` | Meeting transcripts and summaries |
| `docs/inbox/` | Drop documents here → auto-extracted to knowledge-base/drafts |
| `docs/inbox/done/` | Processed files (originals after extraction) |
| `docs/research/` | Per-topic research outputs |
| `projects/` | Concrete client projects (one subfolder each) |
| `research/` | Generic research outside any specific project |
| `notes.md` | Brain dump (`→ research` marker triggers auto-research) |
| `log.md` | Audit trail of automated actions |
</structure>

<constraints>
- Never expose internal pricing, prompts, or tooling to client-facing outputs
- `docs/knowledge-base/drafts/` is staging — Claude must NOT read as source of truth, only review
- `docs/inbox/` is for processing only, not for context
- Communication with client follows the language set above
</constraints>

<documentation>
Per-feature / per-project docs live inside `projects/{project}/docs/`. Top-level `docs/` is for client-level knowledge that crosses projects.
</documentation>
