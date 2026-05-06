# Architecture

How the starter pack is laid out and why each piece exists.

## Two halves: kernel and workspace

```
~/.claude/             ← kernel: settings, rules, skills, scripts, hooks
~/Documents/           ← workspace: per-context directories you actually work in
```

**Kernel** is the configuration that travels with Claude across all projects. It defines safety boundaries, default behaviors, available skills, and reusable scripts. Lives in `~/.claude/`.

**Workspace** is where your work happens. Per-client, per-business-area, per-app directories. Each top-level directory is opinionated about what belongs there.

The two halves are loosely coupled — you can install just the kernel if you don't want the workspace structure, and vice versa.

## Kernel layout

```
~/.claude/
├── settings.json              ← permissions (allow/deny/ask), hooks, env vars
├── AGENTS.md                  ← global behavioral baseline
├── CLAUDE.md → AGENTS.md      ← symlink so Claude Code reads same content
├── rules/                     ← auto-loaded into every session
├── scripts/                   ← user-invokable utilities
├── hooks/                     ← harness-invoked, runs on events
├── agents/                    ← custom subagent definitions (empty by default)
├── skills/                    ← bundled skills (setup, skill-creator, prd-creator, dr-prompt)
└── templates/                 ← scaffolding templates for the /setup skill
```

## Workspace layout

```
~/Documents/
├── _CONTEXT/                  ← user profile, notes, best-practices
├── _CLIENTS/                  ← per-client engagement folders
├── _BUSINESS/                 ← your own business work
└── _APPS/                     ← tools and apps you build
```

Each top-level workspace directory has its own AGENTS.md (with CLAUDE.md symlink) explaining what belongs there, except `_CLIENTS/` itself (you should never run Claude from `_CLIENTS/`, only from a specific client subfolder).

## File convention: AGENTS.md + CLAUDE.md symlink

Every project root has both files. They point to the same content via symlink:

```
project/
├── AGENTS.md       ← canonical content
└── CLAUDE.md       ← symlink → AGENTS.md
```

**Why both?**
- `AGENTS.md` is a cross-tool convention adopted by Cursor, Codex, Gemini CLI, Aider, and ~20 other tools (Linux Foundation Agentic AI Foundation, ratified Dec 2025).
- `CLAUDE.md` is what Claude Code reads natively (as of mid-2026, AGENTS.md support is requested but not native — see issue #6235).
- Symlink means one source of truth, two file paths. Edit either, and both reflect.
- When Claude Code adds native AGENTS.md support, no migration needed — both already work.

## Hook flow (data path)

When you edit a file, multiple things happen:

```
Claude uses Edit tool
        ↓
PreToolUse hooks fire   ← bash-safety-extended.py (Bash only) blocks dangerous patterns
        ↓
Permission engine       ← allow/deny/ask matched against settings.json
        ↓
Edit executes
        ↓
PostToolUse hooks fire  ← notes-research.sh, inbox-processor.sh
   (async, non-blocking)
```

Hooks invoked by harness do NOT go through the permission engine. They're trusted code shipped with the kernel.

## Auto-processing workflows

### Notes → research

Edit `notes.md` with an entry containing `→ research`:
```
## 2026-05-01 14:00
Investigate how competitor X structures their B2B onboarding. → research
```

The `notes-research.sh` hook detects the marker, dispatches an Anthropic API call in the background, writes the result to `research/{topic-slug}-research-{YYYY-MM-DD}.md`, and appends a reference to `notes.md`.

Cost: tokens per trigger. Disabled if `ANTHROPIC_API_KEY` not in `~/.claude/.env`.

### Inbox → knowledge base

Drop a `.md` or `.txt` file into any `docs/inbox/` (e.g. inside a client directory):
- Auto-extraction via Anthropic API → `docs/knowledge-base/drafts/{filename}-extract-{date}.md`
- Original moved to `docs/inbox/done/`
- Action logged to `log.md`

User reviews drafts and promotes to `docs/knowledge-base/` if useful. Hook never writes to `knowledge-base/` directly — drafts only.

Cost: tokens per file (truncated to 50k chars input). Disabled without API key.

## What flows where

| Layer | Reads from | Writes to |
|-------|------------|-----------|
| Claude Code session | `~/.claude/CLAUDE.md`, `~/.claude/rules/*`, project `AGENTS.md/CLAUDE.md` | Files via Edit/Write tools (with permissions) |
| `notes-research.sh` hook | `~/.claude/.env`, project `notes.md` | `research/` dir, appends to `notes.md` |
| `inbox-processor.sh` hook | `~/.claude/.env`, files in `docs/inbox/` | `docs/knowledge-base/drafts/`, `docs/inbox/done/`, `log.md` |
| `bash-safety-extended.py` hook | hook stdin (tool input) | stderr (block reasons), exit code 0/2 |
| `list-env-keys.sh` script | process env, `~/.claude/.env`, `./.env` | stdout (var names only) |

## Trust boundary

The kernel ships with safety enforced via:
1. **`settings.json` denies** — destructive bash, sensitive file reads
2. **`bash-safety-extended.py` hook** — patterns that simple deny rules miss
3. **`disableBypassPermissionsMode: "disable"`** — bypass mode locked off
4. **`respect-denies.md` rule** — Claude is instructed to never bypass denies, only inform user

These protect against accidents and Claude being misled into destructive actions. They do **not** protect against a determined adversary on your machine. For locked-down environments, see `safety-model.md`.
