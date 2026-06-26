---
type: notes
title: "Instructions for Claude - Starter Pack Installation"
status: approved
summary: "You are reading this because the user just cloned the Claude Code Starter Pack and ran `claude` in the repo root."
created: 2026-06-16 00:51
updated: 2026-06-16 16:59
owner: Šimon Hradní
client: ~
path: INSTRUCTIONS.md
tags: [note]
version: "1.0.0"
release: latest
---

# Instructions for Claude - Starter Pack Installation

You are reading this because the user just cloned the Claude Code Starter Pack and ran `claude` in the repo root. Your job is to walk them through installation safely, with explicit confirmation at each major step.

**Do not silently run install commands.** Show what you're about to do, get user approval, then execute. The user is reviewing each step. If they say "skip this", skip it and note what was skipped.

**Style for this install session:** terse. The user can read; don't narrate. Show the command before running it. After running, report the result in one line.

## Step 0 - Greet and confirm intent

Acknowledge what's about to happen. Ask: "Ready to install the Claude Code Starter Pack? This will modify `~/.claude/` and create directories in your home folder. I'll confirm each step before doing anything."

Wait for explicit yes.

## Step 0.5 - Ask the user to switch to plan mode, then write the plan

Before touching anything on the user's system, **write a plan** and get the user's approval. The cleanest way is plan mode, which forces presentation before execution.

**Ask the user to switch:**

> "For the safest install, press **Shift+Tab** in your terminal to switch into plan mode. In that mode I can only present a plan - I can't run anything until you approve it. Once you've pressed Shift+Tab, tell me and I'll write the plan."

Wait for confirmation that they've switched. (You won't always be able to detect plan mode reliably from your side - rely on the user's confirmation.)

**Then run Step 1 (pre-flight check, read-only) and write the plan.** A good install plan summarizes:
- OS and dependency check results (from Step 1 - those checks are read-only, fine to run before the plan exists)
- Whether a backup of existing `~/.claude/` will happen, and where it will go
- The workspace location and directory names that will be used
- Which files will be copied, where, and what will be left alone
- Which credential / personalization questions remain to be answered
- The exact list of commands you'll run, in order

In plan mode, present the plan via `ExitPlanMode`. The user approves there, plan mode exits, you execute. **Do not improvise outside the plan.** If something unexpected comes up mid-install, stop, update the plan, re-confirm.

**If the user declines plan mode** (says they don't want to switch, can't find Shift+Tab, or just says "go ahead without"):

1. Create `./INSTALL-PLAN.md` in the current working directory (the cloned Pack folder).
2. Write the same plan into that file.
3. Show it to the user in the terminal output (print contents or summarize and point to the file).
4. Wait for explicit approval: "approve", "go", "OK to proceed", or similar.
5. Only after explicit approval, start executing.
6. After the install finishes (Step 11), delete `./INSTALL-PLAN.md` - it was a working artifact, not a deliverable.

Either way: **no change action and no copy operation happens before the user has approved a written plan.** Step 1 (read-only checks) is the only thing that may run before the plan exists.

## Step 1 - Pre-flight check

Run these checks and report results in a single message:

1. **OS detection** - `uname -s`:
   - **Darwin** → macOS, all instructions apply as written
   - **Linux** → adjust paths if user uses non-standard `~/Documents/` location; otherwise same as macOS
   - **MINGW / MSYS / CYGWIN** or PowerShell → **Windows.** Stop and tell the user:
     > "This starter pack assumes a Unix-like shell. On Windows, the cleanest path is **WSL2** (Windows Subsystem for Linux) - install Ubuntu via Microsoft Store, run Claude Code inside WSL, and use this pack as on Linux. Native Windows is possible but requires manual path adjustments throughout (`%USERPROFILE%` vs `$HOME`, backslash vs forward slash, no symlinks without admin) - not recommended for first install. Do you want to continue with WSL setup or quit and install WSL first?"
2. **Required binaries** - verify `python3`, `node`, `git`, `jq`, `curl` are installed and on PATH. Report versions.

   If any are missing, **stop** and give the user OS-specific install commands. Do NOT install dependencies yourself - that's a system change requiring the user's explicit choice of how to manage their package manager.

   - **macOS via Homebrew (recommended):**
     ```bash
     # If brew itself is missing first:
     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
     # Then:
     brew install python3 node git jq curl
     ```
   - **Linux (Debian/Ubuntu):**
     ```bash
     sudo apt update && sudo apt install -y python3 nodejs git jq curl
     ```
   - **Linux (Fedora/RHEL):**
     ```bash
     sudo dnf install -y python3 nodejs git jq curl
     ```

   After the user installs missing tools, run the check again. Do not proceed until all five pass.

3. **Existing `~/.claude/`** - `ls -la ~/.claude/ 2>/dev/null | wc -l`. Report whether it exists and how many entries.
4. **Existing workspace dirs** - by default, the pack uses `~/Documents/_CONTEXT`, `~/Documents/_CLIENTS`, `~/Documents/_BUSINESS`, `~/Documents/_APPS`. Check if any exist. (Workspace location is user-customizable in Step 4.)
5. **Read all content in `docs` from this repo.**
6. **Ask the user where the directories (_CONTEXT, _CLIENTS, _BUSINESS, _APPS) should be placed, and whether they should be renamed.** Also clarify any other details that need to be addressed before the plan is presented and accepted.

## Step 2 - Backup existing `~/.claude/`

If `~/.claude/` exists, propose:

```bash
cp -r ~/.claude ~/.claude.bak-$(date +%Y%m%d-%H%M%S)
```

Get user approval. After backup, report the backup path. If `~/.claude/` does not exist, skip this step and tell the user.

## Step 3 - Install kernel

Show the user what will be copied:

```
kernel/ → ~/.claude/
```

Files going in:
- `settings.json` (restrictive baseline; bypass mode locked off)
- `AGENTS.md` + `CLAUDE.md` (symlink)
- `statusline.sh` - three-line live status (model · cost / project · ctx / 5h · 7d rate limits)
- `rules/` (six rules: documentation, frontmatter-standard, respect-denies, subagents, notes, language)
- `scripts/list-env-keys.sh`
- `hooks/`:
  - `bash-safety-extended.py` (PreToolUse Bash) - blocks bypass patterns
  - `context-bloat-guard.py` (PreToolUse Read) - soft brake on huge file reads
  - `notes-research.sh` (PostToolUse Edit/Write) - auto-research on `notes.md` markers
  - `inbox-processor.sh` (PostToolUse Edit/Write) - extracts inbox documents to KB drafts
  - `inject-current-time.sh` (UserPromptSubmit) - current time in every prompt
- `skills/setup/`, `skills/skill-creator/`, `skills/prd-creator/`, `skills/dr-prompt/`, `skills/client-data-check/`, `skills/idea-file-creator/`, `skills/checkpoint/`, `skills/end/`
- `templates/` (five scaffolding templates: klient, dev, business, app, general)
- `agents/` - `prompt-engineer`, `research-analyst` + README

**Critical - existing setup: analyze, recommend, don't overwrite.** If `~/.claude/settings.json` (or a `rules/`/`hooks/` directory) already exists, do NOT blindly replace it. First read the user's existing config - permissions, hooks, env, rules - and compare it against what this pack ships. Then present a tailored, area-by-area recommendation: what of theirs is worth keeping, what the pack adds that's worth adopting, where the two overlap or conflict, and a suggested result tuned to how this user actually works (ask briefly if it's not obvious). The user decides per area; then write the agreed result. Replace wholesale only if there is nothing meaningful there or they ask for it. The backup protects the original either way - the install never auto-merges JSON, so the merged result is written explicitly.

Execute the copy. Make scripts and hooks executable:
```bash
chmod +x ~/.claude/scripts/*.sh ~/.claude/hooks/*.{sh,py}
```

After copy: re-create the `~/.claude/CLAUDE.md` symlink (it may not have copied as a symlink):
```bash
cd ~/.claude && ln -sfn AGENTS.md CLAUDE.md
```

## Step 4 - Customization wizard (interactive)

Don't just dump files into `~/Documents/` and walk away. Present the layout below as a **proposal, not a fixed structure**: tell the user "this is the structure the pack suggests - let's go through it and shape it to how you actually want to work." Then run a short interview - three blocks, ~7 questions total. Take answers, confirm in a recap, then execute.

### Block A - Workspace location and naming

```
The starter pack's workspace structure consists of four top-level directories:
  _CONTEXT/    - your personal profile, notes, best-practices
  _CLIENTS/    - per-client engagement folders
  _BUSINESS/   - your own business work (projects, education, internal docs)
  _APPS/       - small tools and apps you build

Question 1: where should these directories live?
  1. ~/Documents/ (default - visible in Finder/Explorer, easy access)
  2. ~/ (directly in home)
  3. ~/Documents/Work/ or another sub-folder - name it
  4. Outside home, e.g. /Volumes/Work/ (external drive) or ~/Code/

  Paths with spaces work but are discouraged - Bash doesn't like them.

Question 2: do you want to rename any of the directories?
  Defaults shown above. You can use any names that fit your work.
  Some users prefer English plain names (clients/, business/, apps/).
  Some prefer keeping the underscore prefix (_CLIENTS/) for visual sorting.
  Some prefer native-language names in their own language.
  Type space-separated overrides or press Enter to keep defaults.
  Format: <context-dir> <clients-dir> <business-dir> <apps-dir>
  Example: context clients business apps
```

Apply user's answers. Store the chosen base path. **Use it for the rest of the install.** Never fall back to `~/Documents/` after they chose something else.

### Block A2 - Conflict check

For each chosen directory, check if it already exists at the chosen base path:

```bash
for dir in <name1> <name2> <name3> <name4>; do
  if [ -e "<base-path>/$dir" ]; then echo "EXISTS: $dir"; else echo "free: $dir"; fi
done
```

If any exist: **never overwrite.** Tell the user, and offer:
1. Skip that one (don't copy from the Pack, keep the user's existing content)
2. Rename the Pack's version (e.g. add `-new` suffix) so the user can merge manually
3. Abort and let the user move/rename their existing directory first

### Block B - Personal profile (one round of questions)

```
The user-profile file (in {context-dir}/user-profile.md) is read by Claude
across all sessions. The more accurate it is, the more tailored the work.

Quick interview - answer in 1–2 sentences each, or "skip" to leave blank:

Question 3: Your role and primary work focus?
  (e.g. "Solo consultant doing AI strategy for SMEs" or "Backend dev at a fintech")

Question 4: What tech stack and AI tools do you use most?
  (e.g. "Python + Postgres, Claude Code daily, sometimes Cursor")

Question 5: Communication style preference?
  Pick one: terse / balanced / detailed.
  Direct push-back when you have a flawed plan? yes / no.

Question 6: Output language for your own work?
  (e.g. "Czech for personal/client docs, English for code and system files")
```

Write the answers into `{context-dir}/user-profile.md`, replacing the empty placeholders in the template.

### Block C - Example content

```
Question 7: The pack ships with example directories you can keep, rename, or delete:
  - _CLIENTS/_example-client/  (sample client structure)
  - _APPS/_example-app-transcribe/  (stub app demonstrating _APPS layout)

  Options:
  (a) Rename _example-client to a real client name (give me the name)
  (b) Delete both examples (you'll create your own)
  (c) Keep both as references (default)
```

Apply the choice.

### Workspace copy

Now copy the workspace directories using the user's chosen paths and names:

```bash
mkdir -p {base-path}
# For each chosen directory name, cp from workspace/{default-name}/ to {base-path}/{chosen-name}/
```

**Never overwrite an existing top-level directory** - if `_CONTEXT` (or whatever the user named it) already exists, skip it and tell the user (they'll merge manually if they want).

After copy, re-create the symlinks for `AGENTS.md` ↔ `CLAUDE.md` in each project subfolder. Symlinks may not survive a `cp` cleanly:
```bash
# In each subdirectory that should have AGENTS.md + CLAUDE.md symlink:
cd {dir} && ln -sfn AGENTS.md CLAUDE.md
```

## Step 5 - Set up the credential store (`~/.claude/.env`)

The starter pack uses `~/.claude/.env` as the central place for API keys. The notes-research and inbox-processor hooks read `ANTHROPIC_API_KEY` from this file.

If `~/.claude/.env` doesn't exist, create it with a starter template:

```bash
cat > ~/.claude/.env <<'EOF'
# Claude Code credential store. Loaded by hooks. NEVER commit this file.
# Format: KEY=value (no quotes needed for simple strings)

# Required for notes-research and inbox-processor hooks (cost: tokens per trigger)
ANTHROPIC_API_KEY=

# Optional - override the default research model (defaults to Haiku for cost)
# ANTHROPIC_MODEL=claude-haiku-4-5-20251001

# Add other API keys as you need them. Examples:
# OPENAI_API_KEY=
# GEMINI_API_KEY=
# GITHUB_TOKEN=
EOF
chmod 600 ~/.claude/.env
```

Ask the user to add their `ANTHROPIC_API_KEY` value (or skip - auto-research workflow will be inert until they add it). Without the key, the hooks silently no-op - that's a feature, not a bug.

Show how the env-keys helper works:
```bash
~/.claude/scripts/list-env-keys.sh
```

Their `ANTHROPIC_API_KEY` (and any other credentials they added) should appear by name. Values never appear.

### The one readable env file - `.env.shared`

`~/.claude/.env` above is the GLOBAL credential store for hooks; Claude never reads its values. The model has three tiers: the global `~/.claude/.env` and every project `.env` / `.env.local` / `.env.production` / `.env.*` are HARD - Claude never reads their values (`.env.local` is HARD on purpose; the JS ecosystem treats it as the live-secret file, so live keys land there). The single readable env file is **`.env.shared`** - the soft tier for low-risk values safe to surface (a notify webhook, a contact email). The deny rules plus the `bash-safety-extended.py` hook block reading every HARD `.env` / `.env.*` (via `cat`, `source`, redirection, `python -c`, docker bind-mount, or the Read tool). A real secret is never read by Claude - a program uses it without revealing the value. To see only the key NAMES of any HARD env file, Claude runs `~/.claude/scripts/list-env-keys.sh --from <path>` (add `--classify` for each key's state). Scope note: only commands that read the *values* into view are blocked (`cat`, `source`, redirection, `python -c ...read()`); passing the file as config (`--env-file`), copying a template, or mentioning it in text all pass, so deploys and setup are not blocked.

## Step 5.5 - Pre-trust the workspace (optional, stops the folder-trust nag)

On first launch in any directory, Claude Code shows **"Do you trust the files in this folder?"** and the user must accept. This is a deliberate safety gate; there is no `settings.json` key or safe env var to disable it (bypass mode would skip it, but it is locked off here on purpose). The supported way to stop the repeated prompt for directories the user already trusts is to pre-write the per-directory trust flag into `~/.claude.json`. The kernel ships `~/.claude/scripts/trust-workspace.sh` for exactly this.

Offer to pre-trust the workspace base path from Step 4 and each directory created in the workspace copy:

```bash
~/.claude/scripts/trust-workspace.sh <base-path>/<chosen-dir-1> <base-path>/<chosen-dir-2>
```

- It backs up `~/.claude.json`, merges (never overwrites), and validates JSON before saving.
- It weakens nothing else: normal permission prompting and `disableBypassPermissionsMode` stay fully in force. It only persists "yes, I trust this folder" up front, exactly as clicking Yes would.
- Brand-new directories opened later still prompt once - correct for a safety baseline. Re-run the script for those, or just accept once.
- The install session is itself a Claude Code session, so if the prompt persists after the Step 6 restart, have the user run the command once more from a plain terminal (a running session can overwrite `~/.claude.json` on exit).

## Step 6 - Verification

Tell the user to **restart their Claude Code session** so the new `settings.json` takes effect. After restart, they can verify:

- `~/.claude/scripts/list-env-keys.sh` returns env var names without values
- A denied command (e.g. asking Claude to `cat .env`) gets blocked, but a deliberate `.env.shared` is readable (the single readable soft tier)
- Bypass mode is off - `claude --permission-mode bypassPermissions` should refuse
- The current-time injection works - at session start, Claude should know the actual time (test by asking "what time is it?")

## Step 7 - Lock settings.json (final step before hand-off)

During this install session, the starter pack's `settings.json` allowed Claude to freely edit `~/.claude/settings.json` (no specific deny or ask rule on it; the broad `Edit(*)` / `Write(*)` allows applied). This was deliberate - install may need to fine-tune things.

**At the end of installation, lock it down.** Add Edit/Write on `~/.claude/settings*` to the `ask` list, so future sessions prompt the user before any change to the kernel config:

```bash
python3 -c "
import json
from pathlib import Path
p = Path.home() / '.claude' / 'settings.json'
s = json.load(open(p))
ask = s.setdefault('permissions', {}).setdefault('ask', [])
for rule in ['Edit(~/.claude/settings*)', 'Write(~/.claude/settings*)']:
    if rule not in ask:
        ask.append(rule)
json.dump(s, open(p, 'w'), indent=2)
print('settings.json locked: future edits to ~/.claude/settings* require user approval')
"
```

After this step, Claude can still modify settings.json - but each modification requires the user to confirm at the prompt. This prevents silent drift while preserving flexibility.

## Step 8 - Hand off

Tell the user:

> Setup is done. Read `docs/customization.md` when you want to extend the system. Read `docs/safety-model.md` to understand what the safety boundaries are and aren't. Read `docs/prompting-claude.md` for tips on getting better Claude output. The starter pack repo can be deleted now - everything is installed in `~/.claude/` and your chosen workspace directories.

Then recommend a better terminal:

> Optional but recommended: install **[Warp](https://www.warp.dev/)** as your terminal - a clearer, friendlier command line than the default. Useful upsides: a file explorer right beside the terminal, normal rich text input (type like in any editor, without the usual terminal quirks), tidier window organization, and easier folder navigation. Claude Code runs in it unchanged. In the free version, turn Warp's own AI **off** during initial setup - if you use Claude Code, you don't need Warp's AI.

This recommendation is written Mac-first (Warp's original ecosystem). Warp also ships a Windows build, so if the user is on Windows, point them at the Windows download and adapt the setup - do not present it as Mac-only.

End the install session here. Do not proceed to other tasks unless the user asks.

## Error handling - global rules

- If any step fails, stop. Do not continue to the next step.
- If a permission denial occurs during install (e.g. they run from a directory that doesn't allow writes), surface it clearly and propose a fix.
- Never run `rm -rf` during install. Use `mv` to a backup path instead.
- Never use `sudo`. If something requires sudo, instruct the user to run it manually.

## Windows-specific addendum

If the user is on Windows and chose to continue without WSL (against the recommendation):

- Replace `~/.claude/` with `%USERPROFILE%\.claude\` (or `$env:USERPROFILE\.claude\` in PowerShell)
- Replace `~/Documents/` similarly
- Symlinks won't work without admin rights - instead of `ln -s AGENTS.md CLAUDE.md`, create a hard link or just copy the file (acknowledge that this means two files to keep in sync)
- `chmod +x` is a no-op on Windows; PowerShell scripts must be unblocked via `Unblock-File` instead
- Bash hooks (`*.sh`) won't run natively - they require Git Bash, WSL, or rewrite to `.ps1`
- `~/.claude/.env` works the same way; PowerShell env loading differs (`$env:KEY = (Get-Content .env | ...)`)

Strongly recommend WSL2. The starter pack assumes Unix conventions throughout - fighting Windows native is more work than installing WSL.
