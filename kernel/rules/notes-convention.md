---
type: notes
title: "notes-convention"
status: approved
summary: "Convention for per-project notes.md files with auto-research workflow that evaluates unmarked entries and assigns research markers."
created: 2026-05-07 00:33
updated: 2026-05-07 17:13
owner: Šimon Hradní
client: ~
path: kernel/rules/notes-convention.md
tags: [note]
version: "1.0.0"
release: latest
---

<notes_convention>

## Notes.md — Writing and Behavior

`notes.md` is a per-project file for ideas, impulses, and things to explore. It is NOT a task list (those belong in WORKSTATE.md).

Every workspace and every project has its own local `notes.md`.

### Writing format
- Every entry starts with a `## YYYY-MM-DD HH:MM` timestamp.
- Use the **current local time** injected by `~/.claude/hooks/inject-current-time.sh` (auto-added to your context every prompt). Do not guess the time.
- Format below the timestamp can be anything: paragraph, bullets, single word, ### sub-headings. The auto-research workflow is format-agnostic.
- Keep confirmation minimal — no verbose feedback when the user adds a note.

### Auto-research workflow
The hook `~/.claude/hooks/notes-research.sh` watches every Edit/Write to `notes.md`. When it detects any non-blank content after the last marker emoji (or no markers at all), it dispatches a background API call.

The model (Haiku by default) evaluates the unmarked content and writes one of two markers back to `notes.md`:

| Marker | Meaning |
|--------|---------|
| ✅ | Research warranted — full report written to `research/{slug}-research-{YYYY-MM-DD}.md`, link included |
| ⏭️ | Not research-worthy (personal todo, reminder, opinion) — no file written |
| 🔄 | Research dispatched but not yet complete (interim state, may not be visible) |

You don't need explicit `→ research` markers or other triggers. Every unmarked entry gets a verdict.

### Configuration
The hook reads `ANTHROPIC_API_KEY` (and optionally `ANTHROPIC_MODEL`) from `~/.claude/.env`. Without the key the hook is a silent no-op — your notes still save, just no auto-research.

### Cost note
Each unmarked entry triggers an API call (Haiku is cheap; ~$0.001–0.01 per call depending on length). To disable temporarily, comment out the hook in `~/.claude/settings.json` or remove `ANTHROPIC_API_KEY` from `~/.claude/.env`.

### Web search caveat
By default the hook calls the API without the `web_search` server tool — research is limited to the model's training knowledge. For real web research, edit `notes-research.sh` and add the `web_search` tool to the request payload (check Anthropic docs for the current tool name).

</notes_convention>
