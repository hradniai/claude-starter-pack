<notes_convention>

## Notes.md — Writing and Behavior

`notes.md` is a per-project file for ideas, impulses, and things to explore. It is NOT a task list (those belong in WORKSTATE.md).

Every workspace and every project has its own local `notes.md`.

### Writing
- Every entry must have a timestamp: `## YYYY-MM-DD HH:MM`
- Always write to the **local** `notes.md` of the current project/workspace
- Keep confirmation minimal — no verbose feedback when the user adds a note

### Research auto-trigger
- When a note contains the marker `→ research`, the user wants research on that topic.
- **Do NOT start research yourself** — just write the note to `notes.md`.
- The hook `~/.claude/hooks/notes-research.sh` detects the marker, dispatches research in the background (using the `general-purpose` subagent per `subagent-rules.md`), and updates the note entry with a path to the result file when complete.
- Research files use the convention `{topic}-research-{YYYY-MM-DD}.md` per `subagent-rules.md`.

### Configuration
The hook reads `ANTHROPIC_API_KEY` (and optionally `ANTHROPIC_MODEL`) from `~/.claude/.env`. If the key is not set, the hook silently no-ops and Claude treats the `→ research` marker as a plain text annotation — no auto-research happens.

### Cost note
Each `→ research` marker triggers an API call and consumes tokens. To disable temporarily, comment out the hook in `~/.claude/settings.json` or remove `ANTHROPIC_API_KEY` from `~/.claude/.env`.

</notes_convention>
