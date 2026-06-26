---
type: context
title: "Document frontmatter standard"
status: approved
summary: "The unified YAML frontmatter standard for every markdown artifact - an OKF-aligned superset with closed type buckets, a lifecycle status, and a predefined tag vocabulary, so an agent can orient from the frontmatter alone."
created: 2026-06-16 16:59
updated: 2026-06-16 16:59
owner: Šimon Hradní
client: ~
path: ~/.claude/rules/frontmatter-standard.md
tags: [methodology, standard, frontmatter, okf, documentation, claude-code]
version: "1.0.0"
release: latest
---

# Document frontmatter standard

<purpose>
One YAML frontmatter standard for every markdown artifact (decision docs, design artifacts, research, plans, notes, client work) plus, where the loader allows, Claude Code skills/agents/plugins and always-loaded system docs. The frontmatter exists so an AI agent loads ONLY the frontmatter and instantly knows what the file is, whether it is current, and what it does, then decides whether to read the body. This is an on-demand REFERENCE (read by tooling and skills when needed), deliberately NOT an always-loaded rule, so it does not cost context every session. A one-line pointer to it lives in `documentation-standard.md`.

This standard is an opinionated SUPERSET of Google's Open Knowledge Format (OKF v0.1, https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): it keeps the OKF-shaped core and adds governance fields OKF deliberately omits. Conformant outward, opinionated inward.
</purpose>

## Hard rules (top)

- `type` is a CLOSED 7-value bucket. Never invent a new `type` value ad hoc - extend the closed set by editing THIS file.
- `status` is a CLOSED 6-value enum.
- `type` is the COARSE bucket; the FINE kind of a document lives in `tags`, not in `type`.
- Sub-kind tags are a governed closed set (this file). Technology and topic tags are an extensible seed list.
- `summary` goes on every document. `description` goes ONLY on skills/agents (where a loader actually reads it as a trigger).
- Dates are ISO 8601 `YYYY-MM-DD`. Never use a `_at` suffix (that is a database convention, wrong for frontmatter).

## Schema (common core - every document)

```yaml
---
type: product_design        # one of 7 closed buckets (see below)
title: "Human-readable title"
status: active              # draft|review|active|superseded|deprecated|cancelled
summary: "1-3 sentences: what the document says."
created: 2026-06-16         # ISO 8601, YYYY-MM-DD
updated: 2026-06-16         # ISO 8601, same format
created_by: jane            # author slug
client: acme                # client slug; empty (~) when it is own/internal work
path: projects/x/file.md    # path relative to the workspace root; maintained by tooling, never by hand
tags: [prd, postgres, n8n, ai-strategy]   # predefined vocabulary, used generously
resource: "https://..."     # OPTIONAL, OKF-aligned: URI to the underlying asset, when relevant
---
```

## Field reference

- **`type`** - the coarse bucket. Closed 7-value set. The single mandatory discriminator (also satisfies OKF's only hard requirement: a non-empty `type`).
- **`title`** - human-readable title; if omitted, a consumer may derive it from the filename.
- **`status`** - lifecycle state. Closed 6-value enum (below).
- **`summary`** - 1-3 sentence machine-readable abstract of WHAT the document says. Loaded speculatively, so keep it tight (token-cheap). This is OKF's `description` renamed (to avoid colliding with the skill/agent `description` trigger).
- **`created` / `updated`** - ISO 8601 dates (`YYYY-MM-DD`), both in the same format. `updated` is refreshed on every meaningful change. (Two dates by design, not OKF's single `timestamp`; backed by Dublin Core / schema.org.)
- **`created_by`** - author slug (e.g. `jane`). Anchored to Dublin Core `creator`.
- **`client`** - client slug (e.g. `acme`); EMPTY (`~`) when the artifact is own/internal. Explicit here (not only in `path`) for self-sufficiency and filtering. A finer `project` field may be added later if needed.
- **`path`** - the file's own path relative to the workspace root. Maintained by tooling/migration (regenerated on move), never by hand. Keeps the frontmatter self-describing when decontextualized (vector-store indexing, pasting) - which is why domain can be left out of a dedicated field.
- **`tags`** - predefined-vocabulary labels (list, lowercase, kebab-case), used generously. Carry the fine kind, technology, and topic (and the domain that was dropped as a dedicated field).
- **`resource`** - OPTIONAL OKF-aligned URI to the underlying asset the document describes (e.g. research -> source, meeting -> recording, client_analysis -> deliverable).
- **`description`** - NOT on documents. ONLY on skills/agents, where the loader reads it as a "use when" trigger.

## `type` - the 7 closed buckets

| type | what it holds |
|---|---|
| `core` | system/infra files: readme, workstate, worklog, CLAUDE.md, AGENTS.md, skills, agents, plugins, memory, bugs, tech-debt |
| `strategy` | recorded decisions + standalone direction ONLY: adr, decision, strategy/positioning docs |
| `product_design` | defining/planning/designing/de-risking a specific build: prd, spec, plan, roadmap, risks, open-questions + the whole design pipeline |
| `research` | research, deep-research, findings, syntheses |
| `devops` | dev/test/ops: review, audit, test-plan, runbook, deployment/setup guide, implementation-report, changelog, server work |
| `context` | reference / how-to-think: methodology, best-practice, prompting playbooks, model guides, handbooks, standards (this file) |
| `notes` | capture: note, idea-file, brainstorm, meeting, transcript, discussion |

### The strategy vs product_design boundary (the hard nuance)

They are not levels of importance - they are two different KINDS of activity.

- **`strategy`** = a record of a decision, or a standalone direction. Durable, often cross-cutting, sits above any single build. ONLY three kinds: `adr`, `decision`, `strategy`.
- **`product_design`** = the work of defining/planning/designing/de-risking ONE specific thing being built. Everything else in that space.

**Test:** "Is this a decision record or a standalone strategic direction?" -> `strategy`. "Am I working out / defining / planning / designing a specific thing to build?" -> `product_design`.

- `open-questions`, `risks`, `roadmap` of a build go to `product_design` (they are working docs of the build).
- `adr` stays `strategy` even when it is about a product - it is a decision RECORD, not a design artifact.
- A general directional `decision` is `strategy`; design choices logged during a build are tag `design-decision` inside `product_design`.
- Default for `plan`/`prd`/`spec`/`risks`/`roadmap` is `product_design`. The rare exception - a pure business plan/roadmap with no specific build - is `strategy`.

## `status` - the 6 closed values

| value | meaning |
|---|---|
| `draft` | in progress, not yet in force |
| `review` | waiting for someone else's review/sign-off (anticipates collaboration) |
| `active` | current, in force |
| `superseded` | replaced by a specific successor (reference it via `superseded_by`) |
| `deprecated` | aged out, no replacement |
| `cancelled` | deliberately switched off (even from active), no replacement, without having aged out |

## `tags` - the predefined vocabulary

Tags are the one deliberately rich field. Used generously (one tag is ~1-2 tokens; 30 tokens of tags beats making an agent read the body). Governed by a predefined vocabulary in three families.

### Family 1 - sub-kind (CLOSED, governed here)

The fine kind of the document (what `type` used to try to be). Grouped by the bucket they usually sit under:

- **core:** `readme`, `workstate`, `worklog`, `claude-config`, `agents-manifest`, `skill`, `agent`, `plugin`, `memory`, `bugs`, `tech-debt`
- **strategy:** `adr`, `decision`, `strategy`
- **product_design:** `prd`, `spec`, `plan`, `roadmap`, `risks`, `open-questions`, `discovery`, `persona`, `personas-overview`, `jobs-to-be-done`, `information-architecture`, `visual-style`, `user-flow`, `edge-cases`, `error-handling`, `design-decision`, `design-state`, `design-feedback`, `wireframes`, `prototype`
- **research:** `research`, `deep-research`, `findings`, `synthesis`
- **devops:** `review`, `audit`, `test-plan`, `smoke-checklist`, `runbook`, `deployment-guide`, `setup-guide`, `implementation-report`, `changelog`, `feature-doc`
- **context:** `methodology`, `best-practice`, `prompting-playbook`, `model-guide`, `handbook`, `standard`
- **notes:** `note`, `idea-file`, `brainstorm`, `meeting`, `transcript`, `discussion`

A sub-kind tag is added to this list (not invented ad hoc). A sub-kind that becomes common enough may later be promoted to its own `type` bucket if it earns it.

### Family 2 - technology (SEED, extensible)

Add the technologies a document concerns, so an agent sees the stack without reading the body. Seed list (extend as new tech appears):
`postgres`, `paradedb`, `pgvector`, `n8n`, `nextjs`, `react`, `typescript`, `python`, `claude-code`, `docker`, `caddy`, `supabase`, `drizzle`, `tailwind`, `gemini`, `openai`, `anthropic`, `notion`.

### Family 3 - topic / domain (SEED, extensible)

The subject area (this is where the dropped `category` domain lives). Seed list (extend as needed):
`ai-strategy`, `ai-transformation`, `governance`, `security`, `compliance`, `gdpr`, `ai-act`, `onboarding`, `pricing`, `positioning`, `automation`, `rag`, `memory`, `content`, `sales`, `hiring`.

### Tag rules

- list, lowercase, kebab-case (`ai-strategy`, not `AI Strategy`).
- One canonical form per concept (`postgres`, not `pg`/`PostgreSQL`/`psql`).
- Generous count is encouraged; the budget is for orientation, not minimalism.
- Sub-kind tags are closed (edit this file to add). Technology/topic tags extend freely but reuse the canonical form.

## Per-loader rules (where the file is loaded by Claude Code)

- **Documents** (plain markdown in folders): full common core, flat, at the top of the file.
- **Skills (`SKILL.md`):** keep `name` + `description` TOP-LEVEL (loader-reserved; `description` is the functional trigger). Put the standard's fields under the official `metadata:` block. Use `type: core`, tag `skill`.
- **Agents (`.claude/agents/*.md`):** keep `name`/`description`/`tools`/`model`/`color` top-level (`description` = trigger). The loader ignores unknown keys, so the standard's fields may sit top-level; nesting them under `metadata:` for symmetry with skills is also fine. Use `type: core`, tag `agent`.
- **Plugins (`plugin.json`, JSON not markdown):** nest the standard's fields under a `metadata` object - top-level extra keys pass `claude plugin validate` but FAIL `--strict`. Use `type: core`, tag `plugin`.
- **System always-loaded docs (`CLAUDE.md`, `AGENTS.md`, `MEMORY.md`, `WORKSTATE.md`, `README.md`):** MINIMAL frontmatter only - `type: core`, the matching sub-kind tag (`claude-config`/`agents-manifest`/`memory`/`workstate`/`readme`), `created`, `updated`, `created_by`, `summary`. Auto-load STRIPS the frontmatter (zero token cost, no instruction-hijack); an explicit Read tool DOES see it (so cross-workspace discovery works). Do NOT add heavy/per-kind fields here.

## Per-kind extension fields (flat, alongside the core)

Some kinds carry extra fields. Add them flat, next to the core.

- **adr** (`type: strategy`, tag `adr`): `id`, `domain` (closed vocab), `scope` (project|global), `supersedes`, `superseded_by`, `workspace`, `project`, `subproject`.
- **idea-file** (`type: notes`, tag `idea-file`): `handoff` (internal|handoff), `location`, `superseded_by`.
- **research** (`type: research`, tag `research`): `depth` (standard|deep) - this replaces a separate `deep-research` type.
- Other kinds add fields only when they genuinely need them.

## Relationship to OKF (conformant superset)

| our field | OKF | note |
|---|---|---|
| `type` (closed) | `type` (open, required) | we close the vocabulary; still satisfies OKF's only hard rule |
| `title` | `title` | same |
| `summary` | `description` | renamed (skills/agents keep `description` as the trigger) |
| `tags` | `tags` | same |
| `created` + `updated` | `timestamp` | we split into two ISO dates |
| `resource` | `resource` | same, optional |
| `status`, `client`, `path`, `created_by`, per-kind | (custom keys) | OKF-tolerated additional keys; our governance layer |

OKF reserves `index.md` (directory listing) and `log.md` (history); our per-folder indexes and `worklog.md` play the same roles. OKF is v0.1 and will change - keep names roughly aligned where they nearly match.

## Migration (one-time, no grandfathering)

The standard supersedes any earlier ADR and idea-file frontmatter conventions. One large migration (run cheaply, e.g. on Haiku) brings ALL relevant documents into line; nothing is left half-converted. The migration also: reconciles an ADR `date` -> `created` (+ `created_by`), reconciles idea-file `type: internal|handoff` -> `type: notes` + `handoff` field, and sets `path` on every file. The `adr` skill (if present) and the idea-file convention/skill are updated to emit the standard.

## Hard rules (bottom, repeated)

- `type` = 7 closed buckets; never invent values ad hoc (edit this file). The FINE kind goes in `tags`, not `type`.
- `status` = 6 closed values.
- `summary` everywhere; `description` only on skills/agents.
- Dates ISO `YYYY-MM-DD`, no `_at`.
- Sub-kind tags are closed (edit this file); technology/topic tags extend with a canonical form.
- Per-loader: skills -> `metadata:` block; plugins -> nested `metadata`; always-loaded system docs -> minimal core only.
- We stay OKF-conformant (non-empty `type`); the standard is OKF + a governance layer.
