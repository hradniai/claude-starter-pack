---
type: notes
title: "Model Reference: Per-Model Prompting, Claude Code Skills & Cowork Plugins"
status: approved
summary: "How each model wants to be prompted (per-provider best practices, use-case frameworks, JSON, anti-patterns) plus how to build Claude Code Skills and Cowork Plugins. Merged + research-refreshed June 2026."
created: 2026-05-13 00:00
updated: 2026-06-26 00:00
owner: Šimon Hradní
client: ~
path: _CONTEXT/llms/model-reference-prompting.md
tags: [note]
version: "1.1.0"
release: latest
---

# Model Reference: Per-Model Prompting, Claude Code Skills & Cowork Plugins

> How each model wants to be prompted (per-provider best practices, use-case frameworks, JSON output, anti-patterns) plus how to build Skills and Plugins. Refreshed June 2026. Claude/Anthropic specifics here are taken from the authoritative `claude-api` reference, not from memory; OpenAI and Gemini specifics are refreshed from each provider's current official docs.

---

## Core principles (apply to every provider)

### Optimal, not minimal

**Quality over quantity. Add what's needed, skip what's not.** This is the single rule that governs every prompt regardless of model.

**Add more when:**
- Examples cover significantly different variants (not the same pattern with different data).
- An explanation prevents a common mistake the model actually makes.
- Context demonstrably changes output quality.
- Error handling covers a failure that will actually occur.

**Skip:**
- Redundant examples (same pattern, different data).
- Obvious explanations the model already follows.
- Instructions that do not change the output.
- Verbose framing that could be one sentence.

**Golden rule:** if removing it makes the prompt worse, keep it; if not, cut it. The same idea drives the recent Claude models, which now do natively what older prompts scaffolded by hand (see "Re-baseline old prompts" below) - so the optimal prompt for a 2026 frontier model is shorter than the one you wrote for its predecessor.

### Prompt language vs output language

**The prompt body is always written in English. The output language is a constraint you state INSIDE that English prompt - it is never a reason to switch the prompt's language.** These are two independent decisions:

- **Prompt language = English, always.** Every instruction, system prompt, agent rule, classifier prompt, and inline f-string scaffold handed to an LLM is English. Reason: token cost (English tokenizes shorter than Czech) and consistency with the rest of the prompt tooling. This holds even when the deliverable must be Czech.
- **Output language / tone = stated explicitly in the prompt.** If the result must be Czech (or any non-English), add one line: `"Write the output in native Czech, conversational tone"` (or commercial, formal, whatever fits). The model reads an English instruction and produces Czech.

**The trap:** conflating "the user-facing output must be Czech" with "the prompt must be Czech." Writing the prompt in the output language is the mistake - it costs tokens and buys nothing.

**Check both surfaces:** the named prompt / template body AND any inline f-string wrappers in code that get concatenated into the message. Both are prompts; both cost tokens; both must be English.

**Output-format markers stay verbatim.** Where a parser keys on a literal marker the model must emit (`### A`, `Title:`, a JSON key), keep that marker exactly - it is a machine contract, not prose, and is independent of prompt / output language.

---

## Model Comparison (June 2026)

### OpenAI (Apr–May 2026)

| | GPT-5.5 | GPT-5.5 Pro | GPT-5.5 Instant | GPT-4.1 nano | o3 |
|---|---|---|---|---|---|
| **API ID** | `gpt-5.5` | `gpt-5.5-pro` | `chat-latest` | `gpt-4.1-nano-2025-04-14` | `o3` |
| **Context** | 1.05M | 1.05M | ~272K | 1M | 200K |
| **Max output** | 128K | 128K | 32K | 32K | 100K |
| **Reasoning** | Built-in (effort: none/low/med/high/`xhigh`, default `medium`) | Built-in, higher cap | Mid-stream self-correction, lighter reasoning | No | Built-in (low/med/high) |
| **Structured output** | Native | Native | Native | Native | Native |
| **Tool calling** | Native (Responses API recommended) | Native | Native | Native | Native |
| **Prompt format** | Outcome-first, minimal scaffolding | Same | Conversational | Markdown headers | Developer messages |
| **Pricing** | $5 / $30 per MTok (≤272K input); >272K: 2x in / 1.5x out. Cached input $0.50/MTok. | $30 / $180 per MTok | ChatGPT default, not separately metered | $0.10 / $0.40 per MTok | Standard reasoning pricing |
| **Best for** | New flagship: agents, large tool surfaces, multi-step reasoning, coding | Hardest reasoning, long agentic loops | ChatGPT default, low-latency chat, 52 % fewer hallucinations vs 5.3 Instant | Cheapest OpenAI: routing, classification, autocomplete, extraction | Legacy reasoning (transition to GPT-5.5) |
| **Released** | 2026-04-24 | 2026-04-24 | 2026-05-05 | 2025-04 | 2025 |

**Lineup clarifications (June 2026 research pass, developers.openai.com):**
- **"GPT-5.5 Instant" is a ChatGPT consumer product name, NOT a separate API model.** It is the ChatGPT default (replaced GPT-5.3 Instant on 2026-05-05); the ChatGPT-tuned alias is `chat-latest`. The API flagship is simply `gpt-5.5` (dated snapshot `gpt-5.5-2026-04-23`).
- **`gpt-5.5-pro` is a real API model** at $30 / $180 per MTok (1.05M ctx, 128K out, released 2026-04-24) - the deep-reasoning / precision tier.
- **A cheaper GPT-5.4 family also exists** below 5.5: `gpt-5.4` ($2.50 / $15), `gpt-5.4-mini` ($0.75 / $4.50), `gpt-5.4-nano` ($0.20 / $1.25). For the cheapest classification / routing tier, `gpt-5.4-nano` is the going-forward replacement for `gpt-4.1-nano`.
- **No `gpt-5.6`, `gpt-6`, or `o5` family** announced as of 2026-06-26 - reasoning is a mode of GPT-5.x ("Thinking" / reasoning effort), not a separate brand.

**Status / deprecation of older OpenAI models (developers.openai.com/api/docs/deprecations):** GPT-4o, GPT-4.1, GPT-4.1 mini, o3, and o4-mini were **retired from ChatGPT 2026-02-13**; API access stays live with confirmed sunset dates: **`gpt-4.1-nano` API deprecates 2026-10-23** (→ `gpt-5.4-nano`), **`o3-mini` / `o4-mini` deprecate 2026-10-23** (→ `gpt-5.4-mini` / `gpt-5.5`), **`o3` (snapshot `o3-2025-04-16`) deprecates 2026-12-11** (→ `gpt-5.5`). Base `gpt-4.1` and `gpt-4.1-mini` have **no confirmed API sunset date yet** (still live; flag for re-check). Verify exact ID strings and dates on developers.openai.com before a public release.

### Anthropic / Claude (current as of June 2026)

These rows are taken from the authoritative `claude-api` reference (cached 2026-06-04), not stated from memory. The Opus tier moved on twice since the May 2026 revision: **Opus 4.8 is now the current/default Opus** (4.7 is previous-gen), and **Claude Fable 5 is the new most-capable widely released model**, sitting above the Opus family.

| | Claude Fable 5 | Claude Opus 4.8 | Claude Opus 4.7 | Claude Sonnet 4.6 | Claude Haiku 4.5 |
|---|---|---|---|---|---|
| **API ID** | `claude-fable-5` | `claude-opus-4-8` | `claude-opus-4-7` | `claude-sonnet-4-6` | `claude-haiku-4-5` |
| **Context** | 1M (default = max) | 1M | 1M | 1M | 200K |
| **Max output** | 128K | 128K | 128K | 64K | 64K |
| **Reasoning** | Adaptive thinking ALWAYS on (omit the param; `{type:"disabled"}` 400s) | Adaptive thinking only (effort: low→`xhigh`→`max`), default OFF | Adaptive thinking only (effort: low→`xhigh`→`max`), default OFF | Adaptive thinking (effort: low→`max`) | None (no extended thinking, no effort) |
| **Sampling** | `temperature`/`top_p`/`top_k` → 400 - omit | `temperature`/`top_p`/`top_k` → 400 - omit | `temperature`/`top_p`/`top_k` → 400 - omit | Standard (one of temperature OR top_p) | Standard |
| **Structured output** | Native (`output_config.format`) | Native | Native | Native | Native |
| **Tool calling** | Native | Native | Native | Native | Native |
| **Prompt format** | XML tags | XML tags | XML tags | XML tags | XML tags |
| **Pricing** | $10 / $50 per MTok | $5 / $25 per MTok | $5 / $25 per MTok | $3 / $15 per MTok | $1 / $5 per MTok |
| **Best for** | The hardest reasoning + longest-horizon autonomous agentic work (above Opus tier) | Current default Opus: highly autonomous long-horizon agentic work, knowledge work, memory; clearer/warmer writing | Previous-gen Opus, still fully supported | Best speed / intelligence balance; agentic workflows, coding, everyday complex tasks (best value) | Real-time, high-volume, cost-sensitive |

**Notes (authoritative specifics):**
- **Claude Fable 5** is the most capable widely released model. Thinking is always on - omit the `thinking` param; an explicit `{type:"disabled"}` returns 400. The raw chain of thought is never returned (you get summaries via `display:"summarized"`). No assistant prefill. Safety classifiers may return `stop_reason:"refusal"` (HTTP 200) - new `claude-fable-5` code should opt into the server-side `fallbacks` parameter by default. **Requires 30-day data retention - not available under zero data retention (ZDR orgs get a 400 on every request).** Same tokenizer as Opus 4.8.
- **Claude Mythos 5** (`claude-mythos-5`) has the same capabilities, pricing, and API behavior as Fable 5 but is available only through Project Glasswing; it succeeds the invitation-only Claude Mythos Preview (`claude-mythos-preview`). Use `claude-fable-5` unless the org participates in Project Glasswing. This replaces the old "Mythos Preview is the internal frontier" note: the public frontier is now Fable 5.
- **Opus 4.8 ($5/$25, 1M ctx, 128K out)** keeps the same request surface as 4.7 (no new breaking changes) - a 4.7→4.8 move is a model-ID swap plus prompt re-tuning. New: mid-conversation system messages (Opus 4.8 only - append `{"role":"system",...}` to `messages[]` without invalidating the prompt cache).
- **Opus 4.6** ($5/$25, 1M ctx, 128K out) is still supported; adaptive thinking recommended (`budget_tokens` deprecated, transitional escape hatch only).
- **Effort** (`output_config.effort`): GA, default `high`. `low/medium/high/max` on Opus 4.5+ and Sonnet 4.6; `xhigh` (between high and max) added on Opus 4.7 and present on 4.8 + Fable 5. Errors on Sonnet 4.5 / Haiku 4.5.
- **Thinking display** defaults to `"omitted"` on Fable 5 / Mythos 5 / Opus 4.8 / 4.7 (a silent change from 4.6). Set `thinking:{type:"adaptive", display:"summarized"}` if you surface reasoning to users, or the default looks like a long pause.
- **Prefill** (last-assistant-turn) returns 400 on Fable 5, Opus 4.6 / 4.7 / 4.8, and Sonnet 4.6 - use `output_config.format` (structured outputs) instead.
- **Fast Mode**: Opus 4.8 is the durable fast-capable tier; Opus 4.6 and 4.7 fast mode are deprecated.

**Aliases & retirement:** the bare `opus` alias resolves to the current Opus (4.8); on Bedrock / Vertex / Foundry specify the full ID. Sonnet 4 + Opus 4 (`*-20250514`) reached retirement 2026-06-15 (now past). `claude-3-haiku` retired 2026-04-19. `claude-opus-4-1` is deprecated and retires 2026-08-05 → migrate to `claude-opus-4-8`. Opus 4.5 and Sonnet 4.5 remain active. (Verify exact dates via the `claude-api` migration guide before quoting them to a client.)

### Google Gemini (Nov 2025 – May 2026)

| | Gemini 3.1 Pro | Gemini 3.5 Flash | Gemini 3 Flash | Gemini 3.1 Flash-Lite |
|---|---|---|---|---|
| **API ID** | `gemini-3.1-pro-preview` | `gemini-3.5-flash` (alias `gemini-flash-latest`) | `gemini-3-flash-preview` | `gemini-3.1-flash-lite` |
| **Context** | 1M | 1M | 1M | 1M |
| **Max output** | 65K | 65K | 64K | 64K |
| **Reasoning** | `thinking_level` low/med/high (default high) | `thinking_level` low/med/high (default medium) | `thinking_level` minimal/low/med/high (default high) | `thinking_level` minimal/low/med/high (default minimal) |
| **Structured output** | Native (`responseSchema` / Interactions `response_format`) | Native | Native | Native |
| **Tool calling** | Native (`functionDeclarations`; modes auto/any/none/`validated`) | Native | Native | Native |
| **Prompt format** | Markdown / plain text | Markdown / plain text | Markdown / plain text | Markdown / plain text |
| **Pricing** | ≤200K in: $2 / $12. >200K: $4 / $18. Cached $0.20/MTok | $1.50 / $9.00 per MTok | $0.50 / $3 (audio in $1) | $0.25 / $1.50 per MTok |
| **Best for** | Highest Gemini intelligence; complex reasoning, multimodal, agentic coding | Frontier agentic + coding at Flash speed/price; the `gemini-flash-latest` model | Pro-grade reasoning at Flash speed; complex multimodal understanding | High-volume, translation, moderation, cheapest Gemini |
| **Status** | **Still Preview** as of June 2026 (no GA). 1M ctx confirmed on the official model card; 2M claims are third-party, NOT official. A `-customtools` variant exists for built-in-bash workflows. | **GA 2026-05-19.** Free tier (rate-limited). | Preview. Free tier. | **GA 2026-05-07.** 340 tok/s, 2.5x TTFT vs 2.5 Flash. Free tier with reduced quota. |

**Free tier change (2026-04-01):** Pro-tier models (3.1 Pro, 3 Pro, 2.5 Pro) are paid-only - no free tier. The Flash tiers (3.5 Flash, 3 Flash, 3.1 Flash-Lite) retain free tier with reduced daily quotas.

**Deprecated:** the Gemini 2.0 Flash family (`gemini-2.0-flash*`, `-lite`) was shut down 2026-06-01.

**Deep Think:** a specialized reasoning mode (latest: Gemini 3.1 Deep Think, built on 3.1 Pro), NOT a separate model ID. API access is early-access / application-based only - no broadly open API, no published pricing. The Interactions API can offload it to a background process via `background: true`. (Gemini lineup refreshed from the June 2026 research pass against ai.google.dev / Vertex AI docs; a couple of items still need human verification before a public release - see the per-provider Gemini section.)

### Perplexity Sonar (search-augmented generation)

A different category from the models above: search-augmented generation (RAG), not pure generation. The model retrieves live web sources automatically and answers with citations.

| Model | Use for | Notes |
|-------|---------|-------|
| `sonar` | Quick factual lookups + summarization | Lightweight |
| `sonar-pro` | Complex queries | 200K context, $3 / $15 per MTok, 2x citations vs base |
| `sonar-reasoning-pro` | Chain-of-thought reasoning with citations | 128K context, $2 / $8 per MTok |
| `sonar-deep-research` | Exhaustive multi-source synthesis (async; results stored ~7 days) | $2 / $8 per MTok + $3/M reasoning tokens + $5/1K search queries |

Use Sonar when the answer depends on current information or must be source-grounded with citations. Do NOT use it for extraction from known documents, deterministic classification, or anything where a hallucination is unacceptable. The old `sonar-reasoning` ID (without `-pro`) is retired - use `sonar-reasoning-pro`. (Model IDs + pricing verified in the June 2026 research pass against docs.perplexity.ai.)

### Qwen 3.5 / 3.6 (self-hosted, Apache 2.0, Feb–Apr 2026)

Architecture: Hybrid MoE (Gated DeltaNet + sparse MoE). Total params ≠ active params. Native multimodal (early fusion). 201 languages.

**Qwen 3.6 successors (Apr 2026, Apache 2.0):**

| | Qwen3.6-27B | Qwen3.6-35B-A3B |
|---|---|---|
| **Total / Active** | 27B (dense) | 35B / 3B (MoE) |
| **Context** | 262K native (extendable to 1.01M) | Same |
| **Released** | 2026-04-22 | 2026-04-16 |
| **Focus** | Stability + agentic coding (frontend, repo-level reasoning). New "Thinking Preservation" option retains reasoning across turns. | Same |
| **vLLM parsers** | `--tool-call-parser qwen3_coder --reasoning-parser qwen3` (requires vLLM ≥ 0.19.0) | Same |

Proprietary 3.6 tier (Alibaba Cloud only, not self-hostable): Qwen3.5-Omni, Qwen3.6-Plus.

**Flagship + Medium (Feb 2026):**

| | 397B-A17B (Plus) | 122B-A10B | 35B-A3B (Flash) | 27B |
|---|---|---|---|---|
| **Total / Active** | 397B / 17B | 122B / 10B | 35B / 3B | 27B (dense) |
| **Context** | 262K (1M hosted) | 262K | 262K (1M hosted Flash) | 262K |
| **Tool calling** | Hermes/qwen3_coder | Best BFCL-V4: 72.2 (beats GPT-5 mini) | Same | Same |
| **Best for** | Frontier self-hosted, multimodal | Agentic, tool use, production | Production API (Flash = hosted version) | Balanced medium model |

**Small (Mar 2026):**

| | 9B | 4B | 2B | 0.8B |
|---|---|---|---|---|
| **Type** | Dense | Dense, native multimodal | Dense | Dense |
| **Context** | 262K | 262K | 262K | 262K |
| **Tool calling** | Yes | Yes | Limited | Limited |
| **Best for** | Strong reasoning (matches 120B+ models on GPQA) | Lightweight multimodal agents, UI navigation | Edge, mobile, iPhone | Micro-tasks, autocomplete |

**All Qwen 3.5 / 3.6 models share:**
- Thinking mode: `<think>` blocks, `/think` and `/no_think` per-turn control
- Structured output via vLLM guided decoding (`guided_json`, `guided_choice`, `guided_regex`)
- Temperature: thinking `0.6 / top_p=0.95 / top_k=20`, non-thinking `0.7 / 0.8 / 20`
- Never greedy decoding with thinking mode
- vLLM: `--enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3`
- 0.8B and 2B default to non-thinking mode; 4B+ default to thinking mode

---

## Per-Model Prompting Guide

### OpenAI GPT-5.5 / 5.5 Pro (Apr 2026)

**Prompt structure**: Outcome-first. Describe what good looks like, success criteria, evidence rules, output shape. Avoid step-by-step process instructions unless the path matters.

```markdown
# Goal
Decide whether the supplied invoice should be auto-approved.

# Success criteria
- Approve only if total ≤ budget AND vendor is on the approved list.
- If any required field is missing or ambiguous, return REVIEW with the reason.

# Evidence
Cite the exact field values you used in your decision.

# Output
JSON: { "decision": "APPROVE | REVIEW | REJECT", "reasoning": "...", "fields_used": {...} }
```

**Tips:**
- **Do NOT** treat as a drop-in replacement for older models - re-baseline from scratch. Official guidance: "start with the smallest prompt that preserves the product contract, then tune reasoning effort, verbosity, tool descriptions, and output format against representative examples."
- Remove scaffolding like "think step by step", "double-check", "be thorough" - the model does this natively.
- `reasoning.effort`: `none / low / medium (default) / high / xhigh`. Start `medium`; push to `high`/`xhigh` for hard tasks. Caveat (OpenAI): higher effort is NOT automatically better - at high effort with conflicting instructions or open-ended tool access it can overthink and regress. Treat effort as a last-mile tuning knob, not the primary quality lever. (Some models support only a subset; check the model page before using `none` or `xhigh`.)
- `text.verbosity`: three levels - `low / medium (default) / high`. `low` is the better starting point for concise production output; `high` produces comprehensive output with explanations. Per-context overrides also respond to natural-language verbosity instructions in the prompt.
- **Use the Responses API**, not Chat Completions. Official benchmark: switching to the Responses API and passing `previous_response_id` lifted Tau-Bench Retail from 73.9% → 78.2% on its own (reasoning traces persist across turns, saving CoT tokens).
- For long-running agent tasks: emit a brief user-visible status update before tool calls (now an officially named technique - a "preamble" that acknowledges the request and states the first step). Note this is model-specific: GPT-5.3-Codex guidance says the opposite (avoid upfront plans that interrupt rollouts).
- Stronger on large tool surfaces - fewer prompt tricks needed for tool selection. Tone is warmer / more direct out of the box.

**Newly documented GPT-5.x techniques (developers.openai.com/api/docs/guides/prompt-guidance):**
- **Eagerness / persistence controls.** For LESS eagerness: lower `reasoning.effort`, define explicit early-stop conditions, set a fixed tool-call budget (e.g. max 2 calls). For MORE: raise effort, add a persistence directive ("keep going until the query is completely resolved") and "decide, proceed, and document" instead of asking for clarification. "Parallelize independent evidence gathering, not speculative or redundant tool use."
- **Self-reflection rubric.** "Develop a 5-7 category rubric, then iteratively evaluate your solution against it before responding." A named technique for hard tasks.
- **Verification loop / Completeness contract / Empty-result recovery.** Check correctness, grounding, and formatting before finalizing; carry an explicit checklist of deliverables; specify a structured fallback search strategy before concluding "no results".
- **Phase parameter.** In agentic Responses-API flows, mark intermediate updates `phase: "commentary"` vs the final answer `phase: "final_answer"`.
- **Constraint-language discipline.** Reserve absolute language (ALWAYS / NEVER / MUST) for genuine safety rails; express judgment calls as "If X, then Y". Overusing absolutes degrades instruction following.
- **Separate personality from collaboration style.** Define tone/warmth/directness separately from when-to-ask-questions / proactivity / uncertainty handling.
- **Few-shot framing has softened.** The current concern is prompt length / token efficiency ("smallest prompt that preserves the contract"), not a blanket "few-shot hurts reasoning models". Keep examples only when load-bearing for the output contract. (Verify the exact current language in OpenAI's GPT-5.x prompting guide before a public release.)

---

### OpenAI GPT-4.1 / 4.1 mini / 4.1 nano

> **Status:** Retired from ChatGPT 2026-02-13. API still live. `gpt-4.1-nano` API deprecates 2026-10-23 (→ `gpt-5.4-nano`); base `gpt-4.1` and `gpt-4.1-mini` have no confirmed API sunset date yet. New work should target the GPT-5.x family unless cost-constrained.

**Prompt structure**: Markdown headers.
```markdown
# Purpose
Extract product information from input text with high accuracy.

# Instructions
Parse the input and return structured JSON.

# Constraints
- Use null for missing values.
- Maximum 5 tags per product.

# Examples
Input: ...
Output: ...

# Output Format
Return valid JSON matching the schema below.
```

**Tips:**
- `# Purpose` > `# Role` - goal-oriented headers produce better instruction following. Don't overload `# Role` with persona text instead of stating the goal.
- Few-shot examples work very well (3-5 optimal).
- Prompt caching is automatic - static content at the top, dynamic input at the bottom.
- `temperature: 0` for deterministic tasks (extraction, classification).
- Tends to wrap JSON in markdown code blocks - instruct against it explicitly (`"Return ONLY valid JSON, no markdown, no code blocks"`).
- Long system prompts work fine - the model handles structure well.

**n8n notes:** native OpenAI Chat nodes support structured output - use it for JSON instead of prompting. For GPT-4.1 nano on classification, `responseFormat: "json_object"` is sufficient; no need for long schema descriptions.

---

### OpenAI o3 / o4-mini (reasoning)

> **Status:** o4-mini retired from ChatGPT (2026-02-13); o3 still toggle-accessible. API still live, with confirmed sunsets: `o3` (snapshot `o3-2025-04-16`) deprecates **2026-12-11**, `o3-mini` and `o4-mini` deprecate **2026-10-23** - all replaced by the GPT-5.x family. For new builds prefer GPT-5.5 with `reasoning.effort: high` or `xhigh`. No `o5` family exists (reasoning is now a mode of GPT-5.x, not a separate brand).

**Prompt structure**: Minimal. Goal-oriented. Use the `developer` role instead of `system`.
```markdown
Analyze the following data and determine the best pricing strategy.
Consider market position, competitor pricing, and margin requirements.
Return your recommendation as JSON with strategy, price_point, and reasoning.
```

**Tips:**
- **Simpler is better** - treat as a senior colleague who needs a goal, not instructions.
- Do NOT add "think step by step" - it is built in, prompting for it **hurts performance**.
- Few-shot examples are often **counterproductive** - remove them.
- No `temperature`, `top_p` - not supported.
- Use `reasoning.effort: "low|medium|high"` to control depth.
- Best for: complex decisions, code architecture, LLM-as-judge, planning, evaluation steps.

**n8n notes:** no native node yet - use the HTTP Request node against the OpenAI API. Latency is higher; do not use in time-sensitive webhook flows.

---

### Anthropic Claude (Fable 5 / Opus 4.8 / Opus 4.7 / Sonnet 4.6)

**Prompt structure**: XML tags.
```markdown
<purpose>
Extract structured product data from e-commerce inputs with high accuracy.
Return clean JSON matching the provided schema.
</purpose>

<input>
{{product_text}}
</input>

<constraints>
- Use null for missing values. Never fabricate.
- Preserve original language of product names.
- Maximum 5 categories per product.
</constraints>

<examples>
<example>
Input: "iPhone 15 Pro, 128GB, vesmírně černá, 29 990 Kč"
Output: {"name": "iPhone 15 Pro", "storage": "128GB", "color": "vesmírně černá", "price": 29990, "currency": "CZK"}
</example>
</examples>

<output_format>
Return ONLY valid JSON matching the schema. No other text.
</output_format>

<constraints>
Repeat the critical constraints here (top AND bottom).
</constraints>
```

**Core tips (all current Claude models):**
- XML tags are Claude's primary structuring mechanism - it is trained on them, they are not just formatting.
- Anthropic's priority order: **clarity first, examples second, identity/role third.** Purpose/goal framing outperforms role framing for correctness. Don't skip `<purpose>` and jump straight to instructions.
- **Explain WHY** behind rules - "Never fabricate data - output feeds a production database" works better than "Never fabricate data" alone. Motivation increases adherence.
- Constraints in the middle of long prompts get ignored - put them **at top AND bottom**.
- Claude trends verbose - explicit "ONLY [format], no other text" helps.
- Prefill technique (starting the assistant turn with `{`) **returns 400** on all current models - use `output_config.format` (structured outputs) / `messages.parse()` instead.
- Extended thinking is now **adaptive only** on the frontier models: `thinking:{type:"adaptive"}` plus `output_config.effort`. Do NOT set `budget_tokens` (400 on Fable 5 / Opus 4.7 / 4.8; deprecated on Opus 4.6 / Sonnet 4.6). Do NOT set `temperature`/`top_p`/`top_k` on Fable 5 / Opus 4.7 / 4.8 (400) - steer via prompt instead.

**Re-baseline old prompts (the single biggest prompting change).** Recent Claude models do natively what older prompts scaffolded by hand. Remove `"double-check before returning"`, `"give interim status updates"`, `"don't generalize"`, `"think step by step"` - leaving them in causes verbosity and over-validation.

**Opus 4.7 behavioral shifts (still apply, and are the baseline for 4.8):**
- More literal instruction following - it will not silently generalize one instruction to another or infer requests you did not make. Tighten ambiguous prompts that relied on the model "reading intent".
- Verbosity calibrates to task complexity - shorter on simple lookups, longer on open-ended work. If you depend on a fixed length, instruct it explicitly (positive examples of the target concision beat "don't be verbose").
- More direct / opinionated tone, less validation phrasing, fewer emoji. Specify a warmer voice if you need one.
- `effort` matters more than on any prior Opus. Use `xhigh` for coding/agentic, a minimum of `high` for most intelligence-sensitive work; at `xhigh`/`max` set a large `max_tokens` (start 64K).
- Uses tools and spawns subagents less by default - add explicit "when to use this tool/subagent" guidance if your product depends on tool use.
- Design house-style (cream/serif) is persistent; for non-editorial UIs, give a concrete palette/typeface or ask the model to propose 4 directions before building.
- Code review follows "only report high-severity" filters literally, which can depress measured recall - tell it to report everything with confidence + severity and filter downstream.

**Opus 4.8 specifics (current default Opus):**
- Same request surface as 4.7 (no new breaking changes). 1M context at standard pricing, 128K output.
- **Narrates more than 4.7** - more text between tool calls and longer end-of-task wrap-ups by default. Remove forced-progress scaffolding (`"after every 3 tool calls, summarize"`); add a silence-default if a coding agent is too chatty.
- **More deliberate - asks more often.** On minor decisions it pauses and asks, and closes finished tasks with "Want me to also...?". Add "for minor choices (naming, defaults, equivalent approaches), pick a reasonable option and note it rather than asking; still ask first for scope changes or destructive actions."
- **Under-reaches for search, subagents, file-based memory, and custom tools.** Steer with explicit triggering both in the system prompt AND in each tool's own `description` (prescriptive "call this when..." descriptions give measurable lift over "what the tool does").
- **Warmer, less hedged writing** (roughly the opposite of the 4.7 shift) - re-evaluate any style prompts you added to counter 4.7's terseness; they may now overcorrect.
- With `thinking` disabled it can leak reasoning into the visible response - leave adaptive thinking on, or add a final-answer-only instruction.
- **Mid-conversation system messages (Opus 4.8 only):** append `{"role":"system", "content":"..."}` to `messages[]` to inject operator context mid-session without invalidating the prompt cache. Phrase as context, not override-style commands.

**Claude Fable 5 specifics (most capable, above Opus tier):**
- Thinking is always on (omit the `thinking` param). The raw chain of thought is never returned; read the `display:"summarized"` summary if you need reasoning visible.
- Prompts written for prior models are often too prescriptive and *reduce* output quality - A/B with step-by-step scaffolding removed; prefer stating the goal and constraints over enumerating steps.
- Single requests on hard tasks can run many minutes - plan timeouts, streaming, and async check-ins.
- Handle `stop_reason:"refusal"` before reading content (safety classifiers target bio / cyber); opt into server-side `fallbacks` by default. Requires 30-day data retention (no ZDR).
- Reserve Fable 5 for the genuinely hardest long-horizon work - it is priced above Opus tier ($10/$50). For "use the latest Claude", the target is `claude-opus-4-8`.

**Sonnet 4.6:** best value (`$3/$15`, 1M context). Supports adaptive thinking; effort `low/medium/high/max`. More concise by default than 4.5 - may skip the summary after a tool call; ask explicitly if you want one. For agents with many tools (5+) this is the recommended default; escalate to Opus 4.8 / Fable 5 only for the hardest reasoning + agentic coding.

**Server tools (current versions):** web search / fetch are `web_search_20260209` / `web_fetch_20260209` (built-in dynamic filtering) on Opus 4.8 / 4.7 / 4.6 + Sonnet 4.6; do NOT also declare `code_execution` alongside them.

**n8n notes:** the native Anthropic node supports extended thinking via `thinking.type:"adaptive"` + `effort`. `responseFormat:"json_object"` works, but an explicit `<output_format>` with the schema still improves reliability.

---

### Google Gemini 3 / 3.1

**Prompt structure**: Markdown or plain text. No strong preference.
```markdown
You are a data extraction specialist.

Extract product information from the following text:
{{input}}

Return a JSON object with these fields:
- name (string)
- price (number)
- currency (string)
- category (string, one of: electronics, clothing, food, other)

Rules:
- Use null for missing values.
- Do not add extra fields.
```

**Tips (Gemini 3.x, from the official Gemini 3 prompting + developer guides):**
- **Direct, concise prompts.** Gemini 3 responds best to direct, clear instructions; verbose prompt engineering and hand-written chain-of-thought are LESS necessary - `thinking_level: high` replaces hand-crafted CoT scaffolding.
- **Keep temperature at the default 1.0.** Gemini 3's reasoning is optimized for the default; lowering it can cause unexpected behavior on complex reasoning tasks. (This is a change from older "lower temperature for determinism" advice.)
- **Context placement for large inputs:** put the question AFTER the long content, anchored with "Based on the preceding information...".
- **System-instruction hygiene:** for time-sensitive tool calls, insert the current date/year; state the knowledge cutoff explicitly (January 2025 for Gemini 3). For agentic system prompts, structure around logical decomposition, diagnosis depth, information exhaustiveness, adaptability, persistence/recovery, risk assessment (reads vs writes), ambiguity handling (when to ask vs assume), and verbosity control alongside tool calls.
- Gemini 3.1 Pro is designed for concise, direct answers and may guess when info is missing - mitigate with `"If information is missing, return null for that field"`.
- 1M context window, but quality still degrades on very large fills - don't rely on the full window for precision-critical tasks.

**Reasoning (`thinking_level`):**
- For Gemini 3, use `thinking_level`, NOT `thinking_budget` - `thinking_budget` is not supported on Gemini 3 (it remains the parameter for Gemini 2.5). Setting both in one request returns a 400.
- Levels: **`low / medium / high`** on Gemini 3.1 Pro and Gemini 3.5 Flash; **`minimal`** is additionally available only on Flash-Lite and 3 Flash. (Correction: the prior revision wrongly said 3.1 Pro had only low/high.)
- Even `minimal` still generates and requires thought signatures.

**Structured output:**
- Legacy `generateContent` API: `responseMimeType: "application/json"` + `responseSchema` in `generationConfig`. Newer Interactions API: `response_format` with `mime_type` + `schema` (or `response_format: {type: "json_object"}` for JSON mode with no schema). The parameter is NOT `responseJsonSchema`.
- Official guidance is to use clear `description` fields and state plainly what you want; the "+3 examples + 'ONLY JSON'" trick is community practice, not official Google guidance (do, however, always validate). Structured output combined with tools is a Preview feature on Gemini 3.
- Schema limits still apply: not all JSON Schema features are supported; very large / deeply nested schemas may be rejected; property order in the prompt must match the schema.
- For classification, the `text/x.enum` response type (`response_mime_type="text/x.enum"` + a STRING enum schema) is confirmed current and cleaner than prompting.

**Function calling:**
- Modes: `auto` (default) / `any` / `none` / **`validated`** (Preview - the model is held to the function schema; new since the prior revision).
- AUTO mode may skip tool calls in long agentic conversations; switch to `any` for deterministic tool use. (The specific "breaks after 15-20 turns" threshold is a community observation, NOT an official Google finding - do not state it as fact.)
- `thought_signature` continuity: in stateless mode you MUST return all thought blocks exactly as received; in stateful Interactions mode (`store: true` + `previous_interaction_id`) the server manages signatures. The official SDKs handle this automatically when you append the full model response. Gemini 3 also circulates `id` / `tool_type` / `thought_signature` across turns. (A 400 for a missing `thought_signature` is reported but was not confirmed against a primary doc page - human-verify on ai.google.dev/gemini-api/docs/thought-signatures before a public release.)

**Vision / multimodal:** natively multimodal; documented strengths are document understanding (1,000+ page PDFs with charts/tables/handwriting/multi-column), multilingual OCR, conversational image segmentation, and code-execution-on-images (zoom/crop/annotate). **Do not claim it beats Claude / GPT for image analysis - Google publishes no such comparison.** Test for the specific task.

**n8n notes:** native Gemini node; for structured JSON output use the node's structured-output / `responseSchema` setting rather than prompting. For high-volume pipelines, Gemini 3.1 Flash-Lite is the cheapest option with acceptable quality.

---

### Perplexity Sonar

**Category:** search-augmented generation (RAG), not pure generation. Different use case from the models above.

**Tips:**
- Don't ask it to "search the web" - just ask the question directly. Sonar retrieves sources automatically.
- For structured output: explicit schema in the prompt + "Return ONLY JSON" - native structured output is less reliable than OpenAI / Claude; always validate.
- `sonar-deep-research` is slow - always use the async API; results are stored ~7 days.

**n8n notes:** no native node - use the HTTP Request node against the Perplexity API. Best for current events, real-time data, and fact-grounded outputs with citations. Not for extraction from known documents, deterministic classification, or anything where hallucination is unacceptable.

---

### Qwen 3.5 / 3.6 (self-hosted)

**Prompt structure**: Markdown headers with explicit examples.
```markdown
# Purpose
Extract product information from input text. Return structured JSON.

# Input
{{input_text}}

# Output Format
Return ONLY a JSON object:
{
  "name": "string",
  "price": number or null,
  "currency": "string or null"
}

# Example
Input: "Notebook Lenovo ThinkPad, 25 000 Kč"
Output: {"name": "Notebook Lenovo ThinkPad", "price": 25000, "currency": "CZK"}
```

**Tips:**
- Size selection: 9B for basic tasks, 27B / 35B-A3B for production, 122B-A10B for best tool calling, 397B-A17B for frontier. For agentic coding, prefer Qwen3.6-27B or 3.6-35B-A3B (2026-04).
- Hybrid thinking mode: `/think` and `/no_think` per turn in the user message.
- Thinking mode: temperature=0.6, top_p=0.95, top_k=20. Non-thinking: 0.7 / 0.8 / 20.
- 0.8B and 2B default to non-thinking; 4B+ default to thinking mode.
- Never greedy decoding with thinking mode (causes loops / repetition).
- Tool calling: `--tool-call-parser qwen3_coder` (replaces `hermes` for Qwen 3.5 / 3.6; `hermes` streaming had a bug on Qwen3).
- vLLM (≥0.19.0): `--enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3`.
- Native multimodal (early fusion) from 4B up - text + image + video in the same model.
- 201 languages supported.
- DashScope offers an Anthropic-API-compatible endpoint - drops into Claude Code or any Anthropic SDK client.

---

## Prompt Patterns by Use Case

These two frameworks are provider-agnostic scaffolds. Combine them with the per-provider structure above (XML tags for Claude, Markdown headers for OpenAI/Qwen, etc.). Include only the sections that affect output quality - a 3-field prompt is fine for a simple task.

### Single model call (classic automation)

**When:** single-step task with no tool calls or branching.

```
ROLE:         [Expertise/identity - skip if Purpose is enough]
CONTEXT:      [Business context, input characteristics, audience]
TASK:         [Clear objective - one sentence]
REQUIREMENTS: [Must-haves]
FORMAT:       [Structure + length]
EXAMPLE:      [Realistic input → expected output]
CONSTRAINTS:  [Key limits]
```

**Example (extraction):**

```
TASK: Extract structured data from the email below.

FORMAT:
Return ONLY valid JSON matching this schema:
{
  "sender_name": "string",
  "company": "string or null",
  "request_type": "invoice | support | sales | other",
  "urgency": "high | medium | low",
  "summary": "string, max 100 chars"
}

CONSTRAINTS:
- Never fabricate - output feeds production DB
- If a field cannot be determined, use null
- No markdown, no code blocks, ONLY JSON

EMAIL:
{{ $json.body }}
```

### AI agent

**When:** multi-step task requiring tool calls, branching decisions, or state tracking across turns.

```
ROLE & MISSION: [Identity + purpose]
SOP:            [Decision flow with explicit IF/THEN logic]
TOOLS:          [One doc block per tool]
DECISION RULES: [Explicit branching]
MEMORY:         [What to track across steps]
OUTPUT:         [Final format]
CONSTRAINTS:    [Repeat at end]
```

**SOP pattern (explicit, deterministic branching):**

```
State: Customer inquiry received

Classify urgency:
→ IF message contains ["urgent", "critical", "down"]: HIGH priority
→ ELSE: MEDIUM priority

Action: search_kb(query=customer_message)
→ IF confidence > 0.8: Provide answer
→ IF confidence 0.5–0.8: Provide answer + flag for review
→ IF confidence < 0.5: Escalate to human

Errors:
→ search_kb timeout: Retry once → if still fails, escalate
→ search_kb 500: Use cached response from last 24h
```

**Tool documentation pattern (one block per tool):**

```
Tool: search_customer_db

Purpose: Look up customer records (purchase history, account status, contact info)
DO NOT use for: Products, orders, internal documentation

Parameters:
* customer_id (string, required): Format "cust_" + 8 alphanumeric chars
  Example: "cust_a1b2c3d4"
* fields (array, optional): Limit returned fields. Default: all.

Output: {found: bool, customer: {id, name, email, status, purchases[]}, confidence: float}

Errors:
* 404: Customer not found → Ask user to confirm ID
* 500: Server error → Use cached data if available, else escalate
* rate_limit: Wait 2s → Retry once
```

A prescriptive `Purpose` + `DO NOT use for:` per tool is the single most effective fix for wrong-tool selection. On recent Claude models (which reach for tools more conservatively), a "call this when..." trigger in the description gives measurable lift.

**Error handling pattern:**

```
Call: payment_api.process(order_id, amount)
→ SUCCESS: Validate response.transaction_id exists → Confirm to user
→ TIMEOUT: Retry once after 5s → If fails, flag as "pending manual check"
→ 400: Parse error_code from response → Show user-friendly message
→ 500: Wait 30s → Retry → If fails, add to retry queue
```

**State management (only when truly needed across turns):**

```
Track:
{
  "customer_id": "...",
  "urgency": "high | medium | low",
  "tools_used": ["search_kb", "search_customer_db"],
  "current_state": "awaiting_confirmation"
}

Rules:
- Update after each tool call
- Prune conversation history after 10 exchanges
- Never carry sensitive data (PII, payment info) in state
```

---

## JSON Output

### 1. Schema first

Define the schema in the prompt; include one example covering the key case.

```
Return ONLY valid JSON matching this schema - no markdown, no code blocks:
{
  "topics": [
    {
      "name": "string (3–50 chars)",
      "priority": "integer 1–5",
      "rationale": "string or null"
    }
  ],
  "total_count": "integer"
}
```

### 2. Escape rules

```
"Output valid JSON:
- Quotes inside strings: use \"
- Newlines inside strings: use \n (not actual line breaks)
- Backslashes: use \\
- No trailing commas
- All strings in double quotes"
```

### 3. Null handling

```
"Missing or unknown data:
- null = field cannot be determined
- '' = explicitly empty string
- [] = empty array
- 0 = zero count
Never use: 'N/A', 'unknown', 'null' as string values"
```

### 4. Validation instruction

```
"Before outputting: verify schema match, all required fields present, correct types.
If validation fails: fix silently, then output ONLY JSON."
```

### 5. Provider-specific JSON reliability

Prefer API-level enforcement over prompting wherever it exists - it is strictly more reliable than asking nicely.

| Provider | Reliability | Best practice |
|----------|-------------|---------------|
| OpenAI GPT-5.5 / GPT-4.1 | High | `responseFormat: "json_object"` or the structured-output API |
| OpenAI o3 / o4-mini | High | Structured-output API; prompt-only is less reliable |
| Claude (all current) | High | `output_config.format` (structured outputs) / `messages.parse()`. Prefill is gone (400) - do not rely on starting the response with `{`. XML `<output_format>` + "ONLY JSON" as a backstop. |
| Gemini 3.x | Medium | Enforce via API: `responseSchema` (`generateContent`) or `response_format.schema` (Interactions API). NOT `responseJsonSchema`. Validate output; the "+3 examples / ONLY JSON" trick is a community backstop, not official guidance. |
| Perplexity Sonar | Lower | Schema in prompt + "ONLY JSON" - always validate output |

---

## Model Selection for n8n Tasks

| Task | Best Model | Why |
|---|---|---|
| Simple extraction | GPT-5.5 (low effort), Gemini 3.5 Flash / 3 Flash, Qwen 3.5-9B | Fast, cheap, reliable with schema |
| Complex extraction (OCR, messy) | GPT-5.5, Claude Sonnet 4.6, Gemini 3.x (document/OCR) | Better on ambiguous inputs; Gemini strong on document/OCR |
| Agent (< 5 tools) | GPT-5.5 (low/med), Claude Sonnet 4.6 | Good tool calling, reasonable cost |
| Agent (5-20 tools) | GPT-5.5 (Responses API), Claude Sonnet 4.6, Qwen 3.5-122B-A10B / Qwen 3.6-27B | Best tool selection accuracy |
| Agentic coding (hardest) | Claude Opus 4.8 (xhigh) or Claude Fable 5; GPT-5.5 Pro | Frontier long-horizon agentic execution |
| Complex reasoning step | GPT-5.5 (high/xhigh), Claude Opus 4.8 (adaptive, `xhigh`) | Built-in reasoning |
| Content generation | Claude Sonnet 4.6, GPT-5.5 (verbosity: medium) | Best natural language quality |
| Localization / transcreation | Claude Opus 4.8 / Fable 5 | Best cultural nuance |
| Real-time / web search | Perplexity sonar / sonar-pro | Only models with live retrieval + citations |
| High-volume, cost-sensitive | Qwen 3.5-35B-A3B (Flash), Gemini 3.1 Flash-Lite ($0.25/$1.50) | Lowest cost per token |
| Classification, autocomplete | GPT-4.1 nano, Qwen 3.5-2B, Gemini 3.1 Flash-Lite | Fastest, cheapest |
| Self-hosted production | Qwen 3.6-27B / 3.6-35B-A3B (preferred) or 3.5-122B-A10B | Best open-weight for tool use + agentic coding |

---

## Quick Reference

### Anti-patterns

| Anti-pattern | Fix |
|---|---|
| `"Make it good"` | `"Logical flow + 3 supporting examples + conclusion with next step"` |
| Placeholder examples (`[your data here]`) | Realistic data that matches actual input |
| `"If necessary, handle errors"` | `"On timeout: retry 2x. On 500: queue for retry. On 400: return error_code to user"` |
| Constraints buried in the middle of the prompt | Put at top AND bottom (especially Claude) |
| `"Think step by step"` with o3/o4-mini or GPT-5.5 | Remove - hurts reasoning-model performance |
| Scaffolding on frontier Claude (`"double-check"`, `"give status updates"`, `"don't generalize"`) | Remove - the model does this natively; leaving it in causes verbosity / over-validation |
| Setting `temperature`/`top_p`/`top_k` on Fable 5 / Opus 4.7 / 4.8 | Remove - returns 400; control via prompt only |
| `budget_tokens` on Fable 5 / Opus 4.7 / 4.8 | Remove - returns 400; use `thinking:{type:"adaptive"}` + `effort` |
| `{type:"disabled"}` thinking on Fable 5 | Remove - returns 400; omit the `thinking` param entirely |
| Assistant prefill (starting with `{`) on any current Claude model | Returns 400 - use `output_config.format` instead |
| JSON without `"no code blocks"` instruction | GPT-4.1 wraps JSON in markdown - always explicitly forbid |
| `"Search the web for..."` with Perplexity | Just ask the question - Sonar retrieves sources automatically |
| Few-shot examples with reasoning models | Remove - often counterproductive |
| Role-heavy framing (`"You are an expert..."`) | Purpose-first framing (`"# Purpose: Extract..."` / `<purpose>`) |
| Writing the prompt in the output language | Prompt body is always English; state output language as a one-line constraint |

### Symptom → Fix

| Symptom | Fix |
|---------|-----|
| Inconsistent output | Add specific format requirements with an example |
| JSON wrapped in markdown | Add `"ONLY JSON, no code blocks, no markdown"` |
| Fields sometimes null, sometimes missing | Explicit null policy in the prompt |
| Agent picks the wrong tool | Add `DO NOT use for:` to each tool doc + a "call this when..." trigger |
| Reasoning model ignoring detailed instructions | Simplify to a goal statement - remove step-by-step |
| Long agent sessions break tool calling (Gemini) | Switch from AUTO to ANY mode |
| Claude skipping summaries | `"After each tool call, briefly summarize what you found"` |
| Output too verbose (Opus 4.8 narrates a lot) | Silence-default: `"default to silence between tool calls; only write when you find something, change direction, or hit a blocker"` |
| Claude asks too many small questions (Opus 4.8) | `"For minor choices, pick a reasonable option and note it; only ask first for scope changes / destructive actions"` |
| Claude under-uses search / subagents / memory (Opus 4.8) | Add explicit "when to use X" triggers in the system prompt AND each tool's description |
| `refusal` stop reason on Fable 5 | Handle `stop_reason:"refusal"` before reading content; opt into server-side `fallbacks` |

### Pre-deploy checklist

```
ALL PROMPTS:
□ Test with 5+ realistic inputs
□ Test edge cases (empty input, missing fields, unexpected format)
□ Verify output consistency across runs
□ Prompt body is English; output language stated as a constraint

CLASSIC AUTOMATION:
□ Task is unambiguous
□ Format is explicit with an example
□ Null/missing data handling defined
□ JSON: schema + no-markdown instruction + validation

AGENTS:
□ SOP covers all expected states
□ Every tool has complete documentation (purpose, params, errors, "when to use")
□ IF/THEN logic is deterministic - no ambiguous branches
□ Error handling for each tool
□ State tracking defined if multi-turn

PROVIDER-SPECIFIC:
□ Claude: constraints at top AND bottom; no prefill; no budget_tokens/sampling on Fable 5 / Opus 4.7+
□ GPT-4.1: no-code-blocks instruction for JSON
□ GPT-5.5 / o-series: no step-by-step, no few-shot; Responses API
□ Gemini long sessions: tool mode = ANY
□ Perplexity: output validated, not assumed correct
```

---

## Claude Code Skills

### What Skills are
Modular instruction packages for Claude. Each skill = a directory with `SKILL.md` + optional supporting files. Claude loads them automatically when relevant, or users invoke via `/skill-name`.

Follows the **Agent Skills open standard** (Dec 2025) - works across Claude Code, GitHub Copilot, VS Code, Cursor, Amp, OpenCode.

### SKILL.md template

```yaml
---
name: my-skill              # Required. Lowercase, hyphens. Max 64 chars.
description: >               # Required. Max 1024 chars. THE trigger mechanism.
  What it does + when to use it + trigger phrases.
  THIRD PERSON only - description is injected into the system prompt.
  Be "pushy" - Claude under-triggers by default.
license: Apache-2.0          # Optional.
metadata:                    # Optional.
  version: "1.0"             # Bump on changes - helps eval across model updates.

# Claude Code extensions (Claude Code only; safely ignored by Codex / Gemini / Copilot):
disable-model-invocation: false  # true = manual only (/skill-name)
context: fork                    # Isolated subagent context
agent: Explore                   # Subagent type
model: claude-haiku-4-5          # Override model when context: fork (cheaper for routine work)
effort: medium                   # low / medium / high - reasoning depth for forked context
allowed-tools: [Read, Grep]      # CLI only (not SDK) - restrict tools available to skill
hooks:                           # Event triggers
  - event: pre-commit
    command: ./scripts/validate.sh
argument-hint: "<file-path>"     # Tells caller what input to provide
arguments:                       # Structured argument schema
  - name: target
    required: true
---

# Skill Name

Core instructions here. Keep under 5,000 tokens.

## Workflow
1. Step one
2. Step two - reference [details](references/REFERENCE.md)
3. Step three - run validation script

## Output Format
[What the skill produces]

## Examples
[1-2 examples of expected behavior]
```

### Directory structure
```
my-skill/
├── SKILL.md              # Required - instructions
├── scripts/              # Executed via bash (zero context cost)
│   └── validate.py
├── references/           # Loaded on-demand into context
│   └── REFERENCE.md
└── assets/               # Templates, schemas
    └── template.json
```

### Progressive disclosure (token budget)
| Level | Loads | Cost | When |
|---|---|---|---|
| Metadata | name + description | ~100 tokens | Always |
| Instructions | Full SKILL.md | <5,000 tokens | When triggered |
| References | Supporting files | Variable | On-demand |
| Scripts | Executed only | 0 tokens | When needed |

### Writing good descriptions (critical)

Claude **under-triggers** skills by default. Be pushy:

**Good**: "Use this skill whenever the user wants to do anything with PDF files. This includes reading, extracting, combining, splitting, rotating, watermarking, creating, filling forms, encrypting, extracting images, and OCR."

**Bad**: "PDF processing skill."

All "when to use" info belongs in the description, not the body. **Always write in third person** - the description is injected into the system prompt; inconsistent POV breaks discovery.

**skill-creator (Mar 2026 update):** runs real tests, scored results, and blind comparisons to auto-improve descriptions across model updates. Use it instead of hand-tuning if you have evals.

**Performance:** running >20–50 active skills simultaneously degrades performance - descriptions load into context on every message. Prune aggressively.

### Four skill types
| Type | Purpose | Settings |
|---|---|---|
| Reference | Knowledge (style guides, conventions) | Auto-loads when relevant |
| Generator | Step-by-step actions (deploy, generate) | Often `disable-model-invocation: true` |
| Orchestration | Multi-step, parallel agents | `context: fork` + `agent` field |
| Mode | Modify Claude's behavior globally | `mode: true` in frontmatter |

### Skill locations
- Personal: `~/.claude/skills/`
- Project: `.claude/skills/`
- Plugin: `skills/` within plugin
- Managed: org-wide deployment

---

## Cowork Plugins

### What plugins are
Bundles of skills + MCP connectors + slash commands + sub-agents in one installable package. File-based (markdown + JSON), no code required. All paid Claude plans.

### Plugin structure
```
plugin-name/
├── .claude-plugin/
│   └── plugin.json        # Manifest
├── commands/              # Slash commands (.md)
│   └── review.md
├── agents/                # Sub-agents (.md)
│   └── specialist.md
├── skills/                # Skills (subdirs with SKILL.md)
│   └── my-skill/
│       └── SKILL.md
├── .mcp.json              # MCP server config
└── README.md
```

### plugin.json manifest
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What this plugin does",
  "author": {"name": "Author"},
  "commands": "./commands/",
  "agents": "./agents/",
  "skills": "./skills/",
  "mcpServers": "./.mcp.json"
}
```

Only `name` is required. The manifest itself is optional - Claude auto-discovers components.

### Building a plugin
1. Create directory structure
2. Write plugin.json
3. Add skills, commands, agents, MCP config
4. Test: `claude --plugin-dir ./your-plugin`
5. Install: Cowork UI upload or `claude plugin install name@marketplace`

Bump `version` on changes - caching ignores updates without a version change.

### MCP in plugins
Connectors wire Claude to external tools via MCP servers. Plugins are **tool-agnostic** - describe workflows by category (CRM, project tracker), not specific products. Plugins degrade gracefully when tools are unavailable.

### Org-managed plugins (Team/Enterprise)
- Distribution: ZIP upload or private GitHub repo sync
- Controls: Auto-install / Available / Not available per plugin
- Limits: 50 MB/ZIP, 100 plugins/marketplace
- Members cannot edit org-managed plugins

### Official Anthropic plugin expansions (May 2026)
- **Legal vertical (2026-05-12):** 20+ MCP connectors (Thomson Reuters CoCounsel, DocuSign, Everlaw, Box, Harvey, Midpage, Trellis, Legal Data Hunter, Solve Intelligence) + 12 practice-area plugins (contract law, employment, litigation, etc.). Subsets (Commercial / Corporate / Litigation / Product Legal) also available as cookbooks deployable as Managed Agents via API. Microsoft 365 (Word, Outlook, Excel, PowerPoint) context-carrying integration.
- **Claude for Small Business (2026-05-13):** Cowork toggle. Integrations: QuickBooks, Canva, DocuSign, HubSpot, PayPal. 15 ready-made skills (payroll planning, bookkeeping, employee onboarding).
- **Claude Code 2026-05 additions:** agent view, `/goal` command, `/ultrareview` slash command, richer plugin/context tools, smoother MCP / Remote Control / transcript navigation. Default effort raised to `xhigh` (the Opus 4.8-era default in Claude Code).

> The Skills, Plugins, and dated platform-expansion notes above are harness/feature details (not per-provider prompting), carried forward from the prior revision and not part of the June 2026 prompting research pass. Verify any dated claim against current Anthropic release notes before quoting it publicly.

---

## Change log

| Date | Added | Source | Removed |
|------|-------|--------|---------|
| 2026-06-26 | **Merged `ai-prompt-guidelines.md` into this reference and research-refreshed.** Folded in: two Core Principles (Optimal-not-Minimal; Prompt-language-vs-Output-language), Perplexity Sonar (new model row + per-provider section + JSON-reliability row), the "Prompt Patterns by Use Case" frameworks (Single model call + AI agent SOP/tool-doc/error-handling/state), the "JSON Output" section (schema-first / escape / null / validation / provider reliability), and the "Quick Reference" (Anti-patterns, Symptom→Fix, Pre-deploy checklist). **Anthropic section rebuilt from the authoritative `claude-api` reference (cached 2026-06-04):** added **Claude Fable 5** (`claude-fable-5`, most-capable, $10/$50, always-on thinking, no prefill, refusal+fallbacks, 30-day-retention requirement) and **Claude Opus 4.8** (`claude-opus-4-8`, current default Opus, mid-conversation system messages, narrates-more / asks-more / under-reaches-for-tools behavioral shifts). Mythos Preview note replaced (succeeded by `claude-mythos-5`, public frontier = Fable 5). Corrected Opus 4.6 pricing to $5/$25, Sonnet 4.6 to 1M ctx / 64K out, Haiku 4.5 to 64K out. Updated retirement dates (Opus/Sonnet 4 retired 2026-06-15; Opus 4.1 retires 2026-08-05). Effort/thinking/sampling/prefill rules aligned to the frontier surface. Model Selection table updated to Opus 4.8 / Fable 5 + Perplexity row. **OpenAI refresh (research pass):** clarified "GPT-5.5 Instant" is a ChatGPT product name not an API model; documented `gpt-5.5-pro` and the cheaper GPT-5.4 family; corrected `text.verbosity` to three levels; added confirmed API deprecation dates (gpt-4.1-nano 2026-10-23, o3 2026-12-11, o3-mini/o4-mini 2026-10-23); added newly-documented techniques (eagerness/persistence controls, self-reflection rubric, verification loop / completeness contract / empty-result recovery, phase parameter, constraint-language discipline, personality-vs-collaboration split) and the Responses-API Tau-Bench gain; corrected Perplexity (sonar-reasoning retired → sonar-reasoning-pro, pricing). **Gemini refresh (research pass):** added the missing **`gemini-3.5-flash`** (GA 2026-05-19); corrected `thinking_level` (low/med/high on 3.1 Pro + 3.5 Flash, minimal only on Flash-Lite/3-Flash; thinking_budget removed on Gemini 3); fixed structured-output param (`responseSchema`/`response_format.schema`, not `responseJsonSchema`); added `validated` tool mode; downgraded the "AUTO breaks after 15-20 turns" claim to community observation; added Gemini-3 prompting guidance (default temperature 1.0, context-after-content, agentic system-instruction dimensions, date/cutoff hygiene); removed the unsourced "Gemini beats Claude/GPT on vision" claim; resolved the 1M-vs-2M context conflict (1M is official). Items still flagged for human verification: Gemini `thought_signature`-missing 400, OpenAI current few-shot wording. | Anthropic `claude-api` skill reference (authoritative, cached 2026-06-04: models.md, model-migration.md, SKILL.md); `ai-prompt-guidelines.md` (absorbed); June 2026 OpenAI (developers.openai.com) + Gemini (ai.google.dev / Vertex AI) + Perplexity (docs.perplexity.ai) research pass | OpenAI table reshaped (GPT-4.1 mini / o4-mini referenced in status notes). The "Mythos Preview = internal frontier" framing (superseded by public Fable 5). The unsourced Gemini-vision-superiority claim. |
| 2026-05-13 | **OpenAI:** New GPT-5.5 / 5.5 Pro / 5.5 Instant table column with API IDs, pricing, `reasoning.effort` 5 levels incl. `xhigh`, `text.verbosity`, Responses API recommendation, outcome-first prompting block. GPT-4.1 family marked "retired from ChatGPT 2026-02-13, API still live". Status notes on o3 / o4-mini. **Anthropic:** Task Budgets → public beta with API example. Fast Mode for Opus 4.7. Advisor Tool, Memory for Managed Agents, Rate Limits API, Claude Platform on AWS, Multiagent sessions. Mythos Preview flagged as internal capability bar. Haiku 4.6 third-party rumor flagged as unverified. **Gemini:** 3.1 Flash-Lite GA (2026-05-07, $0.25/$1.50). 3.1 Pro flagged "production-recommended but officially still Preview". Free-tier removal for Pro-tier models. **Qwen:** 3.6-27B and 3.6-35B-A3B Apache-2.0 successors. **Skills/Plugins:** frontmatter expansion; legal + small-business verticals. | OpenAI blog, Anthropic platform docs, Google Cloud blog, HuggingFace Qwen3.6 model cards, vLLM recipes, claude.com/plugins | OpenAI table reshaped - GPT-4.1 mini and o4-mini columns dropped from the primary table. "GPT-5.4" reference replaced with GPT-5.5 baseline. |
| 2026-04-19 | Anthropic table column for Claude Opus 4.7 (`claude-opus-4-7`, 1M ctx standard, 128K out, sampling params 400, adaptive-only thinking with `xhigh`, $5/$25 pricing, behavior shifts). Aliases note + Sonnet 4 / Opus 4 retirement 2026-06-15. New "Opus 4.7 specifics" block (sampling 400, `xhigh` effort, hidden thinking, +35 % tokenizer, high-res images, task budgets, prompt re-baseline). Model Selection: new "Agentic coding (hardest)" row. | Anthropic news + platform docs (Opus 4.7 release 2026-04-16), Vellum/llm-stats benchmarks, Finout pricing analysis | Opus 4.6 row relabelled "Previous gen, still supported". |
