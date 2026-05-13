# Claude Code Starter Pack

A curated baseline configuration for Claude Code: hard safety defaults, opinionated workspace scaffolding, and a small set of bundled skills. Designed to be installed once and lived in.

> **Audience:** technically curious users (freelancers, small teams) who want Claude Code working safely from day one without spending two weeks tuning config and hooks.

## What you get

### Kernel (`~/.claude/`)
- **Restrictive `settings.json`** — destructive bash patterns, sensitive file reads, and `--no-verify` style escapes are denied at the global level. Bypass mode is locked off.
- **Safety hook** — catches two-step download-execute, subshell bypasses, and other patterns that simple deny rules miss.
- **Auto-research hook** — detects unmarked notes in `notes.md` files, dispatches background research via the Anthropic API, marks each as ✅ (research done) or ⏭️ (skipped).
- **Inbox-processor hook** — extracts knowledge from documents dropped in `docs/inbox/` to a knowledge-base drafts area.
- **Time-injection hook** — adds the current local time to Claude's context every prompt (so timestamps in notes are accurate).
- **Four baseline rules** — documentation standard, respect-denies behavior, subagent usage guide, notes convention.
- **Four bundled skills** — `setup` (project scaffolding), `skill-creator`, `prd-creator`, `dr-prompt`.
- **Helper script** — `list-env-keys.sh` lets Claude see *names* of your credential env vars without ever touching values.

### Workspace (`~/Documents/`)
- `_CONTEXT/` — your personal profile and best-practices index, read by Claude across all projects.
- `_CLIENTS/` — scaffold per client engagement. Auto-processing for inbox documents into a knowledge base.
- `_BUSINESS/` — your own business work (offers, education content, internal projects).
- `_APPS/` — small tools and apps you build, with one example (`transcribe`) included.

### File convention
Every project root has both `AGENTS.md` (canonical, cross-tool standard) and `CLAUDE.md` (symlink). One source of truth, readable by Claude Code, Cursor, Codex, Gemini CLI, Aider, and any other AGENTS.md-aware tool.

## New to Claude Code?

If your AI experience so far is *"I have a project in claude.ai and I ask it things,"* start with **[`USER-MANUAL.md`](USER-MANUAL.md)** — plain-language explanation of what the Pack is, why it exists, and how to install and use it. No prior terminal experience assumed.

## Install

You don't run an install script. You let Claude walk you through it.

```bash
git clone <this-repo> ~/Downloads/claude-starter-pack
cd ~/Downloads/claude-starter-pack
claude
```

Claude reads `INSTRUCTIONS.md` in the current directory, runs a pre-flight check, and asks for your approval at every major step (backup of existing `~/.claude/`, kernel install, workspace placement, personalization).

If you already have a `~/.claude/` setup, the install respects it — backup is automatic, nothing is overwritten without your confirmation.

## What this is not

- **Not a turnkey product.** You will edit files, add your own rules, and shape this to your work. The defaults are starting points, not destinations.
- **Not enterprise-grade.** The safety model protects against accidents and AI mistakes; it does not protect against a determined adversary on your machine. For locked-down environments, use endpoint-managed settings (`/Library/Application Support/ClaudeCode/managed-settings.json`).
- **Not a magic context for every AI tool.** AGENTS.md gives portable intent across tools, but each tool's deeper config (settings, permissions, hooks) is vendor-specific. Don't expect symmetry.

## License

MIT. Fork it, adapt it, redistribute it.
