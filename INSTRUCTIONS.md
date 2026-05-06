# Instructions for Claude — Starter Pack Installation

You are reading this because the user just cloned the Claude Code Starter Pack and ran `claude` in the repo root. Your job is to walk them through installation safely, with explicit confirmation at each major step.

**Do not silently run install commands.** Show what you're about to do, get user approval, then execute. The user is reviewing each step.

## Step 0 — Greet and confirm intent

Acknowledge what's about to happen. Ask: "Are you ready to install the Claude Code Starter Pack? This will modify `~/.claude/` and create directories in `~/Documents/`. I'll confirm each step before doing anything."

Wait for explicit yes.

## Step 1 — Pre-flight check

Run these checks and report results in a single message:

1. **OS detection** — `uname -s` (expect Darwin or Linux; Windows users should run via WSL).
2. **Required binaries** — verify `python3`, `node`, `git` are installed and on PATH. Report versions.
3. **Existing `~/.claude/`** — `ls -la ~/.claude/ 2>/dev/null | wc -l`. Report whether it exists and how many entries.
4. **Existing workspace dirs** — check if `~/Documents/_CONTEXT`, `~/Documents/_CLIENTS`, `~/Documents/_BUSINESS`, `~/Documents/_APPS` exist.

If any required binary is missing, stop and tell the user how to install it. Do not proceed.

## Step 2 — Backup existing `~/.claude/`

If `~/.claude/` exists, propose:

```bash
cp -r ~/.claude ~/.claude.bak-$(date +%Y%m%d-%H%M%S)
```

Get user approval. After backup, report the backup path.

If `~/.claude/` does not exist, skip this step and tell the user.

## Step 3 — Install kernel

Show the user what will be copied:

```
kernel/ → ~/.claude/
```

Files going in:
- `settings.json` (restrictive baseline)
- `AGENTS.md` + `CLAUDE.md` (symlink)
- `rules/` (four rules)
- `scripts/list-env-keys.sh`
- `hooks/bash-safety-extended.py` + `hooks/notes-research.sh` + `hooks/inbox-processor.sh`
- `skills/setup/`, `skills/skill-creator/`, `skills/prd-creator/`, `skills/dr-prompt/`
- `templates/` (four scaffolding templates)
- `agents/` (empty placeholder + README)

Critical: if `~/.claude/settings.json` already exists in the backup, ask the user whether to replace it or merge. The default is **replace** (the backup preserves their old version). If they want to merge, tell them they'll need to do it manually via editor — the install does not auto-merge JSON.

Execute the copy. Make scripts and hooks executable:
```bash
chmod +x ~/.claude/scripts/*.sh ~/.claude/hooks/*.{sh,py}
```

After copy: re-create the `~/.claude/CLAUDE.md` symlink (it may not have copied as a symlink):
```bash
cd ~/.claude && ln -sfn AGENTS.md CLAUDE.md
```

## Step 4 — Install workspace

Ask the user where to place the workspace. Default: `~/Documents/`.

Copy the four top-level directories: `_CONTEXT/`, `_CLIENTS/`, `_BUSINESS/`, `_APPS/`. **Never overwrite an existing top-level directory** — if `_CONTEXT` already exists, skip it and tell the user (they'll merge manually if they want).

Re-create the symlinks for `AGENTS.md` ↔ `CLAUDE.md` in each project subfolder that has them. Symlinks may not survive a `cp` cleanly; re-establish with `ln -sfn AGENTS.md CLAUDE.md` in each project root.

## Step 5 — Set up the credential store (`~/.claude/.env`)

The starter pack uses `~/.claude/.env` as a central place for API keys and other credentials. The notes-research and inbox-processor hooks read `ANTHROPIC_API_KEY` from this file.

Check if `~/.claude/.env` already exists. If not, create it with a starter template:

```bash
cat > ~/.claude/.env <<'EOF'
# Claude Code credential store. Loaded by hooks. NEVER commit this file.
# Format: KEY=value (no quotes needed for simple strings)

# Required for notes-research and inbox-processor hooks (cost: tokens per trigger)
ANTHROPIC_API_KEY=

# Optional — override the default research model
# ANTHROPIC_MODEL=claude-haiku-4-5-20251001

# Add other API keys as you need them. Examples:
# OPENAI_API_KEY=
# GEMINI_API_KEY=
# GITHUB_TOKEN=
EOF
chmod 600 ~/.claude/.env
```

Tell the user:
- The file is at `~/.claude/.env`
- It's denied from being read by any tool except hooks (which run outside the permission engine)
- Without `ANTHROPIC_API_KEY`, the notes-research and inbox-processor hooks silently no-op — that's a feature, not a bug
- Use `~/.claude/scripts/list-env-keys.sh` to verify Claude can see the variable *names* (never values)

Wait for the user to say they've added their API key (or skipped). If they skip, mention that the auto-research workflow will be inert until the key is added.

## Step 6 — Personalize

1. Open `~/Documents/_CONTEXT/user-profile.md` and ask the user to fill in:
   - Their name, role, primary work focus
   - Their tech stack and main tools
   - Communication style preferences (terse vs. detailed, formal vs. casual)

2. Ask if they want to rename `_CLIENTS/_example-client/` to a real client name. If yes, do the rename and update any internal references.

3. Show them how the env-keys helper works:
   ```bash
   ~/.claude/scripts/list-env-keys.sh
   ```
   Their `ANTHROPIC_API_KEY` (and any other credentials they added) should appear by name. Values never appear.

## Step 7 — Verification

Tell the user to **restart their Claude Code session** so the new `settings.json` takes effect. After restart, they can verify:

- `python3 ~/.claude/scripts/list-env-keys.sh` returns env var names without values
- A denied command (e.g. asking Claude to `cat .env`) gets blocked
- Bypass mode is off (`claude --permission-mode bypassPermissions` should refuse)

## Step 8 — Hand off

Tell the user:

> Setup is done. Read `~/Downloads/claude-starter-pack/docs/customization.md` when you want to extend the system. Read `docs/safety-model.md` to understand what the safety boundaries are and aren't. The repo can be deleted now — everything is installed in `~/.claude/` and `~/Documents/`.

End the install session here. Do not proceed to other tasks unless the user asks.

## Error handling — global rules

- If any step fails, stop. Do not continue to the next step.
- If a permission denial occurs during install (e.g. they run from a directory that doesn't allow writes), surface it clearly and propose a fix.
- Never run `rm -rf` during install. Use `mv` to a backup path instead.
- Never use `sudo`. If something requires sudo, instruct the user to run it manually.

## Style for this install session

- Terse. The user can read; don't narrate.
- Show the command before running it. After running, report the result in one line.
- If the user says "skip this", skip it and note what was skipped.
