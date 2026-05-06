# Custom Subagents

This directory holds custom subagent definitions. Files here are auto-discovered by Claude Code and made available as subagent types you can dispatch via the `Agent` tool.

## Default state

The starter pack ships this directory **empty**. Built-in subagents (`general-purpose`, `Explore`, `Plan`) cover the most common needs and have known-good MCP / WebSearch behavior.

## When to add a custom subagent

Add a custom agent here only when you need:
- A specialized persona that's reused across many sessions (e.g. a code reviewer with a specific style guide)
- A task that benefits from a stable system prompt + tightly scoped tools
- Skill bundling (custom agents can list `skills:` in frontmatter; built-in agents cannot)

## Caveat: known MCP-visibility bug

As of 2026-05, Claude Code issues [#13898](https://github.com/anthropics/claude-code/issues/13898) and [#13605](https://github.com/anthropics/claude-code/issues/13605) document that custom subagents in this directory may **silently hallucinate MCP tool results** — they appear to call MCP servers but invent the response. This affects both project-scoped and (sometimes) user-scoped MCPs.

Practical implication: **do NOT use custom subagents for MCP-dependent research**. Use the built-in `general-purpose` subagent instead. The starter pack's `~/.claude/rules/subagent-rules.md` enforces this rule in your main session.

If you write a custom agent, prefer tasks that don't depend on MCP calls — pure reasoning, code generation, structured analysis from inline content.

## Format

A subagent file is a markdown file with YAML frontmatter:

```markdown
---
name: my-agent
description: One-line description shown in agent picker.
tools:           # Optional. Defaults to all available.
  - Read
  - Glob
  - Grep
  - WebSearch
skills:          # Optional. Skill bodies are injected into the agent's startup context.
  - some-skill
---

# System prompt for this agent

Multi-paragraph system prompt that sets the agent's behavior, tone, and constraints.
```

## Inheritance reminder

A subagent does NOT inherit:
- Your `CLAUDE.md` / `AGENTS.md`
- Rules in `~/.claude/rules/`
- Skills active in the parent session (must list explicitly in `skills:` frontmatter)

A subagent DOES inherit:
- Permissions from `~/.claude/settings.json`
- Working directory
- Environment variables

When dispatching, treat the prompt as a brief for someone who just walked into the room with no context.
