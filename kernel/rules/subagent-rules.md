<subagent_rules>

## When to use
Dispatch parallel subagents when 2+ subtasks are independent. Subagents protect main context from bloat. Don't force it for sequential or trivial tasks.

**Research = `general-purpose` subagent.** Any non-trivial research (web search, documentation lookup, multi-source verification) MUST go through a subagent — specifically the **`general-purpose`** subagent type. Built-in `general-purpose` reliably has WebSearch, WebFetch, and access to user-scope MCP servers. Other subagent types (custom agents in `~/.claude/agents/`, plugin-provided subagents) have known MCP-visibility bugs (Claude Code issues #13898, #13605) and may silently hallucinate MCP results — do NOT use them for MCP-dependent research.

The main context must never be polluted with raw search results or fetched pages. Subagent returns maximum detail (not just a summary) so the main context can make informed decisions without re-researching.

## Inheritance — what subagents do and don't see
- **Permissions** (`settings.json` allow/deny): inherited from main session
- **Working directory**: inherited
- **Environment variables**: inherited
- **CLAUDE.md / AGENTS.md**: NOT inherited (subagent has only its own system prompt + your dispatch prompt)
- **Rules in `~/.claude/rules/`**: NOT inherited
- **Skills**: NOT inherited (must be listed in custom agent `skills:` frontmatter; built-in agents cannot directly preload skills)

**Practical implication:** if a subagent's output must follow project conventions (naming, format, language, file paths), include those conventions explicitly in the dispatch prompt. The subagent will not "know" your CLAUDE.md.

## Model selection
- **Haiku**: simple lookups, formatting, translations
- **Sonnet**: medium complexity — summaries, non-technical research, copy
- **Opus**: architecture, debugging, code changes, deep technical analysis

Pick the cheapest model that can handle the task.

## Prompt quality
Give maximum context — background, constraints, expected output, file paths, decisions. Subagent has NO access to parent conversation. Treat the dispatch prompt as a self-contained brief for someone who just walked into the room.

## Reporting (mandatory)
Full transparency. On errors: exact error message, what was attempted, which tool/step. Never summarize as "didn't work."

On success, report any: deviations from instructions, retry attempts, fallback strategies, assumptions made, partial failures, unexpected behaviors.

## Research output convention
- **Substantial research** (best practices, competitor analysis, technology deep-dives, multi-source verification): always save full findings to a file `{topic}-research-{YYYY-MM-DD}.md` in the project's `research/` dir. The file IS the deliverable. Return a concise verdict to the main context.
- **Smaller research** (single-topic lookup, quick verification): no file needed, but return MAXIMUM data — full details, exact quotes, specific findings, edge cases. Never just a bare summary.

</subagent_rules>
