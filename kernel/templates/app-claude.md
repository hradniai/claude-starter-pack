---
type: notes
title: "app-claude"
status: approved
summary: "Template for documenting app purpose, status, tech stack, architecture, usage, and feature-specific documentation."
created: 2026-05-01 00:00
updated: 2026-05-01 00:00
owner: Šimon Hradní
client: ~
path: kernel/templates/app-claude.md
tags: [note]
version: "1.0.0"
release: latest
---

<purpose>
{{APP_NAME}}: {{ONE_LINE_DESCRIPTION}}
Purpose: {{WHO_IS_IT_FOR_AND_WHY}}
</purpose>

<product>
- Status: {{draft | prototype | mvp | production | archived}}
- Tech stack: {{TECH_STACK}}
- Exposed as: {{standalone | CC skill | CC plugin | MCP server | API | internal tool}}
- Skill name: {{/SKILL_NAME if applicable}}
</product>

<architecture>
{{KEY_DECISIONS — fill as project evolves}}
</architecture>

<usage>
## How to use
{{USAGE_INSTRUCTIONS}}

## How to develop
{{DEV_SETUP}}
</usage>

<documentation>
Per-feature documentation — every concern gets its own file in docs/features/.
One page = one MD file. Larger topics = subdirectory. Mix granularity freely.
Doc changes belong in the same commit as code changes.
If this app has a linked skill in ~/.claude/skills/, keep SKILL.md in sync with changes.
</documentation>
