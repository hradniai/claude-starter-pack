# Customization

Where each part of the pack lives, when Claude Code loads it, and how to change, remove, move or update it. What each part is for is in the [README](../README.md#what-you-get); what the safety layer covers is in [safety.md](safety.md).

## Where everything lives

```
~/.claude/                (on Windows C:\Users\<you>\.claude)
├── settings.json         permission rules, hooks, status line, environment
├── CLAUDE.md             global instructions; imports your profile
├── workspace-root        only when your workspace is not ~/Documents
├── rules/                instructions Claude Code loads by itself
├── skills/               one folder per skill
├── agents/               one file per helper agent
├── scripts/              the hooks, the Python launcher, the status line and helpers
├── workflows/            the research-engine workflow
├── templates/            what /setup builds new projects from
└── .env                  API keys for your own scripts (Claude never reads the values)

~/Documents/              (or the folder you chose)
├── _CONTEXT/             user-profile.md, best-practices/, llms/ (model lineup, prompting guide)
├── _CLIENTS/             one folder per client; _example-client/ shows the layout
├── _BUSINESS/            your own business work
└── _APPS/                tools you build; _example-app-transcribe/ is a small example
```

Every project folder has its own `CLAUDE.md` with that project's instructions, plus the journals `WORKSTATE.md` (where things stand) and `worklog.md` (what happened). The cloned pack folder keeps the documentation and the tests, which are not installed.

## What loads when

- **Every session:** `~/.claude/CLAUDE.md`, the profile it imports (the line `@~/Documents/_CONTEXT/user-profile.md`), the rules without a `paths` field (all but `frontmatter-standard`), and the `CLAUDE.md` of the folder you start in and of the folders above it.
- **When Claude works with markdown files:** `frontmatter-standard`, whose `paths: ["**/*.md"]` field limits it to them.
- **When used:** a skill or agent costs only its short description until Claude uses it.
- **When a change takes effect.** Claude Code applies most edits to `settings.json` to the running session, permission rules and hooks included, and picks up edited skills at once. `CLAUDE.md`, its imports and the rules load only when a session starts, a few settings such as `model` are read only then, and a folder created during a session (a first `agents/`, say) needs a new session. After a change, start a new session to be sure: `/status` lists the settings files it read, `/hooks` the hooks, `/context` what is loaded ([when edits take effect](https://code.claude.com/docs/en/settings#when-edits-take-effect)).

## First things to fill in

1. **`_CONTEXT/user-profile.md`** in your workspace: who you are, how you work, which language Claude should talk in. It is loaded into every session, so it is the biggest single lever on how well Claude's work fits you.
2. **`~/.claude/.env`**: API keys your own scripts need. Nothing in the pack requires one.
3. **`_CLIENTS/_example-client/`**: rename it for your first real client, or remove it once you no longer need the example.

## Global instructions

`~/.claude/CLAUDE.md` says how Claude works with you: candid collaboration, small verified changes, what it asks before doing, where the safety layer and the workspace are. Edit it like any text file, or ask Claude to; changes apply from the next session. A project's own `CLAUDE.md` adds what matters for that project. Keep both short: they are loaded into every session and take up room in the context window.

## Rules

A rule is a `.md` file in `~/.claude/rules/`. Claude Code loads every rule without a `paths` field into every session, so each one costs context all the time, and so does any other `.md` file there: never put notes or a README into that folder.

- Wrap the content in one XML tag (`<my_rule>...</my_rule>`), lead with its purpose, and say *why* each constraint exists: Claude follows a reasoned constraint more reliably.
- Keep it short. Anything that is a procedure belongs in a skill, which loads only when used.
- A rule that matters only for some files gets a `paths` field in its header (for example `paths: ["**/*.py"]`) and then loads only when Claude reads or writes a matching file.
- A rule for one project belongs in that project's `CLAUDE.md`.
- Test it by starting a new session and asking Claude what the rule says.

For prompt structure in general (XML tags, purpose first, explaining why, differences between models), see `_CONTEXT/llms/model-reference-prompting.md` in your workspace.

## Skills

Ask the `prompt-engineer` agent to write one ("use the prompt-engineer agent to make a skill that ..."): it drafts the skill, checks it on test inputs and tells you what it could not check. Anthropic's skill-creator plugin, which the installer offers, can test a skill more thoroughly or compare two versions. A skill is `~/.claude/skills/<name>/SKILL.md` for all your projects, or `.claude/skills/<name>/SKILL.md` inside one project. Its `description` decides when Claude uses it, so name the situations and phrases that should trigger it ([skills](https://code.claude.com/docs/en/skills)).

## Agents

A helper agent (subagent) is a markdown file in `~/.claude/agents/`; the header sets when and how it runs, the body is its instructions:

```markdown
---
name: my-agent
description: When Claude should use this agent - specific, with trigger phrases.
tools: Read, Grep, Glob        # optional; without it the agent gets every tool of the session
model: sonnet                  # optional
---

What the agent is for, its constraints, and the shape of what it returns.
```

It sees your `CLAUDE.md` files and rules, the session's tools (narrowed by `tools:`) and its permissions, but not your conversation: everything it needs must be in the brief Claude gives it. Add one for a task you repeat with a stable prompt; for one-off work, Claude's built-in general-purpose agent with a good brief is enough. The `prompt-engineer` agent can write one for you ([subagents](https://code.claude.com/docs/en/sub-agents)).

## Hooks and helper scripts

Put every program in `~/.claude/scripts/`. A hook is a script that `settings.json` calls on an event. Start Python scripts through the pack's launcher, so the same line works on macOS, Windows and Linux. The entry goes inside the `hooks` object of `~/.claude/settings.json`: add it to the existing `PreToolUse` list there, because a second `"PreToolUse"` key would silently replace the pack's safety hooks:

```json
{ "matcher": "Bash", "hooks": [{ "type": "command", "command": "sh ~/.claude/scripts/python-launcher.sh guard my-check.py" }] }
```

- The launcher runs only files from its own folder. Use `guard` for a check that must block when no Python is available, `plain` for anything else. A shell script runs as `bash ~/.claude/scripts/my-check.sh`.
- Events include `PreToolUse` and `PostToolUse` (matcher: the tool name), `UserPromptSubmit`, `SessionStart`, `SessionEnd` and `Stop`. A hook receives JSON on its standard input (`tool_input.command`, `tool_input.file_path`, ...).
- For `PreToolUse`, exit code 2 blocks the call and shows the error output to Claude; exit 0 lets it through. **Every other exit code lets the call through too**, so a check that crashes or cannot start lets everything through. That is why the pack's hooks run through the launcher in `guard` mode, which turns a missing Python or a crashed check into a block ([hooks](https://code.claude.com/docs/en/hooks)).
- Claude can write the hook for you. It asks before it touches `~/.claude/scripts/` or `settings.json`, and the safety hook blocks shell commands that write there, so every change to the safety layer passes you.

A helper Claude should run without a prompt each time needs an allow rule, for example `"Bash(~/.claude/scripts/my-tool.sh*)"`, and the executable bit (`chmod +x`).

## Safety settings

- **Loosen** by moving a rule in `~/.claude/settings.json` from `deny` to `ask` (a prompt instead of a block) or from `ask` to `allow`. Delete a deny rule only when you know what it was stopping. The hook re-checks refused commands only in their hidden forms (`bash -c '...'`, `eval`, `/bin/rm`), so loosening the plain form is not silently overridden.
- **Tighten** by adding `deny` patterns for things you have seen go wrong, or a check in `~/.claude/scripts/bash-safety-extended.py` for what a pattern cannot express. [safety.md](safety.md#layer-2-the-hooks) lists what the existing checks recognize.
- **Pushing straight to `main` on purpose:** remove the `git-push-guard.py` entry from `settings.json`. It enforces a habit, not a safety boundary, so nothing else weakens.
- **One project:** its `.claude/settings.json` or `.claude/settings.local.json` adds rules for that project only. Rules from every level combine and deny beats ask beats allow, so a project file can add blocks or allow more, but cannot lift a `deny` or an `ask` from `~/.claude/settings.json`.
- **Manual mode, web access behind a prompt, the sandbox:** [safety.md, "Stronger options"](safety.md#stronger-options).
- Keep Claude asking before it edits its own settings. After a change, check in a new session with `/status` and `/hooks` that it took.

## Moving the workspace

The installer asks where the workspace goes and writes that location into the installed files. To move it later:

1. **Tell the git helper.** Write the absolute path as the only line of `~/.claude/workspace-root` (`C:\Users\you\work`, `C:/Users/you/work`, `/c/Users/you/work` and `~/work` all work), or set the `CLAUDE_WORKSPACE_ROOT` environment variable, which wins over the file. The helper gives new projects their local git history only inside the workspace.
2. **Update the files that name the default.** `grep -rl '~/Documents' ~/.claude/CLAUDE.md ~/.claude/rules ~/.claude/skills ~/.claude/agents ~/.claude/templates "<new folder>"` lists them, starting with the profile import in `~/.claude/CLAUDE.md`; replace the path in each. If the new path contains spaces (a OneDrive folder such as `OneDrive - Contoso`), the import line, the one starting with `@`, needs a backslash before each space and no quotes: `@~/OneDrive\ -\ Contoso/Documents/_CONTEXT/user-profile.md`. Claude Code reads an import path only up to the first unescaped space and does not import a quoted one. Everywhere else, write the path as it is, in double quotes in shell commands. Check in a new session by asking Claude what your profile says.
3. **Renamed `_APPS` or `_CLIENTS`?** The git helper recognizes these two folders by name and never makes one of them a repository. Under another name that guard does not apply, so run `/setup` inside a project or client folder, never in the container itself.

On Windows, Documents is often synced to OneDrive, and everything under it, client folders included, is then uploaded. If that is not acceptable, keep the workspace in a local folder such as `C:\Users\you\work`.

## Removing what you do not want

| Remove | Effect |
|---|---|
| `~/.claude/skills/<name>/` | That skill is gone; nothing else depends on `prd-creator` or `idea-file-creator` (two rules mention `idea-file-creator`; harmless if removed) |
| `~/.claude/workflows/research.js` | The deepest research level is unavailable; the `research` skill uses the research lead instead. Keep `scripts/check_source.py`: every research level uses it to check sources |
| The `statusLine` block in `settings.json` | No status line |
| The `UserPromptSubmit` hook | Claude no longer knows the time of day, so dated entries may be off |
| `_CLIENTS/_example-client/`, `_APPS/_example-app-transcribe/` | The examples are gone |

Keep the safety net: the `deny` list; `scripts/bash-safety-extended.py`, `scripts/python-launcher.sh` and `scripts/python-launcher.py` with their hook entries; and the rules `respect-denies.md` and `untrusted-content.md`. To remove the whole install, follow [INSTRUCTIONS.md, "Undo everything"](../INSTRUCTIONS.md#undo-everything).

## Updating the pack

The pack does not update itself, on purpose: an update that rewrote `settings.json` would wipe your changes. To take a newer version, update Claude Code (`claude update`), run `git pull` in the cloned folder (downloaded as a ZIP: download and unzip the new ZIP instead), start Claude Code there and ask it to follow `INSTRUCTIONS.md` again: it backs up `~/.claude/`, compares the new version with what you have, merges with your consent, and moves files that are no longer used into the backup. If you changed the pack's hooks, `python3 -m unittest discover -s tests` in the cloned folder runs their tests.
