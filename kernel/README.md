---
type: core
title: "Kernel - install into ~/.claude"
status: approved
summary: "What the Claude Code starter-pack kernel ships (settings, hooks, rules, skills, agents, templates, scripts) and how to install it into ~/.claude as a merge."
created: 2026-06-16 16:59
updated: 2026-06-16 16:59
owner: Šimon Hradní
client: ~
tags: [readme, claude-code, setup-guide]
version: "1.0.0"
release: latest
path: kernel/README.md
---

# Kernel - install into `~/.claude`

The kernel is the Claude Code baseline. Installing it is **merge, not replace** - if you already have a `~/.claude/` setup, nothing is overwritten blindly; review and keep what's yours.

## What's in here

- `settings.json` - restrictive permission baseline (destructive bash, sensitive file reads, force-push, `--no-verify` all denied; bypass mode locked off) + `cleanupPeriodDays: 3650` (keep conversation history 10 years instead of the 30-day default).
- `hooks/` - `bash-safety-extended.py` (blocks command-safety bypasses AND enforces the env-secret tiers), `context-bloat-guard.py` (brake on huge file reads), `inject-current-time.sh` (current time into every prompt).
- `rules/` - `documentation-standard.md` (docs + idea-file methodology + frontmatter pointer), `respect-denies.md` (denies + the three env tiers), `subagent-rules.md`, `language.md`, `notes-convention.md`, `frontmatter-standard.md` (on-demand reference: the unified YAML frontmatter standard).
- `skills/` - `setup` (project scaffolding: AGENTS.md + symlink, ignore/env templates, local git safety net), `prd-creator`, `skill-creator`, `dr-prompt`.
- `agents/` - `prompt-engineer` (model-aware prompt/skill/agent authoring with a self-contained two-tier validation: sanity + single-judge subagent, no external app), `research-analyst` (focused single-topic research, self-contained verdict inline).
- `templates/` - scaffolding templates used by the `setup` skill: the `*-claude.md` AGENTS.md seeds, the universal `gitignore` + `claudeignore`, the per-type `*-env.example` schemas (`klient`, `dev`, `app`, `general`), and `env-shared.example` (the soft env tier).
- `scripts/list-env-keys.sh` - shows env var NAMES without ever revealing values (`--classify` adds each key's state: empty / placeholder / filled-kind).
- `scripts/env-key-classify.py` - the classifier `list-env-keys.sh --classify` delegates to (reads a value only to label it; never emits it).
- `scripts/git-autosave.sh` - local-only git safety net (`ensure` = init + safe `.gitignore`; `commit` = local checkpoint). Never pushes; uses your own global git identity.
- `scripts/trust-workspace.sh` - pre-approves your working directories for the "Do you trust the files in this folder?" gate (the only supported way to stop that nag; bypass mode stays off).
- `statusline.sh` - live status line.

## Install (review each step, do not run blind)

1. Back up any existing config: `cp -r ~/.claude ~/.claude.bak-$(date +%Y%m%d-%H%M%S)`.
2. Copy the kernel contents into `~/.claude/` (merge - keep your existing rules/skills, add these).
3. Make hooks and scripts executable: `chmod +x ~/.claude/hooks/* ~/.claude/scripts/*`.
4. Optional - stop the "Do you trust the files in this folder?" prompt for the directories you work in: `~/.claude/scripts/trust-workspace.sh ~/path/to/project-a ~/path/to/project-b` (or `--all` to trust every directory Claude already knows). It backs up and merges `~/.claude.json`, never overwrites, and does not weaken permissions or unlock bypass mode. Run it from a plain terminal with no Claude session open.
5. Restart Claude Code so `settings.json` takes effect.
6. Sanity check: ask Claude the current time (time hook), and confirm a denied command (e.g. `cat .env`) is blocked.

If you use Codex or Cursor: the rules and skills (the methodology) apply via `AGENTS.md`; the `settings.json`/hooks are Claude Code-specific.
