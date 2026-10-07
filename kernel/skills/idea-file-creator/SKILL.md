---
name: idea-file-creator
description: Capture or park an idea as a self-contained idea file, ONLY on an explicit ask - "make this an idea file", "capture this idea", "park this for later", "note this idea down", a brain dump to capture, or "extract the ideas from this conversation" (one file per idea). Never create idea files on your own initiative. Not for a finished implementation, a config runbook or a reference doc.
metadata:
  type: core
  status: active
  summary: "Captures an idea as a self-contained, leak-free English markdown file (an ADR for ideas) for parking or handoff, with a short interview that empties the author's head before an internal idea is parked."
  created: 2026-06-25
  updated: 2026-10-06
  created_by: claude-starter-pack
  client: ~
  tags: [skill, idea-file, ideation]
---

# Idea File Creator

An idea file structures a thought, its reasoning and the proposed approach so far - like an ADR, but for an idea instead of a decision. It is a machine-processed artifact: written to be parsed and acted on by an AI and read by a human reviewer, so it is always **English**, precise and descriptive.

Two purposes, and they set how much detail and how much of the author's own know-how the file carries:
- **internal** - the author's own idea, parked to return to later. Put in the MAXIMUM detail available, including their know-how, reasoning and any worked-out approach. It is for them; sanitizing it before sending it anywhere is their call.
- **handoff** - the idea goes to someone else. The necessary detail must be there (a handoff with no substance is useless), but hold back hard-won internal methods unless the author says to share them, and leave out the `location` and `path` fields.

## Writing standard

- **English, always**, whatever language the conversation is in.
- **Descriptive and precise, never colloquial.** Write "Onboarding of new team members is ad hoc; standardize it with a single starter checklist." Not "let's sort out onboarding". No first-person chatter in headings or body.
- **Include the detail that exists; do not pad and do not strip.** A proposed workflow, steps or components that already exist are written down, framed as a first proposal. Do not invent detail to look complete, and do not cut a well-thought idea down to a stub. The line it must not cross: a finished implementation or a literal config runbook is a different artifact.

## The hard property: self-contained and leak-free

An idea file must work pasted into a stranger's blank chatbot with zero context. So: no references to the author's files, rules, memory, paths or repositories; no sensitive or client data; nothing that only makes sense inside their setup. The reasoning and the approach travel; the data does not. Add specifics only when the author explicitly asks.

## How to run it

Run only on an explicit request (see the description).

1. **Handoff or internal, first.** If the author has not signalled it, ask: "Is this a handoff to someone, or internal, just for you?" Signals you can read without asking: "I'll send this to a colleague" -> handoff; "park this", "for later", "note to self" -> internal.
2. **Capture or interview.**
   - **internal -> interview by default** (Develop mode below). People park an idea so they can stop carrying it around, and that only happens once they have been asked enough to empty their head; a silent recap does not do it.
   - **handoff, or an explicit "just note this" / "quick capture" -> capture** without an interview. The outline in step 4 still comes first.
3. **Take the input** - a brain dump, "capture this idea", or "extract the ideas from this conversation" (N ideas -> N files). If the source is a conversation that is no longer in your context (for example after a compaction), have a cheap subagent (Haiku) read the session transcript and return the candidate ideas; if the idea is in context, use it directly.
4. **Recap and propose the outline in chat before writing, in every mode**: the sections plus the concrete details you intend to include, already calibrated to the internal/handoff level. Surface the details that were thought through (approach, workflow, exact specifics); details are usually the point. The author can then say "add more here" or "hold that back" - for a handoff this is their only chance to keep know-how out of a file that leaves their hands.
5. **Ask only about real gaps.** Do not add your own opinion or expand the idea: it is the author's thought as they see it. Push back only if it is genuinely nonsense.
6. **On approval, write the file**, folding in their refinements; "Open questions and pending work" lists what is still missing or undecided.

## Develop mode - the brain-dump interview

Default for internal ideas; skipped for handoff or an explicit quick capture. It serves two purposes, and the second is the one that gets forgotten:

1. **Sharpen the idea**, so the file reads whole to someone hearing it for the first time.
2. **Empty the author's head**, so they can let the thought go. A file that captures 80% of a thought leaves the rest rattling around, and the relief - the reason they asked - does not happen.

It is an interview, not a checklist. Pick the questions the idea most needs:

- **Goal vs solution** - what are they really trying to achieve, and is this idea the best way there?
- **The strength** - what does this do that the obvious existing alternative does not?
- **The hinge** - what has to be true for this to work, or the smallest way to find out whether the core holds?
- **The unsaid** - what were they picturing that has not been said out loud yet? Follow the part they got animated about.

How to run it:
- **One question at a time**, each shaped by the last answer; go deeper rather than wider.
- Ask, then let them talk. Do not load your own answer into the question; if you have a hypothesis, offer it after they have spoken, as a reflection.
- Develop THEIR thought: never substitute your idea for theirs and never inflate the scope.
- **Always close with the completeness check:** "Is there anything else about this still in your head?" Keep going while it produces something new.

Stop when they say enough, when the completeness check comes back empty, or when two questions in a row produce nothing new. Fold what surfaced into Summary / Context / Proposed approach; unresolved gaps go to Open questions. Longer development of an idea (strategy sessions, validation) is a different activity, not this skill.

## Idea file format

Frontmatter follows `~/.claude/rules/frontmatter-standard.md` (read it if it is not loaded yet): the common core plus the idea-file fields.

```yaml
---
type: notes
title: "Descriptive title"
status: active                 # active once the author approved it in step 6; draft before that
summary: "One or two sentences stating the idea."
created: 2026-01-01            # YYYY-MM-DD
updated: 2026-01-01
created_by: jane               # the author's slug
client: ~                      # stays ~ in a handoff unless the author says otherwise
path: _CONTEXT/idea-files/projects-example-retention-idea-file-2026-01-01.md   # internal only
tags: [idea-file]              # plus topic tags
handoff: internal              # internal | handoff
location: projects/example     # internal only, path-derived (see Naming)
# superseded_by: <filename>    # only with status: superseded
---
```

For `handoff: handoff`, omit `location` and `path` (the location token still stays in the filename).

Body (English, descriptive headings):
```
# <Descriptive title>

## Summary
Two or three sentences stating the idea precisely.

## Context and reasoning
The situation or problem, why it matters, the reasoning behind the idea.

## Proposed approach
The current thinking on how to address it, with whatever concrete detail exists, framed as a first proposal, not a commitment.

## Scope and audience
Who it is for, the intended outcome, the boundaries.

## Open questions and pending work
What must still be done or decided (research, validation, a competitor check, open decisions). Listing only.
```

## Status lifecycle (never delete)

Idea files are never deleted, only re-marked: `draft` (not yet approved by the author), `active` (live), `superseded` (a newer idea file replaces it; set `superseded_by`), `deprecated` (stale with no successor), `cancelled` (dropped).

## Naming and location

- **One central folder:** `~/Documents/_CONTEXT/idea-files/` (create it if missing), whichever project you are working in. Never a project-local copy: anyone looking for "all ideas" scans that one folder, and a file parked elsewhere is silently missed.
- **Filename:** `<location>-<title>-idea-file-<YYYY-MM-DD>.md`, kebab-case, date last. Example: `clients-acme-conversation-retention-idea-file-2026-01-01.md`.
- **`location` is derived from the working directory, never translated:** take the path relative to `~/Documents/`, lowercase it, strip a leading `_` from each segment; join with `-` in the filename, keep `/` in the frontmatter. `~/Documents/_CLIENTS/acme` -> filename prefix `clients-acme`, `location: clients/acme`. Outside `~/Documents/`, use the folder name. A later session computes the same token from its own directory, so the match needs no lookup table.

## If it matures

An idea that grows into something to build gets a PRD alongside it (the `prd-creator` skill): the idea file frames the intent, the PRD specifies it.

## Output

Write the file, then confirm the path in one line. Keep it tight: long enough to carry the reasoning and the approach, no padding.
