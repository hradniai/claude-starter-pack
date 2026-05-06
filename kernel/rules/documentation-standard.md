<documentation_standard>

## Format
- XML tags for structural boundaries, Markdown inside sections
- Critical rules at START and END of documents — middle gets ignored
- Motivation increases adherence — always explain WHY a constraint exists
- Purpose over role — state what needs to happen, not who you are
- Every line must earn its context cost

## Project Documentation (non-negotiable)
Autocompact will destroy context. Documentation is the only defense.

### Hard triggers
1. First edit in any project → check README.md and WORKSTATE.md exist, create if not
2. After every logical step → update WORKSTATE.md
3. Before saying "done" → verify WORKSTATE.md and README.md reflect reality

### Files
- **AGENTS.md** — per workspace root (canonical). Purpose, tech stack, architecture, constraints. Cross-tool standard (Cursor, Codex, Gemini CLI, Aider, Claude Code via CLAUDE.md symlink).
- **CLAUDE.md** — symlink to AGENTS.md. Claude Code reads this natively; same content as AGENTS.md.
- **WORKSTATE.md** — per active subproject. Live working state that survives autocompact. Format: Current task, Changes made, Pending/Next steps, Decisions made. Always include "Last updated: YYYY-MM-DD HH:MM".
- **README.md** — per subproject. Changelog with dates, current state, features, known issues, setup.

### Rules
- On session start, read WORKSTATE.md first if it exists
- Delete WORKSTATE.md when task is fully completed and reflected in README.md
- Version all changes with dates
- Outdated docs are worse than no docs

## System Files Language
- All system files (rules, skills, agents, AGENTS.md, hooks documentation) are written in **English**
- No specific client names, person names, or identifying examples in system files — use generic placeholders (`<client>`, `<project>`)
- WORKSTATE.md and README.md follow the language of the project (e.g. local-language projects in that language, English projects in English)

</documentation_standard>
