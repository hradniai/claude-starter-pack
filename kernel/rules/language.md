---
type: core
title: "Language"
status: active
summary: "Which language to use where (English in files, the user's language in conversation, the audience's language in human-read deliverables) and how to write natively when the answer is not English, with a replaceable Czech example."
created: 2026-06-13
updated: 2026-10-06
created_by: claude-starter-pack
client: ~
tags: [rule, language, writing]
---

<language>

# Language

## Which language

1. **Everything you write to files is English:** code, comments, docs, commit messages, rules, skills, config keys and values. One language keeps search and cross-references working, and models perform best in it. When unsure, English.
2. **Conversation is in the user's language:** the one set in `~/Documents/_CONTEXT/user-profile.md` or the project's `CLAUDE.md`, otherwise the language they write in. Talking is not writing a file: a file stays English while you discuss it in theirs.
3. **Output for someone else** (a client, a colleague, the public): a machine-readable artifact (a spec, a config, a markdown someone will feed to an AI) is English without asking; a text people will read (a proposal, an email, marketing copy) is in that audience's language. Ask when the audience is not obvious.

Keep the original language for the user's own notes, verbatim quotes and transcripts, and UI text or samples where translation changes the meaning.

## Writing natively in another language

Write in the target language from the start; never translate sentence by sentence. The test: if your text, translated back, reads like generic AI prose ("In today's fast-paced world..."), rewrite it.
- Active voice, varied sentence length, new information where the language puts its stress.
- Specific over abstract. Open with substance, close with something concrete.
- Lists only for real enumerations, prose otherwise; little bold, few headers.
- No hype words and no mechanical connectors ("Furthermore", "Moreover", "Additionally" in a row is the tell).
- The language's own typography: its quotation marks, decimal separator and date format.

## Example: Czech (replace it with your language, or delete it if you write only English)

- **Calques that read robotic:** „V dnešním rychle se měnícím světě…“, „Ať už jste X, nebo Y…“, „Pojďme se podívat na…“, „Ponořme se do…“, „Je důležité poznamenat, že…“, „Závěrem lze říci“, „Není to jen o X, ale i o Y“, „Doufám, že vám to pomohlo“.
- **Words AI overuses:** klíčový, zásadní, inovativní, robustní, bezešvý, revoluční. Reach for: klíčový → hlavní, efektivní → funkční, implementovat → nasadit, optimalizovat → vyladit, umožnit → nechat.
- **Typography:** quotes „text“, decimal comma 3,14, dates 27. 3. 2026, 250 Kč, a dash written as an en dash with spaces ( – ).

</language>
