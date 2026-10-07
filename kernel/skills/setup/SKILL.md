---
name: setup
description: Set up or tidy a project folder - CLAUDE.md from a project-type template, folders, .gitignore and env templates, the WORKSTATE.md and worklog.md journals, and a local git history. Use instead of /init when the user types /setup or says "set up this project", "new project", "new client folder", "init project", "scaffold this folder", or wants an existing folder brought into the standard structure.
metadata:
  type: core
  status: active
  summary: "Scaffold or tidy a project: CLAUDE.md from a type template, folders, ignore and env templates, WORKSTATE.md + worklog.md, and a first local commit."
  created: 2026-06-10
  updated: 2026-10-06
  created_by: claude-starter-pack
  client: ~
  tags: [skill, setup, scaffolding, claude-code]
---

# Project Setup

Interactive project scaffolding with a project-type choice, used instead of `/init`.

**File convention:** `CLAUDE.md` is the project's instructions file, which Claude Code loads into every session started in that folder. Setup writes no `AGENTS.md`.

## Step 1: Detect context

1. Note the current directory. If it is your home folder, `~/Documents` itself or a workspace root (`~/Documents/_CLIENTS`, `_BUSINESS`, `_APPS`, `_CONTEXT`), ask for the project name and create the project folder inside it first: setup scaffolds a project, never a root.
2. Check whether `CLAUDE.md` or `AGENTS.md` exists (either means the folder was set up before) and whether `WORKSTATE.md` / `worklog.md` exist.
3. List what is already there (`ls -la`, two levels at most).

## Step 2: Ask the project type

```
Project setup for: {folder name}

1. Client   - work for one client (usually in _CLIENTS/{name}/)
2. Business - your own business work (usually in _BUSINESS/projects/{name}/)
3. App      - a tool or app you build for reuse (usually in _APPS/{name}/)
4. Dev      - any other software project
5. General  - community, initiative, research, experiment
6. Clean up - keep the existing CLAUDE.md, add what is missing
```

Wait for the choice. Do not proceed without it.

## Step 3: Gather the details

Read the template for the chosen type (Step 4) and ask for the fields below in one message, using the folder name as the default project name. Its other `{{...}}` fields are optional: ask about them only if the user wants to fill more in now.

- **Client:** CLIENT_NAME, INDUSTRY, ENGAGEMENT_TYPE, ONE_LINE_DESCRIPTION
- **Business:** BUSINESS_CONTEXT (e.g. "consulting offer rebuild", "course development")
- **App:** APP_NAME, TECH_STACK, ONE_LINE_DESCRIPTION, how it is used (skill / plugin / API / standalone)
- **Dev:** PROJECT_NAME, TECH_STACK, ONE_LINE_DESCRIPTION
- **General:** PROJECT_NAME, kind (community / initiative / research / experiment), ONE_LINE_DESCRIPTION
- **Clean up:** nothing to ask; scan and fill gaps.

## Step 4: CLAUDE.md

- Template: `~/.claude/templates/{type}-claude.md` with `{type}` = `client`, `business`, `app`, `dev`, `general`.
- Fill the placeholders with the answers; for a choice list such as `{{draft | prototype | ...}}` pick the fitting value, and write `TBD` for an optional field left unanswered, so no `{{...}}` stays in the file. Drop the template's own frontmatter block (it describes the template) and give `CLAUDE.md` the minimal frontmatter the frontmatter standard sets for always-loaded docs: `type: core`, `tags: [agents-manifest]`, `created`, `updated`, `created_by`, `summary`.
- Write it to `CLAUDE.md`.
- `CLAUDE.md` already exists: show a diff preview and ask before overwriting.
- `AGENTS.md` in the folder (written by another tool): Claude Code reads it only where there is no `CLAUDE.md`, so propose moving it into `CLAUDE.md` and do it once the user agrees. A `CLAUDE.md` beside it that only points to it goes first: a symbolic link, the one line `@AGENTS.md`, or the one word `AGENTS.md` (a link that a Windows checkout turned into text, which Claude reads as a meaningless word instead of the instructions). Then rename `AGENTS.md` to `CLAUDE.md` (`git mv` when git tracks it). A `CLAUDE.md` with instructions of its own: show both and agree with the user how to merge them. If the user declines, leave both files as they are.
- **Clean up:** read the existing file, scan the folder, add missing references and, if the file has no frontmatter, the minimal block above. Never replace its content.

## Step 5: Scaffold

Create only what does not exist yet. Never overwrite a file.

**All types (Clean up included):**
- `WORKSTATE.md` and `worklog.md` from `~/.claude/templates/workstate.md` and `~/.claude/templates/worklog.md`. Fill the placeholders: `{{PROJECT}}` the project name, `{{DATE}}` today (`date '+%Y-%m-%d'`), `{{AUTHOR}}` the user's first name as a lowercase slug (from the user profile, else `claude`), `{{FOCUS}}` "Project set up; next: <the first real task, or ask>", `{{CURRENT_STATE}}` one line on what was scaffolded.

**All types except Clean up:**
- `.claude/rules/` (empty) and `research/` (research files land here as `{topic}-research-{YYYY-MM-DD}.md`).
- `.gitignore` from the standard template, never hand-written (keep `-n`, which never overwrites: the safety hook judges the `cp` even behind the `[ -f ]` test and refuses one that could replace a file):
  ```bash
  [ -f .gitignore ] || cp -n ~/.claude/templates/gitignore .gitignore
  ```
  Claude Code does not read `.claudeignore` files, so none is created; to keep Claude's file tools away from a path, add a `Read` deny rule to the project's `.claude/settings.json`.
- `.env.example` (which keys this project type uses) and `.env.shared` (the readable soft tier), copied if missing; `{type}` = `client`, `dev`, `app`, or `general` for General and Business:
  ```bash
  [ -f .env.example ] || cp -n ~/.claude/templates/{type}-env.example .env.example
  [ -f .env.shared ]  || cp -n ~/.claude/templates/env-shared.example .env.shared
  ```
  Both are empty schemas with notes in `#` comments, never real values. Real secrets go in `.env`, which Claude cannot read, and so do webhook URLs, because whoever holds one can post through it; values that grant nothing and that Claude may see (a contact email, a public URL) go in `.env.shared`; account-wide keys go in `~/.claude/.env`. To see which keys a secret file holds without exposing values, run `~/.claude/scripts/list-env-keys.sh --from <path>` (add `--classify` for each key's state: empty, placeholder or filled).

**Client:**
- `docs/meetings/transcripts/`, `docs/knowledge-base/drafts/`, `docs/assets/`, `docs/presales/`, `docs/strategy/archive/`, `docs/review/`, `docs/final/`
- `projects/` (each project inside is a sub-project with its own `research/` and journals; client-wide research goes to the root `research/`)
- `docs.md` (`# Documents\n\n| Date | Name | Link |\n|------|------|------|\n`) and `meetings.md` (`# Meetings\n\n| Date | Topic | Key Points |\n|------|-------|------------|\n`)

**Business:** `projects/`, `education/`, `docs/`, `scripts/`

**Dev:** `docs/features/`, `docs/decisions/`, `docs/guides/setup.md` (`# Setup` heading only), `src/`

**App:**
- `docs/features/`, `docs/decisions/`, `docs/guides/`, `src/`, `scripts/`
- `README.md`, the outward-facing page for people who use the app:
  ```markdown
  # {APP_NAME}

  {ONE_LINE_DESCRIPTION}

  ## Use

  ## Setup
  ```
- Only when the app is used as a skill: a skeleton at `~/.claude/skills/{app-name-lowercase}/SKILL.md`. Mention that it lives in the global Claude folder. It carries `disable-model-invocation: true` so the unfinished skill never triggers on its own; remove that line once the description is written.
  ```
  ---
  name: {app-name-lowercase}
  description: TODO - what it does and the phrases that should trigger it.
  disable-model-invocation: true
  ---

  # {APP_NAME}

  TODO: define the skill's steps.
  ```

**General:** `docs/`, `scripts/`

## Step 6: Local git history

Give the project a local history from day one: local only, no GitHub, no push. Run from the project folder:

```bash
~/.claude/scripts/git-autosave.sh ensure   # git init + standard .gitignore if missing
```

`ensure` does nothing when the folder is already a repository, never overwrites a `.gitignore`, and only acts inside `~/Documents/` (never at `~/Documents/_APPS` or `~/Documents/_CLIENTS` themselves). Then check `git rev-parse --is-inside-work-tree`: outside `~/Documents/` there is no repository, so say so and offer `git init` instead of failing silently.

First commit:
1. New repository (no commits yet): `git add -A`. If the folder already held files before setup, show the user what would be committed (`git status --short`) and ask first. Existing repository: first note what is already staged (`git diff --cached --name-only`); that is the user's, so leave it staged and out of this commit. Then stage only the files this setup created or changed, each with `git add -- <path>`. A file setup changed that already had uncommitted edits of the user's (Clean up adding frontmatter to an edited `CLAUDE.md`) stays unstaged and is named in the summary.
2. Check `git diff --cached --name-only`: unstage any `.env` / `.env.*` (other than a placeholder template such as `.env.example`), `.envrc`, `*.pem`, `*.key` or SSH key that this step staged and tell the user. Unstage it with `git rm --cached -- <path>` in a new repository (`git restore --staged` fails there, because there is no commit yet) and with `git restore --staged -- <path>` in an existing one; both keep the file on disk; one the user had staged before stays staged, with a warning that their next commit would include it.
3. New repository: `git commit -q -m "chore: scaffold project"`. Existing repository: name the paths, `git commit -q -m "chore: scaffold project" -- <the files staged in 1>`, so whatever the user had staged stays staged and out of the commit.
4. If git reports no identity ("Please tell me who you are"), ask the user for the name and email to use and run `git config --global user.name "<name>"` and `git config --global user.email "<email>"`; never invent them. Any other failure: report the exact error.

Commits from here on happen at `/checkpoint` and `/end`; a push is always a separate, deliberate step.

## Step 7: Summary

Report what was created: files, folders, the skill skeleton if any, the first commit, and a suggested next step.
