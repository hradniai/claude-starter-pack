---
type: notes
title: "LLM model lineup (current)"
status: active
summary: "On-demand reference for model selection (not auto-loaded): which model for which job in Claude Code and in automations, with IDs, limits, prices and retirement dates for Anthropic, OpenAI and Google, each sourced and dated 2026-10-05. How to prompt them lives in model-reference-prompting.md."
created: 2026-06-16
updated: 2026-10-05
created_by: claude-starter-pack
client: ~
path: _CONTEXT/llms/model-lineup.md
tags: [note]
version: "1.0.0"
---

<llm_lineup>

# LLM model lineup (current)

> On-demand reference for picking a model. NOT auto-loaded into every session; read it when you choose a model for a Claude Code subagent, a skill or an automation step. Every fact below was read on the vendor's own pages on **2026-10-05** (sources at the end of each section). Lineups change monthly: re-check the linked pages before a production choice, and pin full model IDs in production, because aliases (`opus`, `gemini-flash-latest`, `chat-latest`) move to new models, sometimes with little notice.
>
> Labels: a plain fact is from the cited vendor page. **[UNVERIFIED]** means no primary page confirmed it. **[Judgment]** marks a recommendation that is this document's opinion, built on the cited facts, not a vendor statement.

## Quick picks

### Claude Code: main session, subagents and skills

| Job | Pick (alias) | Why |
|---|---|---|
| Main session, everyday engineering | `opus` = Claude Opus 5.5, default effort `medium` | Claude Code's default model on every plan and provider except Microsoft Foundry, where the default is Sonnet 4.5 [C1]. Anthropic: "If you're unsure which model to use, start with Claude Opus 5.5 for most workloads." [A1] |
| Hardest long-horizon work: root-cause investigations, architecture, multi-hour autonomous runs | `fable` = Claude Fable 5.1 | Anthropic: "Use Claude Fable 5.1 for demanding reasoning and long-horizon agentic work, or when your evals on Claude Opus 5.5 at higher effort still fall short." [A1] Never the default; costs 2.5x Opus 5.5 per token [A2]; on some plans it bills usage credits [C1]; not available under zero data retention [A5]. |
| Implementation, code review and research subagents | `sonnet` = Claude Sonnet 5.5 | "The best combination of speed and intelligence" [A1] at half the Opus 5.5 token price [A2]. |
| Read-only lookups: search, grep-and-summarize, file inventories | `haiku` (the fast Haiku model; Haiku 4.5 is the only current one), or `sonnet` with `effort: low` | Anthropic lists `low` effort for "simpler tasks that need the best speed and lowest costs, such as subagents" [A4]. Haiku 4.5 is the fastest and cheapest Claude [A1]; see its retirement note below. |
| Plan with a strong model, execute with a cheaper one | `opusplan` | Opus in plan mode, Sonnet for execution [C1]. |

How to set it [C1, C2, C3]:
- Subagent file frontmatter: `model: sonnet | opus | haiku | fable | inherit`, or a full ID such as `claude-sonnet-5-5`. Without a `model:` line the subagent runs on `CLAUDE_CODE_SUBAGENT_MODEL` if set, otherwise on the main session's model, which is expensive when the main session runs Fable. Set `model:` on every cheap subagent. [Judgment for the advice]
- `CLAUDE_CODE_SUBAGENT_MODEL` is only a default: a subagent's own `model:` wins, and it does not change the built-in Explore and Plan subagents unless you also set `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` [C3].
- Skills accept `model:` and `effort:` in frontmatter. The model override lasts for the rest of the current turn and is not saved; the session model resumes with your next message [C2].
- Session effort: `/effort` (saves a level per model), `--effort`, or `CLAUDE_CODE_EFFORT_LEVEL`. A top-level `effortLevel` in your user settings file does not apply to Opus 5.5 or newer models; use `/effort` for them. In Claude Code, Opus 5.5 and Sonnet 5.5 default to `medium`, Opus 4.7 to `xhigh`, every other model that supports effort to `high` [C1].
- Alias targets depend on the provider. `sonnet` is Sonnet 5.5 only on the Anthropic API; it is Sonnet 4.6 on Claude Platform on AWS and Sonnet 4.5 on Amazon Bedrock, Google Cloud and Microsoft Foundry. `opus` is Opus 5.5 everywhere except Foundry (Opus 4.6). `fable` is Fable 5.1, except in Claude apps gateway sessions (Fable 5). Pin with `ANTHROPIC_DEFAULT_SONNET_MODEL` / `ANTHROPIC_DEFAULT_OPUS_MODEL` / `ANTHROPIC_DEFAULT_HAIKU_MODEL` / `ANTHROPIC_DEFAULT_FABLE_MODEL`.
- Minimum Claude Code versions: v2.1.284 for Sonnet 5.5, v2.1.280 for Opus 5.5, v2.1.257 for Fable 5.1 (`claude update`).

### Automations and API calls

Prices are USD per 1M input / output tokens, standard tier, as of 2026-10-05. Detail and sources in the provider sections.

| Job | Cheapest sensible start | Step up when evals demand it |
|---|---|---|
| Classify, route, tag, extract (high volume) | GPT-6 Luna $0.10 / $0.50; Gemini 3.1 Flash-Lite $0.25 / $1.50; Gemini 3.5 Flash-Lite $0.30 / $2.50 | Claude Haiku 4.5 $1 / $5; Gemini 3.8 Flash |
| Messy documents, multi-step extraction, agents with tools | Gemini 3.8 Flash $0.75 / $3.75 (intro, until 2026-12-31) | Claude Sonnet 5.5 $2 / $10; GPT-6.1 Sol $2 / $10 |
| Hardest reasoning, long agentic coding | Claude Opus 5.5 $4 / $20 | GPT-6 Astra $10 / $50; Claude Fable 5.1 $10 / $50 |
| Audio and video input | Gemini 3.5 Flash-Lite (one flat rate covers audio) | Gemini 3.8 Flash. Claude reads PDFs (up to 600 pages per request) but takes no audio or video [A6]. |
| Answers grounded in live web search, with citations | A web-search tool on the model you already use: Claude and OpenAI $10 per 1,000 searches; Gemini 3.x on the paid tier 5,000 free searches per month, then $14 per 1,000 | Perplexity Agent API (see `model-reference-prompting.md`) |
| Self-hosted, data stays on your hardware | Qwen3.8-27B (Apache 2.0) | See `model-reference-prompting.md` |

The table is a starting point [Judgment]: cheapest-first ordering, not a quality ranking. Token prices are not directly comparable across vendors, because each family tokenizes differently (Claude 4.7 and later produce about 30 % more tokens for the same text than earlier Claude models [A2]). Compare cost per finished task on your own data.

## Selection principle

Bottom-up: start with the cheapest tier that could plausibly do the job, run it on 20-50 real samples (accuracy plus cost per task), and escalate only when the measured gap justifies it, never preventively. Use the Batch API (50 % off at all three providers) for anything nobody is waiting for. Cascading (cheap call, then a confidence check, then escalate only the low-confidence cases) usually beats a routing classifier unless sub-second latency matters. Effort or reasoning level is the second cost lever after the model itself: lower it first when a model is too slow or too expensive. [Judgment]

## Anthropic (Claude)

As of 2026-10-05. Current lineup [A1]:

| Model | API ID | Context / max output | In / Out per 1M (cache read) | Thinking, default effort | Knowledge cutoff | Retirement not before | Use for |
|---|---|---|---|---|---|---|---|
| Claude Fable 5.1 | `claude-fable-5-1` | 1M / 128K | $10 / $50 ($0.25) | Adaptive, always on; `high` | Jun 2026 | 2027-09-01 | Hardest reasoning and long-horizon agentic work. Requires 30-day data retention, so not available under ZDR unless Anthropic authorizes it [A5]. |
| Claude Opus 5.5 | `claude-opus-5-5` | 1M / 128K | $4 / $20 ($0.20) | Adaptive, always on; `medium` | Jun 2026 | 2027-09-22 | Default for most work: long-running agentic coding and knowledge work. Cheaper per token than every earlier Opus [A2]. |
| Claude Sonnet 5.5 | `claude-sonnet-5-5` | 1M / 128K | $2 / $10 ($0.20) | Adaptive, on by default; `high` on the API (`medium` in Claude Code) | Jun 2026 | 2027-09-28 | Speed plus intelligence: coding, agents, production workloads. |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` (alias `claude-haiku-4-5`) | 200K / 64K | $1 / $5 ($0.10) | Extended thinking (manual budget); no effort parameter | Feb 2025 | 2026-10-15 | Fastest and cheapest: routing, classification, simple subagents. |

Notes [A1-A5]:
- **Haiku 4.5 retirement floor is 2026-10-15**, ten days after this check. The deprecations page still lists it as Active with no deprecation, and Anthropic promises at least 60 days' notice before retiring a publicly released model [A3], so it stays usable until at least early December 2026 [Judgment, derived from those two facts]. Anthropic has no newer Haiku; check [A3] before you build on it.
- Every current model takes text and image input and returns text [A1].
- Batch API: 50 % off input and output. Cache writes cost 1.25x input (5-minute) or 2x (1-hour); cache reads cost 0.1x input, except 0.05x on Opus 5.5 and 0.025x on Fable 5.1 [A2].
- 1M context is billed at the standard per-token rate on Claude 4.6 and later, with no long-context premium [A2].
- Fast mode (research preview, Claude API only, not with Batch): Opus 5.5 $8 / $40; Opus 5 and Opus 4.8 $10 / $50 [A2].
- US-only inference (`inference_geo: "us"`) multiplies every token price by 1.1 on Claude 4.6 and later [A2].
- Server tools: web search $10 per 1,000 searches plus the result tokens; web fetch has no fee beyond tokens [A2].
- Claude Mythos 5.1 / Mythos 5 share Fable's specs and price but are invitation-only (Project Glasswing) [A2].

Older models still available (legacy) [A1, A2, A3]: Fable 5 ($10 / $50), Opus 5, 4.8, 4.7, 4.6 and 4.5 ($5 / $25 each), Sonnet 5 ($2 / $10), Sonnet 4.6 ($3 / $15). **Deprecated:** Sonnet 4.5 (`claude-sonnet-4-5-20250929`) retires **2026-11-30**, replacement `claude-sonnet-5-5`. **Retired** (requests fail on the Claude API): Opus 4.1 (2026-08-05), Opus 4 and Sonnet 4 (2026-06-15), Haiku 3 (2026-04-20), Haiku 3.5 and Sonnet 3.7 (2026-02-19). Bedrock and Google Cloud set their own retirement dates.

Sources, read 2026-10-05:
- [A1] Models overview: https://platform.claude.com/docs/en/models/overview
- [A2] Pricing: https://platform.claude.com/docs/en/about-claude/pricing
- [A3] Model deprecations: https://platform.claude.com/docs/en/about-claude/model-deprecations
- [A4] Effort: https://platform.claude.com/docs/en/build-with-claude/effort
- [A5] API and data retention: https://platform.claude.com/docs/en/manage-claude/api-and-data-retention
- [A6] PDF support: https://platform.claude.com/docs/en/build-with-claude/pdf-support
- [C1] Claude Code model configuration: https://code.claude.com/docs/en/model-config
- [C2] Claude Code skills: https://code.claude.com/docs/en/skills
- [C3] Claude Code subagents: https://code.claude.com/docs/en/sub-agents

## OpenAI (GPT)

As of 2026-10-05. OpenAI's own starting advice: "If you're not sure where to start, use GPT-6 Astra, our flagship model for complex reasoning and coding. Choose GPT-6.1 Sol to balance intelligence and cost, or GPT-6 Luna for cost-sensitive, high-volume workloads." [O3]

| Model | API ID | Context / max output | In / Out per 1M (cached input) | Reasoning effort (default) | Knowledge cutoff | Status | Use for |
|---|---|---|---|---|---|---|---|
| GPT-6 Astra | `gpt-6-astra` | 1.05M (922K max input) / 128K | $10 / $50 ($1.00) | low, medium, high, xhigh, max; `none` returns 400; default not stated [UNVERIFIED] | 2026-04-30 | Current, released 2026-09-03 | "Most capable model for the most demanding work." Tool calling needs the Responses API. |
| GPT-6.1 Sol | `gpt-6.1-sol` | 1.05M (922K) / 128K | $2 / $10 ($0.10, i.e. 5 % of input) | low, medium (default), high, xhigh, max; no `none` or `minimal` | 2026-04-30 | Current, released 2026-09-29 | "Near-Astra performance for complex work at a lower cost." Tool calling needs the Responses API. |
| GPT-6 Luna | `gpt-6-luna` | 1.05M (922K) / 128K | $0.10 / $0.50 ($0.01) | none, low, medium (default), high, xhigh, max | 2026-05-18 | Current, released 2026-09-22 | "Most efficient model for focused, high-volume tasks." |
| GPT-5.6 Sol / Terra / Luna | `gpt-5.6-sol` (alias `gpt-5.6`), `gpt-5.6-terra`, `gpt-5.6-luna` | 1.05M (922K) / 128K | Sol $4 / $20 (promotional, "at least through November 21, 2026"); Terra $2 / $12; Luna $0.20 / $1.20 | none, low, medium (default), high, xhigh, max | 2026-02-16 | Previous generation, available | Existing pipelines; also the named replacement for many shutdowns below. |
| GPT-5.5 | `gpt-5.5` | 1.05M / 128K | $5 / $30 ($0.50) | none, low, medium (default), high, xhigh | 2025-12-01 | Available on the API (it leaves ChatGPT and Codex on 2026-10-14, which does not affect the API) | Existing pipelines only. |
| GPT-5.4 mini | `gpt-5.4-mini` | 400K (272K max input) / 128K | $0.75 / $4.50 ($0.075) | none (default), low, medium, high, xhigh | 2025-08-31 | Available | Older cheap tier; GPT-6 Luna is cheaper. |
| GPT-4.1 / GPT-4.1 mini | `gpt-4.1`, `gpt-4.1-mini` | ~1.05M / 32K | $2 / $8; $0.40 / $1.60 | None (non-reasoning) | 2024-06-01 | Available, not on the deprecations list | Low-latency, non-reasoning long-context jobs. |

Notes [O1-O5]:
- GPT-6 Sol (`gpt-6-sol`, $2 / $10) is still available; OpenAI points to GPT-6.1 Sol as "the newer Sol model", at the same list price with half the cached-input price. It is not a drop-in swap: 6.1 Sol drops effort `none` and Chat Completions tool calling, and `gpt-6-sol` remains the named replacement in several deprecation notices below.
- Pro tiers (`gpt-5.5-pro`, `gpt-5.4-pro`, $30 / $180, Responses API only) still exist; on GPT-5.6 and GPT-6, `reasoning.mode: "pro"` gives the same idea at the model's standard token rates [O4].
- Batch and Flex: 50 % of standard. On the models with a long-context price tier (the full-size models from GPT-5.4 on, not GPT-4.1 or the 400K-context minis), prompts over 272K input tokens bill the **whole request** at 2x input and cache rates and 1.5x output. Cached input is 10 % of input on most current models (5 % on GPT-6.1 Sol). GPT-5.6 and all GPT-6 models add a cache-write charge of 1.25x input; earlier models do not [O1, O5].
- Fast mode (`service_tier: "fast"`, formerly Priority): 2x standard on GPT-6 and GPT-5.6; other models use other multipliers (GPT-5.5 is 2.5x). Ultrafast (`service_tier: "ultrafast"`; broadly available on GPT-6 Astra, preview on GPT-5.6 Sol) costs $60 / $300 per 1M on Astra, 6x standard by arithmetic [O1, O6].
- Regional data-residency processing adds 10 % on models released on or after 2026-03-05 [O1].

Deprecations a model picker can trip on [O2]:
- Shut down **2026-10-23**: `gpt-4.1-nano` (replacement `gpt-5.6-luna`), `o4-mini` (`gpt-5.6-terra`), `o3-mini`, `o1`, `gpt-4`, `gpt-4-turbo`, `gpt-4o-2024-05-13` (`gpt-5.6-sol`), `gpt-3.5-turbo` (`gpt-5.6-terra`).
- Shut down **2026-12-11**: the `gpt-5`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5-pro`, `o3` and `o3-pro` snapshots (replacements `gpt-5.6-sol`, `-terra`, `-luna`, or `gpt-5.6-sol` in pro mode).
- Shut down **2027-04-01** (announced 2026-10-01): `gpt-5.4-nano` (`gpt-6-luna`), `gpt-5.3-codex` and `gpt-5.1` (`gpt-6-sol`).
- Already shut down on 2026-07-23: the `gpt-5.1-codex` / `gpt-5.2-codex` family, `o3-deep-research`, `o4-mini-deep-research`, `computer-use-preview`. `gpt-5.3-codex-spark` was retired from the Codex apps on 2026-09-14 [O3].

Sources, read 2026-10-05:
- [O1] Pricing: https://developers.openai.com/api/docs/pricing
- [O2] Deprecations: https://developers.openai.com/api/docs/deprecations
- [O3] Models catalog and model pages: https://developers.openai.com/api/docs/models (per model: https://developers.openai.com/api/docs/models/gpt-6.1-sol and siblings); Codex models: https://learn.chatgpt.com/docs/models
- [O4] Reasoning guide: https://developers.openai.com/api/docs/guides/reasoning
- [O5] Prompt caching: https://developers.openai.com/api/docs/guides/prompt-caching ; changelog: https://developers.openai.com/api/docs/changelog
- [O6] Ultrafast mode: https://developers.openai.com/api/docs/guides/ultrafast-mode

## Google (Gemini)

As of 2026-10-05. Every model below takes text, image, video, audio and PDF input, with 1,048,576 input and 65,536 output tokens [G1].

| Model | API ID | Status | In / Out per 1M | Thinking levels (default) | Use for |
|---|---|---|---|---|---|
| Gemini 3.8 Flash | `gemini-3.8-flash` | GA 2026-09-02; Google's "most intelligent Flash model" | $0.75 / $3.75 until 2026-12-31, then $1.50 / $7.50 | low, medium (default), high; `minimal` returns an error | Agents, coding, enterprise workflows. Uses more tokens on long tasks by design; lower the thinking level for everyday work [G3]. |
| Gemini 3.7 Flash | `gemini-3.7-flash` | GA 2026-08-13; previous generation | Same schedule as 3.8 Flash | low, medium (default), high; `minimal` returns an error | Fallback if 3.8 Flash's token use is too high [G3]. |
| Gemini 3.6 Flash | `gemini-3.6-flash` | GA 2026-07-21; previous generation | Same schedule as 3.8 Flash | minimal, low, medium (default), high | Existing pipelines. |
| Gemini 3.5 Flash | `gemini-3.5-flash` | GA 2026-05-19; Google calls it legacy | $1.50 / $9.00 | minimal, low, medium (default), high | Existing pipelines; more expensive than 3.8 Flash. |
| Gemini 3.5 Flash-Lite | `gemini-3.5-flash-lite` | GA 2026-07-21 | $0.30 / $2.50, one flat input rate including audio | minimal (default), low, medium, high | Cheapest audio input; high-volume multimodal. (3.1 Flash-Lite is cheaper for text, image and video.) |
| Gemini 3.1 Flash-Lite | `gemini-3.1-flash-lite` | GA 2026-05-07; earliest shutdown **2027-05-07** (replacement 3.5 Flash-Lite) | $0.25 / $1.50 (audio input $0.50) | minimal (default), low, medium, high | Cheapest text tier, until its shutdown. |
| Gemini 3.1 Pro | `gemini-3.1-pro-preview` | **Preview** (since 2026-02-19), no GA date; paid only | $2 / $12 up to 200K input; $4 / $18 above | low, medium, high (default) | Hardest Gemini reasoning. Preview: IDs and prices can change. |
| Gemini 3 Flash | `gemini-3-flash-preview` | Preview; Google names 3.6 Flash as its replacement | $0.50 / $3.00 (audio input $1.00) | minimal, low, medium, high (default) | Avoid for new work. |

Notes [G1-G8]:
- Thinking levels and defaults per model: [G3]; the 3.1 Flash-Lite default comes from [G7].
- No Gemini Pro newer than 3.1 Pro exists on the API; Google's model page shows "3.5 Pro coming soon" without a date [G6].
- **Gemini 4 Argon** was announced on 2026-09-30 for "trusted cyber defenders" only, with broader paid-API access promised later; it has no API model ID in the docs yet, so it is not usable [G6].
- Older 2.x generation: 2.0 Flash and Flash-Lite shut down on 2026-06-01; 2.5 is still served but limited to users who have actively used it, with no announced shutdown [G2]. New projects should start on 3.x.
- `gemini-flash-latest` was last documented as pointing at `gemini-3.5-flash` (2026-05-19); its current target is [UNVERIFIED]. Pin explicit IDs [G4].
- Batch: 50 % of standard. Flex: 50 % off with minutes of latency. Priority: 75-100 % above standard [G5].
- Context caching: reads cost 10 % of input. Explicit caching, where storage is billed ($1.00 per 1M tokens per hour on Flash tiers, $0.50 on 3.8/3.7/3.6 Flash until 2026-12-31, $4.50 on 3.1 Pro), exists only on the generateContent API; the Interactions API supports implicit caching only. Minimum cacheable prompt: 4,096 tokens on 3.8, 3.7, 3.6 and 3.5 Flash and 3.1 Pro [G5]. On a long-lived explicit cache that is read rarely, storage rather than reads dominates the bill [Judgment].
- Grounding with Google Search on 3.x (paid tier only): 5,000 free search queries per month shared across all 3.x models, then $14 per 1,000 queries; billed per query the model runs, not per prompt [G5].
- Thinking tokens bill as output [G5].

Sources, read 2026-10-05:
- [G1] Models: https://ai.google.dev/gemini-api/docs/models (per model: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash and siblings)
- [G2] Deprecations: https://ai.google.dev/gemini-api/docs/deprecations
- [G3] What's new in Gemini 3.8 Flash: https://ai.google.dev/gemini-api/docs/latest-model ; thinking: https://ai.google.dev/gemini-api/docs/thinking
- [G4] Changelog: https://ai.google.dev/gemini-api/docs/changelog
- [G5] Pricing: https://ai.google.dev/gemini-api/docs/pricing ; caching: https://ai.google.dev/gemini-api/docs/caching ; Google Search grounding: https://ai.google.dev/gemini-api/docs/google-search ; Flex: https://ai.google.dev/gemini-api/docs/flex-inference ; Priority: https://ai.google.dev/gemini-api/docs/priority-inference
- [G6] Gemini 4 Argon announcement: https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-4-argon/ ; Gemini Pro page: https://deepmind.google/models/gemini/pro/
- [G7] What's new in Gemini 3.5 (baseline guide for 3.x): https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.5
- [G8] Gemini 3 developer guide (marked deprecated by Google, still the only page stating the 3.1 models' cutoff): https://ai.google.dev/gemini-api/docs/gemini-3

## Other providers

Perplexity (search-grounded answers) and Qwen (open weights you host yourself) are covered, with status and sources, in `model-reference-prompting.md`. In short: Perplexity moved Sonar Chat Completions onto its Agent API in July 2026 and ended Sonar support on 2026-09-27, so new work goes to the Agent API; the newest open-weight Qwen generation is Qwen3.8 (August 2026).

## Not verified on a primary page (as of 2026-10-05)

- Default `reasoning.effort` of `gpt-6-astra` (no OpenAI page states it).
- Current target of the `gemini-flash-latest` alias, and knowledge cutoffs of Gemini 3.6, 3.7, 3.8 Flash and 3.5 Flash-Lite. (3.5 Flash: January 2025 [G7]; the 3.1 models: January 2025, stated only on Google's deprecated Gemini 3 guide [G8].)
- Gemini 4 Argon's API model ID, context window and availability date (the announcement gives only prices and a 1M-token output limit).
- The quality ordering implied by the quick-pick tables: those are [Judgment] from vendor positioning and prices, not from a benchmark run for this document.

---
Last verified: 2026-10-05 (Anthropic, OpenAI, Google).
</llm_lineup>
