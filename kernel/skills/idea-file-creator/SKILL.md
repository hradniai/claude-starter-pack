---
name: idea-file-creator
description: Use ONLY on explicit ask to capture or park an idea - "make this an idea file" / "udělej z toho idea file", "capture this idea" / "zapiš tohle jako idea file", "park this for later" / "odlož to na později", a brain dump to capture, or "extract the ideas from this conversation" / "z týhle konverzace vytáhni nápady" (-> one file per idea). NEVER create idea files automatically. NOT a finished implementation, config runbook, or reference doc.
metadata:
  title: Idea File Creator
  summary: "Captures an idea as a self-contained, leak-free, machine-readable markdown that structures the thought, its reasoning, and the proposed approach so far (an ADR for ideas), for handoff or parking - with an optional short develop pass that sharpens a raw idea before capture."
  client: ""
  status: approved
  type: core
  version: "1.0.0"
  release: latest
  tags: [skill, idea-file, ideation]
  created: 2026-06-25 00:05
  updated: 2026-06-25 00:05
  owner: Šimon Hradní
  path: .claude/skills/idea-file-creator/SKILL.md
---

# Idea File Creator

An idea file structures a thought, its reasoning, and the proposed approach so far - like an ADR, but for an idea instead of a decision. It is a **machine-processed artifact**: written to be parsed and acted on by an AI (and read by a human reviewer), so it is always **English**, precise, and descriptive.

Two purposes - and they govern how much detail and how much of the author's own know-how the file carries:
- **internal** - the author's own idea, kept to return to later. Put in the MAXIMUM detail available, including their own know-how, reasoning, and any worked-out approach. It is for them. (If they later decide to send it to someone, sanitizing it first is their call.)
- **handoff** - the idea is passed to someone else. Necessary detail must be there (a handoff with no substance is useless), but be careful with proprietary know-how - include what the recipient needs to act, hold back hard-won internal methods unless the author says to share them. Also omit the `location` path from the frontmatter.

Determining which it is comes FIRST - see "How to run".

## Writing standard (non-negotiable)

- **English, always.** Idea files are machine-processed; never write them in another language.
- **Descriptive and precise, never colloquial.** Write "Onboarding of new team members is currently ad hoc; standardize it via a single starter pack." Do NOT write "let's sort out onboarding". No chit-chat, no first-person chatter in headings or body.
- **Include the detail that exists; do not pad and do not strip.** When a proposed workflow, steps, procedures, or components already exist, write them down (framed as a first proposal). Do not invent detail to look complete, and do not artificially reduce a well-thought idea to a bare stub. The line it must not cross: a committed/finished implementation or a literal config runbook - that is a different artifact.

## The hard property: self-contained and leak-free

An idea file must work pasted into a stranger's blank ChatGPT/Gemini with zero context. So: NO references to the author's files, rules, memory, paths, or repos; NO sensitive/client data; nothing that only makes sense inside their setup. The reasoning and the approach travel; the data does not. Add specifics only if the author explicitly asks.

## How to run this skill

Triggered only by an explicit request (see description). First decide **capture or develop**: just capture the thought as it is, or spend a few questions sharpening it first (see **Develop mode** below)? Signals: "quickly note this" / "park this" -> capture; "help me think this through", or a clearly raw, half-formed idea -> develop. Default to a clean capture unless asked. Then:

1. **Determine handoff vs internal FIRST.** If the author hasn't already signalled it, ASK ("Is this a handoff to someone, or internal just for you?"). Signals you can read without asking: "I'll send this to a colleague" -> handoff; "park this / for later / note to self" -> internal. This choice sets how much of the author's own know-how the file may carry (see Two purposes).
2. **Take the input** - a brain dump, "capture this idea", or "extract the ideas from this conversation".
   - If the source is a past conversation NOT in your current context (e.g. "pull ideas from today's whole session" after a long/compacted chat), read the transcript via a cheap subagent and have it return the candidate ideas. If the idea is already in context, use it - no subagent.
   - "Extract N ideas" -> produce N separate idea files.
3. **Recap, and propose the outline IN CHAT before writing the file** - the sections plus the concrete details you intend to include, already calibrated to the handoff/internal know-how level. Surface the thought-through details that exist (proposed approach, workflow, the exact specifics already decided) - do NOT strip them; details are usually the point. The author can then tell you "add more here" or "this is too detailed / hold that back" before anything is written.
4. **Ask only about genuine gaps** - what is under-defined or unclear. Do NOT add your own opinion or expand the idea itself; it is the author's thought, as they see it. Push back only if the idea is genuinely nonsense. Do not push to close.
5. **The author approves** -> write the idea file, folding in their refinements; fill "Open questions and pending work" with what is still missing or undecided (listing gaps, not adding content).

## Develop mode (optional, short)

When asked to develop rather than just capture, sharpen the raw idea with a few pointed questions BEFORE writing it down - enough that the idea file reads whole to someone hearing the idea for the first time. This is deliberately SHORT: **2-3 sharp questions, asked ONE at a time, then stop.** It is not a checklist and not a gate. Pick the 2-3 the idea most needs from these:

- **Goal vs solution** - what is the person really trying to achieve, and is this idea the best way to get there? (Often reframes the whole idea.)
- **The strength** - what makes this worth doing: what does it do that the obvious existing alternative does not?
- **The hinge** - what one thing has to be true for this to work, or the smallest way to find out if the core holds?

How to run it:
- Ask, then let the person talk. Do NOT pre-load your own answer into the question - the point is to draw THEM out. Save any hypothesis of your own for after they have spoken, framed as a reflection, never as a hint inside the question.
- One question at a time, each shaped by the last answer; go a little deeper rather than wider.
- Develop and sharpen THEIR thought; never substitute your own idea for theirs, and never inflate the scope.
- Stop after 2-3 questions, or the moment they say "enough". Fold what surfaced into the idea file (a sharper Summary / Context / Proposed approach; unresolved gaps into Open questions).

Deeper, longer development of an idea is a separate activity, not this skill.

## Idea file format

Frontmatter (YAML):
```yaml
---
type: internal             # internal | handoff
status: active             # active | superseded | outdated | cancelled
owner: Šimon Hradní
created: 2026-01-01 12:00
updated: 2026-01-01 12:00
location: projects/example # path-derived (see Naming). OMIT this field when type: handoff; the location still lives in the filename.
# superseded_by: <filename> # only when status: superseded
---
```

Body (English, descriptive headings):
```
# <Descriptive title>

## Summary
Two or three sentences stating the idea precisely.

## Context and reasoning
The situation or problem and why it matters - the reasoning behind the idea.

## Proposed approach
The current thinking on how to address it, with whatever concrete detail already exists (proposed workflow, steps, components) framed as a first proposal, not a commitment.

## Scope and audience
Who it is for, the intended outcome, the boundaries.

## Open questions and pending work
What must still be done or decided (research, brainstorm, competitor check, validation, open decisions). Listing only.
```

## Status lifecycle (never delete)

Idea files are never deleted, only re-marked:
- `active` - live.
- `superseded` - a newer idea file replaces it; set `superseded_by`.
- `outdated` - stale with no successor.
- `cancelled` - dropped.

## Naming and location

- Filename: `<location>-<title>-idea-file-<YYYY-MM-DD>.md`. Date last (least important sort key). The location ALWAYS stays in the filename (even for `handoff`, where it is omitted only from the frontmatter) - it is what lets an agent find a workspace's idea files. Example: `projects-example-conversation-retention-idea-file-2026-01-01.md`.
- **`location` is DERIVED FROM THE WORKSPACE PATH, deterministically - never translated.** Take the workspace path relative to your projects root, lowercase it, strip a leading underscore from each segment; in the filename join segments with `-`, in the frontmatter keep them as a `/` path. So a workspace `_PROJECTS/EXAMPLE` -> filename prefix `projects-example`, frontmatter `location: projects/example`. WHY: a future agent computes the same token from its own working directory and matches with zero lookup table.
- On disk: keep ALL idea files in ONE central folder you designate (for example `~/idea-files/`), no matter which workspace you are working in. Never create a workspace-local copy. The location token (filename prefix + the `location` field on `internal` files) is what associates an idea with its workspace, so the single central folder holds everything and an agent scans that one folder and filters by location + status. WHY: a workspace-local copy fragments the store - an agent looking for "all ideas" only scans the central folder and would silently miss anything parked elsewhere.

## If it matures

A lightweight idea stays a single idea file. When it grows into something to build, it gets a PRD or spec alongside it - the idea file frames the intent, the PRD specifies it.

## Output

The idea file in your central idea-files folder - ALWAYS the central directory, never a workspace-local folder. Confirm where you saved it. Keep it tight - long enough to carry the reasoning and the proposed approach, no padding.

## Document frontmatter

Every idea file carries the small YAML frontmatter shown under "Idea file format" (`type`, `status`, `owner`, `created`, `updated`, `location`, optional `superseded_by`). `created` / `updated` use `YYYY-MM-DD HH:MM`. Keep it minimal; the body carries the substance.
