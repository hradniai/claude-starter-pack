---
type: context
title: "documentation-standard"
status: active
summary: ""
created: 2026-06-13
updated: 2026-06-16
created_by: Šimon Hradní
client: ~
path: kernel/rules/documentation-standard.md
tags: [standard]
---

<documentation_standard>

## Format & structure (follow Anthropic / Claude conventions)

Docs in this system are read by Claude first and humans second - structure them the way Claude reads best.

- **XML tags for structural boundaries**, Markdown inside sections. XML is Claude's primary structuring mechanism (it's trained on it) - wrap major sections (`<purpose>`, `<constraints>`, `<output_format>`, …).
- **Critical rules at the START and END** - the middle of a long document gets ignored. Repeat hard constraints top and bottom.
- **Purpose over role** - state what needs to happen and WHY, not "you are an expert…". Goal framing beats role framing.
- **Always explain WHY a constraint exists.** Motivation increases adherence ("never fabricate - output feeds production" > "never fabricate").
- **Every line must earn its context cost.** Optimal, not minimal: keep what changes behavior, cut filler. If removing it makes the doc worse, keep it; else cut.
- **Trust capable models - don't pad with scaffolding** the model already does on its own ("double-check before returning", "give status updates", "don't generalize"). Add instruction only where it measurably changes output.
- **Force the format you want** - if you need only a given structure, say "output ONLY X, nothing else". Capable models trend verbose by default.

## Project Documentation (non-negotiable)

Autocompact WILL destroy context. Documentation is the only defense.

### Hard triggers

1. First edit in any project → check `README.md` and `WORKSTATE.md` exist; create if not.
2. After every logical step → append to the WORKSTATE engineering log (structure below).
3. Before saying "done" → verify `WORKSTATE.md`, `README.md`, and (if directional decisions fell) `docs/decision-log.md` reflect reality.

### Files

- **`CLAUDE.md` / `AGENTS.md`** - per workspace root, never in subdirectories. Purpose, tech stack, architecture, constraints. (AGENTS.md canonical, CLAUDE.md symlink - see the `setup` skill.)
- **`WORKSTATE.md`** - per project AND per subproject. Append-only project journal that survives autocompact. Fixed structure below.
- **`README.md`** - per project / subproject. Polished changelog with dates, current state, features, known issues, setup. The outward-facing "open it cold" document.
- **`docs/decision-log.md`** - per project / subproject. Running table of smaller directional decisions (the tier below ADR). Convention below.
- **ADR** (`decisions/*.md`) - formal record of big, hard-to-reverse decisions. See `adr.md` + the `adr` skill.

### WORKSTATE.md structure (fixed - enforced so partial-load works)

```
# WORKSTATE: <project>
## Focus              live header: current focus / pending / next. Mutable, tiny.
## Related context    few doc links to load to grasp context. Per project, no hard limit, keep short. Mutable. (Not CLAUDE.md - auto-loaded.)
## Current state      project situation: what is happening, where it stopped, current challenges, weekly session, pointer to any overnight-homework file. Mutable summary.
## Sub-project work states   pointers (name + one line + link). Append-only, added when a sub-WORKSTATE is created.

<!-- ═══ WORKSTATE MARKER 1 · LIVE ABOVE · LOG BELOW ═══ -->

## Engineering log    append-only, NEWEST FIRST. One dated `### YYYY-MM-DD HH:MM` block per logical step: what was done, why, links to decisions / ADRs.

<!-- ═══ WORKSTATE MARKER 2 · CHANGELOG BELOW ═══ -->

## Changelog          short running one-liners per notable change, for quick orientation; loadable standalone.
```

### WORKSTATE rules

- **Append-only. Never delete anything.** The ONE exception: when `/end` writes a pending ADR, it rewrites the "ADR needed on X" note into "ADR-NNN - <link>" (a rewrite, not a deletion).
- Engineering log is **newest first**.
- **NEVER read the whole WORKSTATE. Hard rule, not a preference - a full read is a defect.** At session start and after autocompact, read ONLY the part above MARKER 1 (Focus + Related context + Current state + Sub-project pointers). For recent context read the top 1-3 log blocks just below MARKER 1. For a fast recap read the Changelog (below MARKER 2) on its own. Go deeper into the log only when a specific question demands it, and then by section - never the entire file. WORKSTATE is primarily a document for Claude, not for the human. The marker structure exists precisely to make this enforceable.
- Version all changes with dates. WORKSTATE is no longer deleted on completion - it is the project's history.

### docs/decision-log.md (smaller directional decisions)

- One per project and per subproject, in `docs/` (NOT root - keeps the root clean so it is not opened needlessly).
- Format: a table grouped by theme, with a one-line purpose header. Columns `| # | Decision | Who, when | Why | Detail |` (IDs D1, D2, …). Append-only.
- The tier BELOW ADR. When a decision meets the ADR bar (2 of 3: cross-project, rejected alternatives, hard to reverse) it becomes an ADR; the decision-log / WORKSTATE then point to it.

### Sub-projects

- A folder with its own purpose under a client's `depts/` or `projects/` (or a deliberately separated part of an app) is a **sub-project** and gets its own `WORKSTATE.md`, `docs/decision-log.md`, and `README.md`.
- Write detail into the NEAREST (most specific) WORKSTATE. When a sub-WORKSTATE is created, register a one-line pointer in the parent's "Sub-project work states" section. No content roll-up - "when worked on what" already lives in the worklog.

## Idea files (capturing a thought)

An **idea file** structures a thought, its reasoning, and the proposed approach so far - an ADR, but for an idea instead of a decision. It holds the IDEA and its proposed approach, never a finished implementation/config ("let's solve X by making a repo, here's my first notion and why" - not the repo, not the steps, not a link). Two purposes: **internal** (park your own idea to return to it - maximum detail, including private know-how) and **handoff** (pass it to someone - the detail they need, holding back proprietary know-how). Idea files are machine-processed artifacts: always English, descriptive and precise.

Hard property: **self-contained and leak-free.** An idea file must work pasted into a stranger's blank chatbot with zero context - no references to files/rules/memory/paths, no sensitive data, unless explicitly added. The reasoning and the approach travel; your data does not.

- **Created only on explicit ask**, never automatically (capture this / brain dump / "extract N ideas from this conversation" → N files). Determine **handoff vs internal first** (ask if unsignalled) - it sets how much of the author's own know-how the file may carry.
- **Idea file + PRD** once an idea matures into something to build - the idea file frames it, the PRD specifies it (`prd-creator`).

Frontmatter: `type` (internal | handoff), `status` (active | superseded | outdated | cancelled - never deleted, only re-marked; `superseded_by` when relevant), `created_by`, `created`, `updated`, `location` (path-derived; OMITTED when `type: handoff`). Body (English, descriptive headings): Summary / Context and reasoning / Proposed approach / Scope and audience / **Open questions and pending work** (the gaps to address later).

Naming: `<location>-<title>-idea-file-<YYYY-MM-DD>.md` (date last). `location` is derived from the workspace path (lowercased, leading `_` stripped). All idea files live in a central idea-files folder; the location token ties each idea back to its origin workspace so the folder stays scannable.

Full methodology (recap-and-ask flow, no opinions/expansions, Haiku-subagent transcript reads only when not in context) lives in the **`idea-file-creator` skill** - load it, don't reproduce from memory (same pattern as ADRs loading the `adr` skill).

## Frontmatter (every markdown document)

Every markdown artifact carries a small YAML frontmatter core (`type`, `status`, `summary`, `created`, `updated`, `created_by`, `client`, `path`, `tags`) so an agent orients from the frontmatter alone without reading the body. `type` is one of 7 CLOSED buckets (core / strategy / product_design / research / devops / context / notes); the fine kind, technology, and topic live in `tags`. The full standard (bucket definitions, the predefined tag vocabulary, per-loader rules for skills/agents/plugins/system docs, OKF alignment) lives in `~/.claude/rules/frontmatter-standard.md` - a reference, not auto-loaded; skills read it on demand. An OKF-conformant superset (Google Open Knowledge Format). Kept there, not inline, so this rule does not bloat.

## Language

→ Moved to `~/.claude/rules/language.md` (single authority: English by default; the team's language only in chat and in human-read deliverables for others, ask-first). This rule no longer governs language.

## Content

- No specific client names, person names, or identifying examples in system files. Use placeholders: `<client>`, `<project>`.

## App Skill Maintenance

When modifying any app that has a linked skill in `~/.claude/skills/`, after completing the changes, prompt the user to review and update the corresponding `SKILL.md`.

---

**Bottom line:** technical artifacts = English (see `language.md`), structured per Anthropic / Claude conventions (XML, purpose-first, constraints top+bottom, explain-why). WORKSTATE is the append-only per-project / subproject journal (live header above MARKER 1, newest-first log below, changelog at the bottom); README is the polished changelog; `docs/decision-log.md` is the lighter decision tier under ADR. Documentation is non-negotiable - autocompact destroys context, files are the defense.

</documentation_standard>
