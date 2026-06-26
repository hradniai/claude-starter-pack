---
name: setup
description: Initialize or restructure a project workspace with AGENTS.md (canonical) and CLAUDE.md symlink, directory scaffolding, and optional skill linking. Use instead of /init for structured project setup. Triggers on "setup project", "init project", "/setup".
metadata:
  type: core
  status: active
  summary: "Initialize or restructure a project workspace: AGENTS.md + CLAUDE.md symlink, directory scaffolding, ignore/env templates, local git safety net."
  created: 2026-06-10
  updated: 2026-06-16
  created_by: Šimon Hradní
  client: ~
  tags: [skill, setup, scaffolding]
---

# Project Setup

Interactive project scaffolding. Replaces /init with structured project type selection.

**File convention:** AGENTS.md is the canonical project intent file (cross-tool standard adopted by Cursor, Codex, Gemini CLI, Aider, etc.). CLAUDE.md is a symlink to AGENTS.md so Claude Code reads the same content natively. Both files always point to the same source. The deeper tool-specific config (`.claude/rules/`, `.claude/settings.json`, hooks) stays Claude Code-specific.

## Step 1: Detect context

1. Note the current working directory (CWD).
2. Check if AGENTS.md or CLAUDE.md exists in CWD (either is a sign the project was already scaffolded).
3. Check if README.md exists.
4. Scan directory for existing files/folders (ls -la, max 2 levels).

## Step 2: Ask project type

Present these options to the user:

```
Project setup for: {CWD basename}

1. Klient   - per-client engagement (typically lives in _CLIENTS/{name}/)
2. Business - your own business work (typically lives in _BUSINESS/projects/{name}/)
3. App      - tool/app you build for reuse (typically lives in _APPS/{name}/)
4. Dev      - generic development project (any location)
5. General  - community, initiative, research, experiment (any location)
6. Just clean up - keep existing AGENTS.md/CLAUDE.md, add missing references
```

Wait for the user's choice. Do NOT proceed without it.

## Step 3: Gather info

Based on choice, ask the user for template placeholders. Use directory name as default project name. Ask only what's needed - skip optional fields unless the user wants to fill them.

**Klient:** CLIENT_NAME, INDUSTRY, ENGAGEMENT_TYPE, ONE_LINE_DESCRIPTION
**Business:** BUSINESS_CONTEXT (e.g. "consulting offering rebuild", "course development", "internal automation")
**App:** APP_NAME, TECH_STACK, ONE_LINE_DESCRIPTION, exposure type (skill/plugin/API/standalone)
**Dev:** PROJECT_NAME, TECH_STACK, ONE_LINE_DESCRIPTION
**General:** PROJECT_NAME, type (community/initiative/research/experiment), ONE_LINE_DESCRIPTION
**Clean up:** No questions - just scan and update.

## Step 4: Create AGENTS.md (canonical) + CLAUDE.md symlink

- Read template from `~/.claude/templates/{type}-claude.md`:
  - Klient → `klient-claude.md`
  - Business → `business-claude.md`
  - App → `app-claude.md`
  - Dev → `dev-claude.md`
  - General → `general-claude.md`
- Fill in placeholders with user's answers.
- Write the filled content to `AGENTS.md` (NOT CLAUDE.md - AGENTS.md is canonical).
- Create `CLAUDE.md` as a symlink to `AGENTS.md` so Claude Code reads it natively:
  ```bash
  ln -s AGENTS.md CLAUDE.md
  ```
- If AGENTS.md already exists, show diff preview and ask for confirmation before overwriting.
- If CLAUDE.md exists as a regular file (legacy), ask the user whether to:
  (a) migrate: rename CLAUDE.md → AGENTS.md, then create CLAUDE.md symlink
  (b) keep as-is and skip
- If CLAUDE.md is already a symlink to AGENTS.md, do nothing - already in the right state.
- For option 5 (clean up): read existing AGENTS.md/CLAUDE.md, scan directory structure, add missing references. Do NOT replace.

Note: the template filenames keep `-claude.md` suffix as a legacy internal label. Their content is written to AGENTS.md regardless.

## Step 5: Scaffold directories

Create only what doesn't already exist. Never overwrite existing files.

**All types:**
- `.claude/rules/` (empty directory)
- `notes.md` (skeleton: `# Notes\n\nIdeas, brain dumps, future automations.`)
- `research/` (empty directory)
- `.gitignore` and `.claudeignore` from the standard templates (single source of truth - never hand-write them inline):
  ```bash
  [ -f .gitignore ]    || cp ~/.claude/templates/gitignore .gitignore
  [ -f .claudeignore ] || cp ~/.claude/templates/claudeignore .claudeignore
  ```
  Both are copy-if-missing (never overwrite). The `.claudeignore` is deliberately permissive: it only keeps heavy/derived dirs out of auto-loaded context (token hygiene), it is NOT a security boundary - secret blocking lives in `settings.json` deny + the `bash-safety-extended.py` hook.
- `.env.example` (type-specific schema) + `.env.shared` (soft tier), copy-if-missing. Map the project type to the template: Klient→`klient`, Dev→`dev`, App→`app`, General/Business→`general`.
  ```bash
  [ -f .env.example ] || cp ~/.claude/templates/{type}-env.example .env.example   # {type} = klient|dev|app|general
  [ -f .env.shared ]  || cp ~/.claude/templates/env-shared.example .env.shared
  ```
  These are EMPTY schemas with requirement notes in `#` comments, NEVER real values (a weak example value like `password=changeme` would teach Claude to generate weak secrets). `.env.example` documents which keys this workspace type uses; real secrets go in `.env` (HARD, Claude never reads), soft low-risk values go in `.env.shared` (Claude-readable). Account-level keys are NOT per-project - they live in the global `~/.claude/.env`. See `respect-denies.md` for the three env tiers.

> **Secrets convention.** `.env` and `.env.*` are gitignored, and Claude is hard-blocked from reading their values (deny rules + the `bash-safety-extended.py` hook, which covers `cat`/`source`/redirection/`python -c`/docker-mount and the `Read` tool). The ONE readable env file is **`.env.shared`** - the soft tier for low-risk values safe to surface (a notify webhook, a contact email). `.env`, `.env.local`, `.env.production` and every other `.env.*` are HARD: their values never reach Claude (`.env.local` is HARD on purpose - the JS ecosystem treats it as the live-secret file, so live keys land there). Placeholders (`.env.example`/`.sample`/`.template`) are readable. To learn the key NAMES of a hard env without exposing values, Claude runs `~/.claude/scripts/list-env-keys.sh --from <path>`; add `--classify` to also get each key's value-STATE (empty / placeholder / filled + kind, e.g. `api_key`/`token`/`webhook_url`) - the value is read only to derive the label and is never surfaced.

**Klient:**
- `docs/meetings/transcripts/`
- `docs/knowledge-base/`
- `docs/knowledge-base/drafts/`
- `docs/assets/`
- `docs/inbox/`
- `docs/inbox/done/`
- `docs/presales/`
- `docs/strategy/`
- `docs/strategy/archive/`
- `docs/research/`
- `docs/review/`
- `docs/final/`
- `projects/`
- Mandatory MD files (create only if they don't exist):
  - `log.md` (skeleton: `# Log\n`)
  - `docs.md` (skeleton: `# Documents\n\n| Date | Name | Google Drive URL |\n|------|------|------------------|\n`)
  - `meetings.md` (skeleton: `# Meetings\n\n| Date | Topic | Key Points |\n|------|-------|------------|\n`)
  - `worklog.md` (skeleton: `# Worklog\n\n| Timestamp | Type | Project | Description | Files |\n|-----------|------|---------|-------------|-------|\n`)

**Business:**
- `projects/`
- `education/`
- `research/`
- `docs/`
- `scripts/`

**Dev:**
- `docs/features/`
- `docs/decisions/`
- `docs/guides/setup.md` (empty skeleton with `# Setup` header)
- `src/`

**App:**
- `docs/features/`
- `docs/decisions/`
- `docs/guides/`
- `src/`
- `scripts/`
- Create skill skeleton at `~/.claude/skills/{app-name-lowercase}/SKILL.md`:
  ```
  ---
  name: {app-name-lowercase}
  description: TODO
  ---

  # {APP_NAME}

  TODO: Define skill interface.
  ```

**General:**
- `docs/`
- `scripts/`

**Clean up:**
- No directory creation. Only update AGENTS.md (or CLAUDE.md if AGENTS.md doesn't yet exist) references.

## Step 6: Create README.md

Only if README.md doesn't exist. Skeleton:

```markdown
# {PROJECT_NAME}

Created: {YYYY-MM-DD}

## Overview

{ONE_LINE_DESCRIPTION}

## Status

In progress.
```

## Step 7: Initialize local git (safety net)

Give the new workspace a local time machine from day one - local only, no GitHub, no push:

```bash
~/.claude/scripts/git-autosave.sh ensure   # git init + standard .gitignore from ~/.claude/templates/gitignore (only if missing)
git add -A && git commit -q -m "chore: scaffold project"   # first snapshot
```

Run from the workspace root. `ensure` is a no-op if git already exists; it never overwrites an existing `.gitignore`, and it does NOT set a git identity (it uses the user's own global `~/.gitconfig`). Commits stay local - pushing to GitHub is always a separate, deliberate action.

## Step 8: Summary

Report what was created:
- Files created/modified (list)
- Directories created (list)
- Skill linked (if App type)
- Next steps suggestion

Do NOT create WORKSTATE.md or MEMORY.md - those are created on-demand by documentation-standard and memory-management rules.
