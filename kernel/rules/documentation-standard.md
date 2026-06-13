<documentation_standard>

## Format
- XML tags for structural boundaries, Markdown inside sections
- Critical rules at START and END of documents - middle gets ignored
- Motivation increases adherence - always explain WHY a constraint exists
- Purpose over role - state what needs to happen, not who you are
- Every line must earn its context cost

## Project Documentation (non-negotiable)
Autocompact will destroy context. Documentation is the only defense.

### Hard triggers
1. First edit in any project → check README.md and WORKSTATE.md exist, create if not
2. After every logical step → update WORKSTATE.md
3. Before saying "done" → verify WORKSTATE.md and README.md reflect reality

### Files
- **AGENTS.md** - per workspace root (canonical). Purpose, tech stack, architecture, constraints. Cross-tool standard (Cursor, Codex, Gemini CLI, Aider, Claude Code via CLAUDE.md symlink).
- **CLAUDE.md** - symlink to AGENTS.md. Claude Code reads this natively; same content as AGENTS.md.
- **WORKSTATE.md** - per active subproject. Append-only working journal that survives autocompact. A small live header on top (current task, pending, next steps); below it a dated log, newest entries first. Always timestamp entries (YYYY-MM-DD HH:MM).
- **README.md** - per subproject. Changelog with dates, current state, features, known issues, setup.

### Rules
- On session start, read WORKSTATE.md first if it exists
- WORKSTATE.md is append-only - never delete it. It is the project's journal and survives autocompact precisely because it is not reset. Add new log entries newest-first; when a task completes, record that in the log and in README.md rather than wiping the file
- Version all changes with dates
- Outdated docs are worse than no docs

## Language
Language routing (which language to use) and native-language quality (how to write non-English output well) are owned by `language.md`. This file no longer governs language.

## Content
No specific client names, person names, or identifying examples in system files - use generic placeholders (`<client>`, `<project>`).

</documentation_standard>
