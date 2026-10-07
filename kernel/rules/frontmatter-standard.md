---
paths:
  - "**/*.md"
type: core
title: "Frontmatter standard"
status: active
summary: "The small YAML header every markdown document carries, so an agent can tell what a file is, whether it is current and what it says without reading the body: seven closed types, six statuses, a kind tag, and where the header goes on skills, agents and system files."
created: 2026-06-16
updated: 2026-10-06
created_by: claude-starter-pack
client: ~
tags: [rule, standard, frontmatter]
---

<frontmatter_standard>

# Frontmatter

Every markdown document you write starts with a small YAML header (except files written for people, listed below), so an agent can tell what the file is, whether it is current and what it says without reading the body. This rule loads only when you read or write a `.md` file.

## The header

```yaml
---
type: research              # one of the 7 types below
title: "Human-readable title"
status: draft               # draft | review | active | superseded | deprecated | cancelled
summary: "1-3 sentences: what the document says."
created: 2026-10-06         # YYYY-MM-DD
updated: 2026-10-06         # refresh on every meaningful change
created_by: <author>        # a person's slug, or the skill or agent that wrote it
client: <client-slug>       # ~ for the user's own work
tags: [research, postgres, pricing]
---
```

Optional, only when they help: `path` (the file's path from the workspace root, for files read out of context; update it when the file moves), `resource` (URL of the underlying source or recording), `version` (quoted, `"1.2.0"`, for documents you version on purpose), `superseded_by` (with `status: superseded`). Research files add `depth: standard | deep`.

## type: seven closed values

| type | holds |
|---|---|
| `core` | system files: CLAUDE.md, rules, skills, agents, templates, journals |
| `strategy` | decision records and direction above any one build: ADRs, decisions, strategy, positioning |
| `product_design` | defining and planning one thing to build: PRD, spec, plan, roadmap, risks, design work |
| `research` | research and findings |
| `devops` | building, testing and running: reviews, audits, test plans, runbooks, setup guides, changelogs |
| `context` | reference: methodology, best practices, guides, standards |
| `notes` | capture: notes, idea files, brainstorms, meetings, transcripts |

A decision record is `strategy` even when it is about a product; working out a specific thing to build is `product_design`. Never invent a new type: the finer kind goes in `tags`.

## status: six closed values

`draft` in progress; `review` waiting for someone's sign-off; `active` current and in force; `superseded` replaced by `superseded_by`; `deprecated` aged out with no replacement; `cancelled` switched off on purpose.

What you write on your own and no human has reviewed stays `draft`, research included. Only the user moves a document to `review` or `active`. Status tells you how far to trust a file; it never stops you reading or using one.

## tags

Lowercase kebab-case, one form per concept (`postgres`, not `pg`), used generously: first the kind of document, then technologies and topics. Kind tags come from this list; add to it rather than invent one on the fly:
- core: `agents-manifest`, `rule`, `skill`, `agent`, `template`, `readme`, `workstate`, `worklog`, `bugs`, `tech-debt`, `decision-log`
- strategy: `adr`, `decision`, `strategy`
- product_design: `prd`, `spec`, `plan`, `roadmap`, `risks`, `design`
- research: `research`, `deep-research`
- devops: `review`, `audit`, `test-plan`, `runbook`, `setup-guide`, `changelog`, `feature-doc`
- context: `methodology`, `best-practice`, `guide`, `standard`
- notes: `note`, `idea-file`, `brainstorm`, `meeting`, `transcript`

## Where the header goes

- **Documents:** the full header at the top.
- **Skills (`SKILL.md`):** `name` and `description` stay top-level, because Claude Code reads `description` to decide when to use the skill; the other fields go under `metadata:`.
- **Agents (`agents/*.md`):** `name`, `description`, `tools` and `model` stay top-level; the other fields may sit top-level or under `metadata:`.
- **`CLAUDE.md`, rules and journals** (`WORKSTATE.md`, `worklog.md`, `BUGS.md`, `TECH-DEBT.md`, `docs/decision-log.md`): a short header is enough (`type: core`, the kind tag, `summary`, dates, `created_by`); the journal templates in `~/.claude/templates/` show it. Claude Code strips the header before loading `CLAUDE.md` or a rule into a session, so it costs no context there; reading the file shows it.
- **Idea files** follow the header the `idea-file-creator` skill defines.
- **Files written for people** (a repository's `README.md`, a guide in `docs/guides/`, anything sent or published): no header, because readers would see it as raw text at the top.
- `description` belongs only on skills and agents; documents use `summary`.

</frontmatter_standard>
