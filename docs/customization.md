# Customization

How to extend, modify, or replace pieces of the starter pack to fit your work.

## What you'll customize first

1. **`~/Documents/_CONTEXT/user-profile.md`** — fill in who you are. Claude reads this every session. Single biggest leverage on output quality.
2. **`~/.claude/.env`** — add `ANTHROPIC_API_KEY` to enable auto-research and inbox-processing. Add other API keys (OpenAI, Gemini, GitHub, etc.) as needed.
3. **`~/Documents/_CLIENTS/_example-client/`** — rename to a real client when you onboard one, or delete if you don't have clients yet.

## What you'll customize over time

### Adding rules

Drop a new `.md` file into `~/.claude/rules/`. It auto-loads on every session.

Convention:
- Wrap content in a single XML tag (`<my_rule>...</my_rule>`)
- Lead with the rule's purpose; explain *why* (not just what)
- Keep under ~3 KB unless the topic genuinely needs more
- Test by starting a new session and asking Claude about it

Common rules people add:
- `tech-stack.md` — locked technology choices for your standard projects
- `code-style.md` — formatting, naming, comment conventions
- `client-communication.md` — how to write client-facing emails, proposals
- `output-language.md` — language preferences (e.g. "Czech for client docs, English for code comments")
- `decision-philosophy.md` — your principles for evaluating tools and approaches

### Adding skills

Use the bundled `skill-creator` skill: in any project, run `claude` and ask it to "use skill-creator to make a new skill for X". The skill walks you through anatomy, naming, and packaging.

Skills go in `~/.claude/skills/{skill-name}/SKILL.md`. They're auto-discovered.

### Adding hooks

Hooks are configured in `~/.claude/settings.json` under `hooks.{event}` arrays. Events:
- `PreToolUse` — before any tool call (matcher: tool name)
- `PostToolUse` — after any tool call (matcher: tool name)
- `UserPromptSubmit` — when user sends a message
- `SessionStart`, `SessionEnd`, `Stop` — session lifecycle

Hook scripts go in `~/.claude/hooks/`. Make them executable (`chmod +x`).

A hook receives JSON via stdin (`tool_input.command`, `tool_input.file_path`, etc.). Exit code 0 = continue, exit code 2 = block (PreToolUse only) with stderr message shown to Claude.

### Adding scripts

User-invokable utilities go in `~/.claude/scripts/`. Add an allow rule in `settings.json` under `permissions.allow`:
```json
"Bash(~/.claude/scripts/my-tool.sh*)"
```

Without the allow rule, Claude will be prompted every time it runs the script.

### Modifying safety boundaries

The deny list in `settings.json` is the safety net. To loosen it:
- Move a rule from `deny` to `ask` if you want a prompt instead of a hard block
- Move from `ask` to `allow` if you trust it always
- **Never delete a deny rule lightly.** They exist because something you don't want to happen could otherwise happen.

To tighten it:
- Add new patterns to `deny` for behaviors you've seen go wrong
- Edit `bash-safety-extended.py` to add patterns that escape simple deny rules

The starter pack uses `Edit/Write(~/.claude/settings*)` in deny so Claude can't silently change its own config. To edit, open the file directly in an editor. After editing, restart your Claude session for changes to take effect.

## Scaling: solo → team → enterprise

### Solo (default)
The starter pack as-shipped. Single user, single machine. `~/.claude/` is your kingdom.

### Small team
Each team member installs the starter pack independently. Drift is OK — diverging configs reflect personal preferences. Share new rules / skills via:
- Personal git repos (each member pulls into their `~/.claude/`)
- A team-shared starter pack fork with team conventions baked in

### Larger team / managed environment
Use endpoint-managed settings (`/Library/Application Support/ClaudeCode/managed-settings.json` on macOS) to enforce uncircumventable policy across all team members. Combine with `allowManagedPermissionRulesOnly: true` to lock out user-defined permission rules.

The starter pack is fine to use alongside managed settings — managed settings supersede on conflict.

### Enterprise
Server-managed settings (Teams/Enterprise Claude.ai plan) push policy from the admin console. The starter pack becomes a personal layer on top of organization-mandated baselines.

## Removing what you don't want

Modular, not monolithic. To remove pieces:

| Remove this | Effect |
|-------------|--------|
| `~/.claude/skills/dr-prompt/` | `/dr-prompt` slash command unavailable |
| `~/.claude/skills/prd-creator/` | `/prd-creator` unavailable |
| `~/.claude/hooks/notes-research.sh` (and remove from settings.json) | `→ research` markers in notes.md become inert text |
| `~/.claude/hooks/inbox-processor.sh` (and remove from settings.json) | Files in `docs/inbox/` no longer auto-process |
| `~/Documents/_CLIENTS/_example-client/` | Example template gone (you'll create real clients yourself) |
| `~/Documents/_APPS/_example-app-transcribe/` | Stub app gone |

Don't remove:
- `~/.claude/rules/respect-denies.md` — this is what stops Claude from bypassing your safety boundaries
- `~/.claude/hooks/bash-safety-extended.py` — the only catch for two-step bypass patterns
- `~/.claude/settings.json` deny rules — your safety net

## Updating the starter pack itself

The starter pack does not auto-update. There's no version bump mechanism for installed instances. Track upstream changes by:
1. Watching the repo on GitHub
2. Reading release notes when they appear
3. Manually merging changes into your `~/.claude/` if anything looks valuable

This is intentional. Auto-update on settings.json risks blowing away customizations you've made.

If you want centrally-managed configs that update automatically across machines, you've outgrown a starter pack — you need endpoint-managed or server-managed settings (see "Scaling" above).
