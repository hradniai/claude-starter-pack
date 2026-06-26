---
type: notes
title: "LLM model lineup (current)"
status: approved
summary: "On-demand reference for model selection (not auto-loaded). The llm-or-deterministic rule (step 4), the prompt-engineer agent, and any model-choice decision read it."
created: 2026-06-16 00:00
updated: 2026-06-26 00:00
owner: Šimon Hradní
client: ~
path: _CONTEXT/llms/model-lineup.md
tags: [note]
version: "1.0.0"
release: latest
---

<llm_lineup>

# LLM model lineup (current)

> On-demand reference for model selection. NOT auto-loaded into every session. The `llm-or-deterministic` rule (step 4) points here; the `prompt-engineer` agent and any model-choice decision read it. Always re-verify before a production model choice and pin versioned IDs in production (aliases like `-latest` silently drift to a new model). Claude facts come from the bundled `claude-api` skill (authoritative); OpenAI + Gemini verified against official pricing/model pages on 2026-06-26 (see Sources).

## Anthropic (Claude)

Verified against the `claude-api` skill (authoritative source for Claude IDs, pricing, context, limits).

| Model | API id | Context | In / Out per 1M | Use for |
|---|---|---|---|---|
| Fable 5 | `claude-fable-5` | 1M / 128K out | $10 / $50 | Most capable widely released model. Most demanding reasoning + long-horizon agentic work. Thinking always on; no assistant prefill. Requires 30-day retention (NOT available under ZDR). Mythos 5 = same model, Project Glasswing only. Use sparingly - priced above Opus tier. |
| Opus 4.8 | `claude-opus-4-8` | 1M / 128K out | $5 / $25 | Flagship default for serious work + Claude Code default. Long-horizon agentic, knowledge work, memory. Adaptive thinking only. |
| Sonnet 4.6 | `claude-sonnet-4-6` | 1M / 64K out | $3 / $15 | Practical default with prompt caching. Hard reasoning, multi-step, agentic. |
| Haiku 4.5 | `claude-haiku-4-5` (`-20251001`) | 200K / 64K out | $1 / $5 | Cheap routing, strict JSON/YAML schema, light coding. Best instruction-adherence in the cheap tier. |

## Google (Gemini)

Verified via ai.google.dev model + pricing pages, 2026-06-26. Pro models are context-tiered (a higher rate kicks in above 200K input tokens). `-preview` models are NOT stable - do not pin them in production.

| Model | API id | Context | In / Out per 1M | Use for |
|---|---|---|---|---|
| Gemini 2.5 Flash-Lite | `gemini-2.5-flash-lite` | 1M | $0.10 / $0.40 | Cheapest viable AI workhorse: classification, routing, extraction, translation, multimodal, long context. The default cheap-AI tier. |
| Gemini 3.1 Flash-Lite | `gemini-3.1-flash-lite` | 1M | $0.25 / $1.50 | Next-gen low-cost, stable. High-frequency lightweight tasks where 2.5 Flash-Lite is not enough. |
| Gemini 2.5 Flash | `gemini-2.5-flash` | 1M | $0.30 / $2.50 | Mid-tier price-performance workhorse. Multimodal, thinking, tools. |
| Gemini 3.5 Flash | `gemini-3.5-flash` | 1M | $1.50 / $9.00 | Current flagship Flash (launched 2026-05-19). Frontier-level intelligence at Flash speed; agentic + complex coding. |
| Gemini 2.5 Pro | `gemini-2.5-pro` | 1M | $1.25 / $10 (<=200K); $2.50 / $15 (>200K) | Deep reasoning Pro: math, STEM, complex code, multimodal. Stable. |
| Gemini 3 Flash | `gemini-3-flash-preview` | 1M | $0.50 / $3.00 | PREVIEW (not stable). Next-gen Flash. |
| Gemini 3.1 Pro | `gemini-3.1-pro-preview` | 1M | $2.00 / $12 (<=200K); $4.00 / $18 (>200K) | PREVIEW (not stable). Most advanced Gemini 3.x reasoning + multimodal. No free tier. |

## OpenAI (GPT)

Verified via developers.openai.com model + pricing pages, 2026-06-26. GPT-5.5 / GPT-5.4 prompts over 272K input tokens bill at 2x in / 1.5x out for the session. Batch API = 50% off.

| Model | API id | Context | In / Out per 1M | Use for |
|---|---|---|---|---|
| GPT-5.5 | `gpt-5.5` | ~1.05M | $5 / $30 | Frontier flagship; hardest reasoning + agent tasks. |
| GPT-5.5 Pro | `gpt-5.5-pro` | ~1M | $30 / $180 | Maximum compute for the hardest problems. Responses API only. |
| GPT-5.4 | `gpt-5.4` | ~1.05M | $2.50 / $15 | Lower-cost frontier workhorse. |
| GPT-5.4-mini | `gpt-5.4-mini` | 400K | $0.75 / $4.50 | Cheap-but-capable; strong mini for coding + agents. |
| GPT-5.4-nano | `gpt-5.4-nano` | 400K | $0.20 / $1.25 | Ultra-cheap routing / extraction / high-volume backend. |
| GPT-5.3-Codex | `gpt-5.3-codex` | 400K | $1.75 / $14 | Dedicated coding-agent flows (SWE-Bench / Terminal-Bench). |
| GPT-4.1 | `gpt-4.1` | ~1M | $2 / $8 | Long-context, no-reasoning workhorse; lower latency. |
| GPT-4.1-nano | `gpt-4.1-nano` | ~1M | $0.10 / $0.40 | Cheapest OpenAI model; lowest latency, long context. |
| o3 / o4-mini | `o3` / `o4-mini` | 200K | $2 / $8 ; $1.10 / $4.40 | Reasoning models, being superseded by the GPT-5 family. |

## Selection principle

Always bottom-up: start with the cheapest tier that could plausibly do the job (default `gemini-2.5-flash-lite` at $0.10/$0.40 for classify/route/extract; `claude-haiku-4-5` for strict-schema output), eval on 20-50 samples (accuracy + cost-utility), escalate measurably, never preventively. Batch API (~50% off) for anything non-interactive. Cascading (cheap call -> judge confidence -> escalate only the low-confidence cases) beats a routing classifier unless sub-second latency is critical.

## How to prompt these models

- `ai-prompt-guidelines.md` (this folder) - general AI prompting guidance.
- `model-reference-prompting.md` (this folder) - per-model / per-provider prompting reference.

## Sources

- Anthropic: bundled `claude-api` skill (`shared/models.md` - authoritative model IDs, context windows, pricing, limits).
- OpenAI (verified 2026-06-26): `developers.openai.com/api/docs/models`, `developers.openai.com/api/docs/pricing`.
- Google Gemini (verified 2026-06-26): `ai.google.dev/gemini-api/docs/models`, `ai.google.dev/gemini-api/docs/pricing`.

Flag before relying on in a public/production context:
- `gpt-5.5-pro` and `gpt-5.4-nano` model-ID strings appear on the official OpenAI pricing page but were not separately confirmed on a dedicated model page; the `gpt-5.5-pro` snapshot ID is unconfirmed.
- Gemini `-preview` models (`gemini-3-flash-preview`, `gemini-3.1-pro-preview`) are not GA - their IDs and prices will change at stable release.

---
Last verified: 2026-06-26. Auto-update: TODO (Šimon to wire a periodic refresh).
</llm_lineup>
