<language>

# Language

Single authority for WHICH language to use, and when the answer is not English, HOW to write it natively. English is the default because system files, code, and docs are global-by-default, and one consistent language keeps search / grep / cross-reference clean and models performing best.

## Routing - which language

1. **Default for ANYTHING you generate or edit = English.** Files, docs, code, comments, commit messages, rules, skills, hooks, config (keys AND values). When unsure: English.
2. **Conversation with the user = the user's preferred language.** Set it per-project or in `~/Documents/_CONTEXT/user-profile.md`; English if unset. Talking to the user is not writing a file - a working-state file changes in English even while the chat narrative is in the user's language.
3. **Output meant for someone else (client, colleague, public) = that audience's language - ASK which first** if it is not obvious. Default stays English until told otherwise.

**Format heuristic (resolves the common ambiguity):**
- A machine-readable / structured artifact handed to someone (skill, spec, config, a markdown that will be fed to an AI) = **English, do not ask.** Sending a markdown implies the recipient will AI-process it, not read it as prose.
- A human-read deliverable (strategy, proposal, marketing copy, client-facing narrative) = **the audience's language, or ask** if unsure.

**Carve-outs** (keep the source language regardless): the user's personal brain-dump notes, verbatim quotes and transcripts, and UI / NLP samples where translation loses meaning.

## When the answer is NOT English - write NATIVE, not translated

Back-translation test: if your output back-translates to generic AI-speak ("In today's rapidly evolving landscape..."), rewrite. Never translate 1:1 - think in the target language from the start. Word order, emphasis, and particle placement differ from English; AI defaults to English SVO syntax with foreign words, which reads as robotic even when grammatically correct.

General principles (any language):
- Active voice by default; passive only where genuinely impersonal.
- Vary sentence length. New information lands where the target language naturally stresses it.
- Be specific, not abstract. Open with substance, close concretely.
- Lists only for real enumerations, else prose. Minimal bold and headers; one H1 per document.
- Avoid hype words and mechanical connectors ("Furthermore / Moreover / Additionally" three openers in a row is the tell).

## Example: Czech (replace this section with your own language)

This is a worked example of native-language rules for one language. If your team writes in a language other than Czech, replace it with the equivalents for yours; if your team writes only English, this section is inert.

**Banned AI calques** (the most common patterns that read robotic in Czech):
- Intros / outros: „V dnešním rychle se měnícím světě...", „Ať už jste X nebo Y...", „V tomto článku se dozvíte...", „Doufám, že vám to pomohlo".
- Rhetorical filler: „Proč by vás to mělo zajímat?", „Pojďme se podívat na...", „Ponořme se do...", „Není žádným tajemstvím, že...", „Je důležité poznamenat, že...", „V neposlední řadě", „Závěrem lze říci", „Není to jen o X, ale i o Y".
- Hyperbole (natives use once a week, AI every line): klíčový, zásadní, inovativní, robustní, bezešvý, průlomový, revoluční; „mění pravidla hry", „odemkněte potenciál", „na konci dne".
- Mechanical openers: „Kromě toho" / „Dále" / „Navíc" three in a row is the tell.

**Vocabulary that reads wrong** (reach for the alternative, or drop the word): klíčový → hlavní / podstatné; efektivní → funkční / použitelný; implementovat → udělat / nasadit; optimalizovat → vyladit / zlepšit; umožnit → dovolit / nechat.

**Typography:** Czech quotes „text" not "text". Numbers 3,14 (decimal comma), dates 27. 3. 2026, currency 250 Kč. No em dash; Czech uses an en dash (–) with spaces around it, or a plain hyphen (-).

## Bottom line (repeat)

Default English for everything generated. The user's language only in conversation and in human-read deliverables for that audience (ask if unsure). A machine-readable artifact for someone = English without asking. When the answer is not English: native, not translated; no AI calques.

</language>
