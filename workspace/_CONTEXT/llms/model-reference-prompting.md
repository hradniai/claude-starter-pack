---
type: notes
title: "Model Reference: Per-Model Prompting, Claude Code Skills & Plugins"
status: active
summary: "How each current model wants to be prompted and called (prompt structure, request parameters, behavioral shifts, JSON, anti-patterns) plus how to build Claude Code skills and plugins. Vendor facts re-read on the vendors' own pages on 2026-10-05."
created: 2026-05-13
updated: 2026-10-05
created_by: claude-starter-pack
client: ~
path: _CONTEXT/llms/model-reference-prompting.md
tags: [note]
version: "1.0.0"
---

# Model Reference: Per-Model Prompting, Claude Code Skills & Plugins

> How each current model wants to be prompted (structure, request parameters, behavioral shifts, JSON output, anti-patterns) plus how to build Claude Code skills and plugins. Every vendor fact was re-read on the vendor's own documentation on **2026-10-05**; each provider section ends with its sources. Model IDs, prices and retirement dates live in `model-lineup.md` (same folder).
>
> Labels: **[UNVERIFIED]** = no primary page confirmed it. **[Judgment]** = this document's recommendation, not a vendor statement. **[Practice]** = a widely used technique that no vendor page cited here states.

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

**Golden rule:** if removing it makes the prompt worse, keep it; if not, cut it. All three large vendors now say the same about their current models. OpenAI: "State each instruction once." Google: "Verbose or complex prompt engineering techniques designed for older models may cause the model to over-analyze." Anthropic asks you to re-evaluate instructions written for earlier models. A prompt written for a 2026 frontier model is usually shorter than the one written for its predecessor.

### Prompt language vs output language

**The prompt body is always written in English. The output language is a constraint you state INSIDE that English prompt - it is never a reason to switch the prompt's language.** These are two independent decisions:

- **Prompt language = English, always.** Every instruction, system prompt, agent rule, classifier prompt, and inline f-string scaffold handed to an LLM is English. Reason: token cost (English usually tokenizes shorter than other languages) and consistency with the rest of the prompt tooling. This holds even when the deliverable must be in another language.
- **Output language / tone = stated explicitly in the prompt.** If the result must be Czech (or any non-English language), add one line: `"Write the output in native Czech, conversational tone"` (or commercial, formal, whatever fits). The model reads an English instruction and produces the target language.

**The trap:** conflating "the user-facing output must be Czech" with "the prompt must be Czech." Writing the prompt in the output language costs tokens and buys nothing.

**Check both surfaces:** the named prompt / template body AND any inline f-string wrappers in code that get concatenated into the message. Both are prompts; both cost tokens; both must be English.

**Output-format markers stay verbatim.** Where a parser keys on a literal marker the model must emit (`### A`, `Title:`, a JSON key), keep that marker exactly - it is a machine contract, not prose, and is independent of prompt / output language.

---

## Model comparison (October 2026)

### Anthropic / Claude

| | Claude Fable 5.1 | Claude Opus 5.5 | Claude Sonnet 5.5 | Claude Haiku 4.5 |
|---|---|---|---|---|
| **API ID** | `claude-fable-5-1` | `claude-opus-5-5` | `claude-sonnet-5-5` | `claude-haiku-4-5-20251001` |
| **Context / max output** | 1M / 128K | 1M / 128K | 1M / 128K | 200K / 64K |
| **Thinking** | Adaptive, always on | Adaptive, always on; `{"type":"disabled"}` and `budget_tokens` return 400 | Adaptive, on by default; lowest setting is `{"type":"between_tools"}` (only at effort `high` or below); `disabled` returns 400 | Extended thinking: off unless you send `{"type":"enabled","budget_tokens":N}` |
| **Effort** (`output_config.effort`) | low, medium, high, xhigh, max; default `high` | same levels; default `medium` | same levels; default `high` on the API, `medium` in Claude Code | Not supported |
| **Sampling** (`temperature`, `top_p`, `top_k`) | Non-default values return 400 | 400 | 400 | Accepted |
| **Assistant prefill** | 400 | 400 | 400 | Accepted |
| **Forced `tool_choice`** (`any`, named tool) | Error | 400 | 400 | Accepted |
| **Thinking text by default** | Omitted | Omitted | Omitted | Summarized |
| **Structured output** | `output_config.format` | same | same | same |
| **Prompt format** | XML tags | XML tags | XML tags | XML tags |
| **Best for** | Hardest reasoning, long-horizon agentic work | Default for most work, long-running agentic coding | Speed plus intelligence; most production workloads | Fastest, cheapest: routing, classification, simple subagents |

Notes:
- Anthropic's own guidance: "start with Claude Opus 5.5 for most workloads"; use Fable 5.1 "for demanding reasoning and long-horizon agentic work, or when your evals on Claude Opus 5.5 at higher effort still fall short" [A1]. For Sonnet 5.5: "For the hardest long-horizon work, an Opus model is the better choice." [A7]
- Every Claude model ID from the 4.6 generation on is a dateless pinned snapshot [A1]. The floating `opus` / `sonnet` / `haiku` aliases are a Claude Code feature (see `model-lineup.md`), not an API feature.
- The Python SDK v1.0 and later removed `temperature`, `top_p` and `top_k`; passing them raises a `TypeError` even on models that accept them [A3].
- Claude 4.7 and later use a tokenizer that produces about 30 % more tokens for the same text than earlier models [A2]: re-check `max_tokens` and cost when you move a prompt from Haiku 4.5 or Sonnet 4.6.
- Older Claude models still served behave differently: Opus 5 and Sonnet 5 accept `thinking: {"type":"disabled"}` (Opus 5 only at effort `high` or below) and forced tool choice; Opus 4.8 and 4.7 run without thinking unless asked; Sonnet 4.6 still accepts sampling parameters and the deprecated `budget_tokens` [A4, A5]. Anthropic keeps a prompting page per model, linked from [A6].

### OpenAI

| | GPT-6 Astra | GPT-6.1 Sol | GPT-6 Luna | GPT-5.6 Sol / Terra / Luna |
|---|---|---|---|---|
| **API ID** | `gpt-6-astra` | `gpt-6.1-sol` | `gpt-6-luna` | `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna` |
| **Context / max output** | 1.05M (922K max input) / 128K | same | same | same |
| **Reasoning** (`reasoning.effort`) | low, medium, high, xhigh, max; `none` returns 400; default [UNVERIFIED] | low, medium (default), high, xhigh, max; no `none` or `minimal` | none, low, medium (default), high, xhigh, max | none, low, medium (default), high, xhigh, max; `reasoning.context` defaults to `all_turns` |
| **Sampling** | Custom `temperature`, `top_p`, `logprobs` not accepted | Omit `temperature`, `top_p`, `top_logprobs` (and `logprobs` in Chat Completions) whenever effort is not `none` | same | [UNVERIFIED for 5.6] |
| **Tool calling** | Responses API only | Responses API only | Chat Completions function calling only with effort `none`; otherwise Responses | Chat Completions function tools only with effective effort `none` (the default is `medium`); reasoning with tools needs the Responses API [O9] |
| **Structured output** | Structured Outputs | same | same | same |
| **Prompt format** | Outcome-first, lean (from the GPT-5.x guides; see below) | same | same | same |
| **Knowledge cutoff** | 2026-04-30 | 2026-04-30 | 2026-05-18 | 2026-02-16 |
| **Best for** | "Most capable model for the most demanding work" | "Near-Astra performance for complex work at a lower cost" | "Most efficient model for focused, high-volume tasks" | Existing pipelines; previous generation |

Notes [O1-O4]:
- `reasoning.mode` (`standard` / `pro`) works on both GPT-6 and GPT-5.6 in the Responses API; pro mode does more work before answering, billed at the model's standard token rates [O3].
- Earlier models still on the API: GPT-5.5 (effort `none` to `xhigh`, default `medium`), GPT-5.4 and 5.4 mini (default effort `none`), GPT-4.1 and 4.1 mini (non-reasoning). `chat-latest` is "Latest Instant model used in ChatGPT" and is regularly updated, so do not pin production to it.
- The o-series is on its way out: `o3-mini` and `o4-mini` shut down 2026-10-23, the `o3` snapshot on 2026-12-11 (dates and replacements in `model-lineup.md`).
- In Codex and ChatGPT Work the effort scale runs Light to Ultra, and "Ultra uses subagents to handle separate parts of a complex task in parallel". Ultra is a product setting, not a documented `reasoning.effort` API value [O4].

### Google Gemini

| | Gemini 3.8 Flash | Gemini 3.7 Flash | Gemini 3.5 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Pro |
|---|---|---|---|---|---|
| **API ID** | `gemini-3.8-flash` | `gemini-3.7-flash` | `gemini-3.5-flash-lite` | `gemini-3.1-flash-lite` | `gemini-3.1-pro-preview` |
| **Context / max output** | 1,048,576 / 65,536 | same | same | same | same |
| **Input** | Text, image, video, audio, PDF | same | same | same | same |
| **Reasoning** (`thinking_level`) | low, medium (default), high; `minimal` returns an error | same as 3.8 | minimal (default), low, medium, high | minimal (default), low, medium, high | low, medium, high (default) |
| **Sampling** | `temperature`, `top_p`, `top_k` deprecated on all Gemini 3.x: remove them | same | same | same | same |
| **Structured output** | Native (see Gemini section) | same | same | same | same |
| **Tool calling** | `tool_choice`: auto, any, none, validated | same | same | same | same |
| **Prompt format** | Markdown or XML, one style per prompt | same | same | same | same |
| **Status** | GA 2026-09-02 | GA 2026-08-13 | GA 2026-07-21 | GA; earliest shutdown 2027-05-07 | Preview since 2026-02-19 |
| **Knowledge cutoff** | [UNVERIFIED] | [UNVERIFIED] | [UNVERIFIED] | January 2025 | January 2025 |

Notes [G1-G5]:
- The January 2025 cutoff for the 3.1 models is stated only on Google's Gemini 3 developer guide, which Google marks as deprecated [G10].
- Also live: Gemini 3.6 Flash and 3.5 Flash (both accept `minimal`, default `medium`; 3.5 Flash knowledge cutoff January 2025) and `gemini-3-flash-preview` (default `high`; Google names 3.6 Flash as its replacement).
- Two APIs coexist: "While generateContent remains fully supported, we recommend the Interactions API for all new development." Google also recommends the `google-genai` SDK v2.0.0 or later [G2].
- Gemini 4 Argon (announced 2026-09-30) is restricted to selected security teams and has no API model ID yet; see `model-lineup.md`.

### Perplexity (search-augmented generation)

A different category from the models above: the model searches the live web and answers with citations.

**Status change.** Perplexity moved Sonar Chat Completions onto its Agent API in July 2026 [P5], and "Sonar Chat Completions support ended on September 27, 2026." Synchronous and streaming Sonar requests still work because Perplexity is reformulating them as Agent API requests, model by model; asynchronous Sonar requests (the old `sonar-deep-research` async endpoint) are no longer supported. Perplexity recommends "Using the Agent API for all new projects." [P1]

- **Agent API (current):** `POST /v1/agent` with a `preset` (`fast`, `low`, `medium`, `high`, `xhigh`) instead of a model name; `messages` becomes `input`. Presets are dynamic: the model behind each one changes over time. If you need stable behavior, Perplexity suggests a frozen configuration made by copying the current preset values inline [P3]. Perplexity's starting mapping: `sonar` and `sonar-pro` -> `fast`, `sonar-reasoning-pro` -> `low`, `sonar-deep-research` -> `high`; `xhigh` for "state-of-the-art deep research" [P1, P2]. Fees: `web_search` $2.50 per 1,000 calls ($1.00 with `search_type: "fast"`), `fetch_url` $0.0005 per call, model tokens billed separately [P4].
- **Legacy Sonar (existing customers):** `sonar` (128K, $1 / $1 per 1M tokens), `sonar-pro` (200K, $3 / $15, "2x more search results than standard Sonar"), `sonar-reasoning-pro` (128K, $2 / $8), `sonar-deep-research` (128K, $2 / $8 plus citation and reasoning tokens and $5 per 1,000 searches); each call except deep research also pays a per-request search fee of $5-$14 per 1,000 depending on model and context size. `sonar-reasoning` (without `-pro`) was removed on 2025-12-15 [P4, P5; per-model pages such as https://docs.perplexity.ai/docs/legacy/sonar/models/sonar-pro.md].

### Qwen (open weights, self-hosted)

| Model | Released | Size | Context | License | Notes |
|---|---|---|---|---|---|
| Qwen3.8-27B | 2026-08-14 | 27B dense | 262,144 native, up to 1,000,000 with YaRN | Apache 2.0 | Text, image, video input; thinking on by default |
| Qwen3.8-2.4T-A95B | 2026-08-12 | 2.4T total, 95B active (MoE) | 262,144 native, extensible | Custom "Qwen3.8-Max License" | Text only; thinking cannot be disabled |
| Qwen3.8-Flash-Next | 2026-08-26 | 125B total, 6B active (MoE), plus a 51B n-gram embedding and a 4B MTP module: about 176B to host, 335 GiB in BF16 | 262,144 native, up to 1,000,000 | Custom "Qwen Community License 1.0" | Multimodal; "an early preview of the architecture used in Qwen4" [Q6] |
| Qwen3.6-27B / 3.6-35B-A3B | 2026-04-22 / 2026-04-16 | 27B dense / 35B total, 3B active | 262,144 native, up to 1,010,000 | Apache 2.0 | Thinking on by default |
| Qwen3.5 family | 2026-02 / 2026-03 | 397B-A17B, 122B-A10B, 35B-A3B, 27B, 9B, 4B, 2B, 0.8B | 262,144 native; up to 1,010,000 from 4B up | Apache 2.0 | 2B and 0.8B default to non-thinking [Q7] |

Notes [Q1-Q4]:
- No Qwen3.7, Qwen3.9 or Qwen4 open-weight release exists on Hugging Face or GitHub as of 2026-10-05; Qwen3.7-Plus appears only as a model name in Qwen's benchmark tables, with no open weights.
- The two custom licenses are not Apache 2.0. The Community License requires a separate license from Qwen for a "Model as a Service or AI Work Assistant business" (internal use is exempt); read the license before you resell inference or build an assistant product on these weights.

### Sources: model comparison

Read 2026-10-05.
- [A1] Claude models overview: https://platform.claude.com/docs/en/models/overview
- [A2] Claude pricing (tokenizer note): https://platform.claude.com/docs/en/about-claude/pricing
- [A3] Claude model deprecations (API parameter deprecations): https://platform.claude.com/docs/en/about-claude/model-deprecations
- [A4] Migrating to Claude Opus 5.5: https://platform.claude.com/docs/en/models/opus-5-5/migration-guide
- [A5] Migrating to Claude Sonnet 5.5: https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide
- [A6] Claude prompting best practices: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- [A7] Prompting Claude Sonnet 5.5: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5
- [A8] Claude Fable 5.1 overview: https://platform.claude.com/docs/en/models/fable-5-1/overview
- [O1] OpenAI models: https://developers.openai.com/api/docs/models (per model: https://developers.openai.com/api/docs/models/gpt-6.1-sol and siblings)
- [O2] OpenAI GPT-6 guide: https://developers.openai.com/api/docs/guides/latest-model
- [O3] OpenAI reasoning guide: https://developers.openai.com/api/docs/guides/reasoning
- [O4] Codex models: https://learn.chatgpt.com/docs/models
- [G1] Gemini models: https://ai.google.dev/gemini-api/docs/models (per model: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash and siblings)
- [G2] What's new in Gemini 3.5 (baseline guide for all 3.x): https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.5 ; migrate to Interactions: https://ai.google.dev/gemini-api/docs/migrate-to-interactions
- [G3] Gemini thinking: https://ai.google.dev/gemini-api/docs/thinking
- [G4] Gemini deprecations: https://ai.google.dev/gemini-api/docs/deprecations
- [G5] Gemini changelog: https://ai.google.dev/gemini-api/docs/changelog
- [P1] Perplexity, migrate from Sonar: https://docs.perplexity.ai/docs/agent-api/migrate-from-sonar/overview.md
- [P2] Perplexity migration how-to: https://docs.perplexity.ai/docs/agent-api/migrate-from-sonar/how-to.md
- [P3] Perplexity presets: https://docs.perplexity.ai/docs/agent-api/presets.md
- [P4] Perplexity pricing: https://docs.perplexity.ai/docs/getting-started/pricing.md
- [P5] Perplexity legacy Sonar models: https://docs.perplexity.ai/docs/legacy/sonar/models.md ; changelog: https://docs.perplexity.ai/docs/resources/changelog.md
- [Q1] Qwen3.8-27B card: https://huggingface.co/Qwen/Qwen3.8-27B ; Qwen3.8-2.4T-A95B: https://huggingface.co/Qwen/Qwen3.8-2.4T-A95B
- [Q2] Qwen3.8-Flash-Next card: https://huggingface.co/Qwen/Qwen3.8-Flash-Next ; license: https://huggingface.co/Qwen/Qwen3.8-Flash-Next/raw/main/LICENSE
- [Q3] Qwen3.6 cards: https://huggingface.co/Qwen/Qwen3.6-27B , https://huggingface.co/Qwen/Qwen3.6-35B-A3B ; Qwen3.5: https://huggingface.co/Qwen/Qwen3.5-397B-A17B
- [Q4] Qwen GitHub release list: https://github.com/QwenLM/Qwen3.8
- [Q6] Qwen3.8-Flash-Next GitHub: https://github.com/QwenLM/Qwen3.8-Flash-Next
- [Q7] Qwen3.5-2B card: https://huggingface.co/Qwen/Qwen3.5-2B

---

## Per-model prompting guide

### Anthropic Claude (Fable 5.1 / Opus 5.5 / Sonnet 5.5 / Haiku 4.5)

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
- Use null for missing values. Never fabricate - the output feeds a production database.
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
```
For production JSON, enforce the schema with structured outputs instead of relying on the `<output_format>` line (see JSON Output below).

**Core tips (all current Claude models) [A6]:**
- **Be clear and direct.** "Think of Claude as a brilliant but new employee who lacks context on your norms and workflows." Golden rule: "Show your prompt to a colleague with minimal context on the task and ask them to follow it. If they'd be confused, Claude will be too."
- **Explain why.** "Your response will be read aloud by a text-to-speech engine, so never use ellipses" works better than "NEVER use ellipses": "Claude is smart enough to generalize from the explanation."
- **Examples** are "one of the most reliable ways to steer Claude's output format, tone, and structure." Make them relevant, diverse, wrapped in `<example>` / `<examples>` tags; 3-5 is the recommended count.
- **XML tags** separate instructions, context, examples and variable inputs; use consistent, descriptive tag names and nest them when content is hierarchical.
- **Purpose before role.** Anthropic notes that even a one-sentence role in the system prompt focuses behavior and tone; state the goal first and add a role only if it changes the output. [Practice for the ordering]
- **Long documents go at the top, the question at the end.** "Queries at the end can improve response quality by up to 30 percent in tests, especially with complex, multidocument inputs."
- **Say what to do, not what not to do.** "Your response should be composed of smoothly flowing prose paragraphs" beats "Do not use markdown".
- **Ask for action explicitly.** "Can you suggest some changes" gets suggestions; "Change this function to improve its performance" gets changes.
- **Calm language, no shouting.** Current models are responsive to the system prompt and overtrigger on aggressive wording: "Where you might have said 'CRITICAL: You MUST use this tool when...', you can use more normal prompting like 'Use this tool when...'."
- **Re-baseline prompts written for older models.** Anthropic: "If your prompts previously encouraged the model to be more thorough or use tools more aggressively, dial back that guidance." Remove scripted chain of thought ("think step by step": rely on thinking and effort instead) and forced progress-summary scaffolding, then add back only what your evals show is needed.
- **Keep explicit verification criteria.** Anthropic: "Append something like 'Before you finish, verify your answer against [test criteria].' This catches errors reliably, especially for coding and math." The exceptions are Opus 5, where carried-over verification instructions "can cause over-verification", and Fable in Claude Code [C1].
- **Repeat the critical constraint at the end of a long prompt.** [Practice]
- **No prefill.** Starting the assistant turn with `{` returns 400 on Claude 4.6 and later; use structured outputs. Haiku 4.5 still accepts prefill.

**Request rules shared by Fable 5.1, Opus 5.5 and Sonnet 5.5 [A4, A5, A6]:**
1. **Thinking runs on (almost) every request**, and `max_tokens` is a hard limit on thinking plus answer. Thinking tokens bill as output even when hidden. For agentic coding, Anthropic recommends `max_tokens` 128,000 with streaming on Sonnet 5.5 and reports that 128,000 "has worked well" on Opus 5.5 [A7, A9].
2. **Read content blocks by `type`.** A response can start with `thinking` blocks, so `content[0].text` breaks.
3. **Return thinking blocks unchanged in tool loops**, including empty ones. Edited, reordered or partly dropped blocks return 400.
4. **Keep the conversation append-only.** Editing earlier turns, the system prompt or the tool list invalidates earlier thinking blocks. For accounts created on or after 2026-08-31 such a request fails by default (you can opt into dropping the affected blocks instead); older accounts should still make history append-only [A13]. Change instructions with a mid-conversation `role: "system"` message instead.
5. **Thinking text is omitted by default** (`display: "omitted"`). Set `display: "summarized"` to read summaries. The notes the model writes between tool calls now come back as `thinking` blocks instead of `text` (on Sonnet 5.5 only notes longer than a sentence or two; shorter remarks stay `text`); set `display: "updates"` (beta header `thinking-display-updates-2026-08-18`) or your UI goes quiet during long agentic turns.
6. **No forced tool choice.** Use `tool_choice: {"type":"auto"}` plus strict tools or structured outputs.
7. **No sampling parameters, no prefill, no `budget_tokens`.** Steer with the prompt and `effort`.
8. **Set `effort` explicitly and re-run an effort sweep** instead of carrying over a level tuned for an older model: level names do not mean the same amount of thinking across models. To lower thinking, lower effort; prompt instructions do it less reliably. Changing top-level effort mid-session invalidates the prompt cache; use per-message effort (beta header `mid-conversation-output-config-2026-07-01`) instead.
9. **Handle refusals.** Safety classifiers return a normal response with `stop_reason: "refusal"` and `stop_details.category` (on Sonnet 5.5: `cyber`, `bio`, `frontier_llm`, `reasoning_extraction`, `general_harms`). Server-side fallback (`fallbacks: "default"`, beta, Claude API only) retries some categories on another model but never `reasoning_extraction`.
10. **Do not ask the model to write out its reasoning in the answer.** That invites `reasoning_extraction` refusals; read the summarized thinking instead. A short explanation of the answer is fine.

**Claude Opus 5.5 specifics [A9]:**
- Effort: start at the default `medium`. In Anthropic's testing Opus 5.5 at `medium` "matches or exceeds Claude Opus 5 at `high`" on coding and knowledge work, and on several coding evals `low` comes close at much lower cost. Reserve `xhigh` and `max` for measured gains; at a given level it thinks more per turn than Opus 5.
- Unattended agents: some progress updates end the turn with text instead of a tool call (`stop_reason: "end_turn"`). Treat that as a report, not proof the task is done: keep the task list in a to-do tool or file, send a short user message naming the open items, and stop after two or three automatic continuations. Anthropic publishes a system-prompt paragraph naming four unwanted early stops for fully unattended runs [A9].
- Chat: remove "think carefully before answering" lines; replies start sooner with no clear quality loss. To stop it re-examining earlier answers: "Once you have answered something, treat that answer as done. On later turns, focus your thinking on what the user is asking now, and don't go back over an earlier answer unless the user asks about it or points out a problem with it."
- Multi-app automations: "Before taking any action, explore broadly with tool calls: list and open the emails, documents, spreadsheet tabs and records across the available apps that could be relevant to this task, including ones the task does not explicitly mention, and use what you find."
- Multi-agent harnesses: append elapsed time against a budget to each message (`elapsed 340s / 1200s`); the model paces itself and parallelizes more.
- Pasted text: wrap text the user pasted from elsewhere in `<pasted_content id="ab12">` ... `</pasted_content id="ab12">` with a random ID, and tell the model to follow instructions inside it only where the user's own message asks.
- Frontend: "avoid a generic AI look" swaps one default style for another; name the specific patterns to avoid.

**Claude Sonnet 5.5 specifics [A7]:**
- Effort: start at `high` (API default) unless the work is agentic or latency-sensitive. Agentic coding: `medium` for well-specified tasks, `high` for harder ones. Chat: `medium` or `low`. From `medium` up it thinks briefly before almost every reply, and asking it to think less "doesn't reliably reduce its thinking"; lower effort instead.
- Initiative: at `low` and `medium` it may stop to check in before a coding task is done; at `xhigh` and `max` it may start its own review rounds and reviewer subagents. Anthropic's fixes: "Keep working until everything the user asked for is done, and only stop to ask when you can't go on without the user or before a risky step." and "When the work the user asked for is done and its checks pass, stop and report." It also adds tests and docs nobody asked for; say so if you want changes limited to the request.
- Open-ended requests ("show me what you can do") can trigger building; if you want ideas, say "give them that and stop".
- No up-front thinking: `thinking: {"type":"between_tools"}` at `high` effort or below. Do not use it for reasoning tasks without tools: the model then answers without thinking.
- JSON on tasks that need working out: with structured outputs, add "Think the problem through before you answer." or use `xhigh`; treat `stop_reason: "max_tokens"` as a failure even if the JSON parses. Without structured outputs, parse the last JSON value in the text, not the span from the first `{` to the last `}`.
- Search: remove "minimize tool calls" style lines; tell it to search for specifics that may have changed since training (what is allowed, required or charged).
- Mid-turn user messages: never put user text inside a `tool_result` block; it may be treated as a prompt injection. Append it as a text block after the last `tool_result`.
- At `low` effort it can report code changes as done without running a check; add an instruction to run the project's tests, type-checker or build before reporting.
- It occasionally calls a tool with the wrong letter case; accept unambiguous matches or return `is_error: true` with the exact expected name.

**Claude Fable 5.1 specifics [A8, A10]:**
- Start at `high` (default) and test every level: at `medium` it roughly matches Fable 5 at lower cost, and at `low` it "is often competitive with Claude Opus and Claude Sonnet models on cost per task while scoring higher".
- It writes fewer progress updates than Fable 5. Remove lines like "hold all findings for the final response" before adding a short request for updates.
- In coding and computer-use loops it may issue one tool call per turn; Anthropic's nudge: "First privately list what you need next; then request every item that doesn't depend on another's result in this one response."
- Prose can run dense: "Please remove all mannered prose." It also formats less than earlier models; drop old anti-formatting rules.
- For long autonomous work, Anthropic publishes a system-prompt block that opens "You are operating autonomously. The user is not watching in real time and cannot answer questions mid-task" [A10]; it stops the model asking permission for work already requested.
- At `low` effort it searches less; tell it that recognizing a name from a fast-moving area is a reason to search, not to skip searching.
- Fewer false-positive refusals than Fable 5, but ask "Are there any bugs in this program?" rather than "Does this program compile without errors?", and keep base64 out of tool output.
- Fable 5.1 is a "Covered Model": it requires 30-day data retention and is unavailable under zero data retention unless Anthropic authorizes it [A11].
- In Claude Code, Anthropic's advice for Fable: "Describe the outcome, not the steps" and "Skip the verification reminders: it verifies its own work with less prompting" [C1].

**Claude Haiku 4.5 specifics [A1, A5, A12]:**
- Older request surface: no effort parameter, extended thinking only when you request a `budget_tokens` budget, sampling parameters and prefill still accepted, minimum cacheable prompt 4,096 tokens, 200K context.
- Give it more detail than you would give Opus. Anthropic on skills: "What works perfectly for Opus might need more detail for Haiku."
- Its retirement floor is 2026-10-15 (no deprecation announced as of 2026-10-05); see `model-lineup.md`.

**Server tools and caching [A2 for prices, A4 and A5 for cache minimums]:**
- Web search `web_search_20260209` ($10 per 1,000 searches) and web fetch `web_fetch_20260209` (no fee beyond tokens); code execution is free when used together with either.
- Prompt caching: add one top-level `cache_control` field for automatic caching, or place `cache_control` on individual blocks; check `usage.cache_read_input_tokens` to confirm hits. Minimum cacheable prompt: 512 tokens on Opus 5.5 and Sonnet 5.5, 4,096 on Haiku 4.5.

**Low-code tools (n8n and similar):** prefer the node's structured-output setting over prompt-only JSON, and check that the node actually exposes `effort` and the thinking settings above before relying on them. [Judgment]

### OpenAI GPT-6 (Astra / 6.1 Sol / Luna) and GPT-5.6

OpenAI has no standalone GPT-6 prompting guide. The GPT-6 guide covers request changes plus a "Prompting best practices" section of starter prompts written for Astra; the outcome-first, lean-prompt advice below comes from the GPT-5.6 and GPT-5.5 guides, and carrying it to GPT-6 is an assumption [O2, O5, O6].

**Prompt structure**: outcome-first. Describe what good looks like, success criteria, evidence rules and output shape; avoid step-by-step process unless the path matters. OpenAI's suggested sections: Role, Personality, Goal, Success criteria, Constraints, Tools, Output, Stop rules [O5].
```markdown
# Goal
Decide whether the supplied invoice should be auto-approved.

# Success criteria
- Approve only if total <= budget AND vendor is on the approved list.
- If any required field is missing or ambiguous, return REVIEW with the reason.

# Evidence
Cite the exact field values you used in your decision.

# Output
JSON: { "decision": "APPROVE | REVIEW | REJECT", "reasoning": "...", "fields_used": {...} }
```

**Tips:**
- "GPT-5.6 works best when prompts define the outcome, important constraints, available evidence, and completion bar, then leave room for the model to choose an efficient path." [O5]
- **Lean prompts.** "State each instruction once." OpenAI reports roughly 10-15 % better eval scores with 41-66 % fewer tokens after removing repeated instructions and examples, in an internal sample it calls "directional" [O6].
- **Effort is a tuning knob, not the quality lever.** "Treat `reasoning.effort` as a tuning knob, not the primary way to recover quality." [O3] "Before increasing reasoning effort, check whether the prompt is missing a success criterion, dependency rule, tool-routing rule, or verification loop." [O5] Start at `medium`, use `low` for latency-sensitive work, reserve `max` for the hardest quality-first jobs. Migrating from 5.5 or 5.4: keep your current effort as the baseline, then compare one level lower [O6]. Astra and 6.1 Sol reject `none`; use `low` [O2].
- **Verbosity:** set `text.verbosity` (`low` / `medium` / `high`) for the default level of detail and use the prompt for task-specific requirements [O5]. Astra "tends to use lists, tables and Markdown"; ask for prose if you need it [O2].
- **Use the Responses API** ("Reasoning models work better with the Responses API.") and continue with `previous_response_id` so earlier reasoning stays available [O3, O7]. Use `instructions` for high-level behavior: "Any instructions provided this way will take priority over a prompt in the `input` parameter." [O8]
- **Autonomy.** Astra "is also more likely to ask for clarification where earlier models would make assumptions." OpenAI's starter line: "Your job is to bias towards action and carry the user's intended task to completion." [O2] For GPT-5.6, define which actions each request authorizes: report-only for questions, in-scope work plus validation for change requests, confirmation before external writes, destructive actions, purchases or scope expansion [O5].
- **Audit skills and `AGENTS.md`.** Astra "can be more sensitive to instructions contained in skills and other files, such as `AGENTS.md`"; OpenAI "strongly recommend[s]" auditing every file the model can read [O2].
- **Preambles, not narration.** "For multi-step or tool-heavy tasks, prompt for a short visible preamble before the first tool call, then sparse outcome-based updates at major phase changes. Do not ask the model to narrate routine tool calls." [O5]
- **`phase`** (documented for GPT-5.4, 5.5 and 5.6; no GPT-6 page mentions it). Mark intermediate assistant updates `phase: "commentary"` and the final answer `phase: "final_answer"`; when you replay history yourself, keep each original `phase` value [O3, O5].
- **Constraint language.** "Use ALWAYS, NEVER, must, and only for true invariants such as safety rules, required fields, or actions that should never happen. For judgment calls, ... prefer decision rules." Repeated "ask first" / "wait for approval" lines cause needless approval requests, and "conflicting rules can create more instability than missing detail." [O5]
- **Few-shot.** "Keep examples and style guidance when they encode a product requirement or correct a measured gap"; drop examples that do not change behavior [O6].
- **Drop old scaffolding.** No "think step by step", no current date ("The model is already aware of the current UTC date."), no output schema in the prompt where Structured Outputs can enforce it [O7].
- **Request changes for GPT-6:** whenever effort is not `none`, remove `temperature`, `top_p` and `top_logprobs`, plus `logprobs` in Chat Completions and `message.output_text.logprobs` from `include` in Responses; change effort mid-conversation with a `configuration_update` input item so the cached prefix survives; replace `prompt_cache_retention` with `prompt_cache_options.ttl: "30m"` [O2].
- **Pro mode (GPT-5.6 and GPT-6):** `reasoning.mode: "pro"` does more work before answering at standard token rates; "You do not need to ask the model to 'use pro mode,' 'think harder'..." On GPT-5.6, `reasoning.context` defaults to `all_turns` [O3, O6].

**Older OpenAI models (still on the API):**
- GPT-5.5: same outcome-first style; works best in the Responses API with `previous_response_id`; effort `none` to `xhigh` [O7].
- GPT-4.1 / 4.1 mini (non-reasoning): Markdown headers (`# Purpose / # Instructions / # Constraints / # Examples / # Output Format`), 3-5 few-shot examples, `temperature: 0` for deterministic extraction, and an explicit "no markdown, no code fences" line when you prompt for raw JSON. [Practice]
- o3 / o4-mini / o3-mini: shutting down (2026-10-23 and 2026-12-11); migrate rather than tune prompts.

### Google Gemini 3.x

**Prompt structure**: Markdown headings or XML-style tags; "Choose one format and use it consistently within a single prompt." Put role, critical constraints and output format in the system instruction or at the very start [G6].
```markdown
# Task
Extract product information from the text below.

# Output
JSON with fields: name (string), price (number), currency (string),
category (one of: electronics, clothing, food, other).
If a field cannot be determined, return null for that field.

# Text
{{input}}

Based on the text above, return the JSON.
```

**Tips [G2, G6]:**
- **Be concise.** "Gemini 3.x responds best to direct, clear instructions. Verbose or complex prompt engineering techniques designed for older models may cause the model to over-analyze."
- **Short answers by default.** "If you need a more conversational or detailed response, you must explicitly request it in your instructions."
- **Context first, question last.** "Place your specific instructions or questions at the end of the prompt, after the data context," anchored with "Based on the preceding information...".
- **Date and cutoff hygiene.** Under "Gemini 3 Flash strategies" Google suggests system-instruction lines such as "Remember it is 2026 this year." and "Your knowledge cutoff date is January 2025." Use the cutoff line only for models where Google states that cutoff (3 Flash, 3.5 Flash and the 3.1 models); use Search grounding for anything newer.
- **No scripted chain of thought.** Use `thinking_level` instead; "simple requests like 'Think very hard before answering' can improve performance, though at the cost of extra thinking tokens." Use the lowest level for retrieval and classification (`minimal` where supported; `low` on 3.7 and 3.8 Flash, which reject `minimal`), higher levels for coding, math and multi-step planning [G3].
- **Too many tool calls?** Lower the thinking level first; then add "You have a limited action budget of <n> tool calls. Use them efficiently." [G2]
- **Agents.** Google publishes a tested agentic system-instruction template that begins "You are a very strong reasoner and planner." and covers decomposition, persistence, risk assessment and when to ask versus assume [G6].
- **3.8 Flash uses more tokens on long tasks by design**; lower the thinking level for everyday work, or stay on 3.7 Flash [G7].
- The general section of Google's prompting-strategies page still says "always include few-shot examples", while its Gemini 3 sections stress concise prompts. For 3.x, keep examples only where they change the output. [Judgment]

**Sampling parameters:** do not set `temperature`, `top_p` or `top_k` on Gemini 3.x. The changelog (2026-07-21) calls them deprecated and the 3.8 Flash guide says "Strip temperature, top_p, and top_k from generation configs" [G5, G7]; the 3.x baseline guide calls them "no longer recommended" and says "Remove these parameters from all requests", while the same guide and the prompting-strategies page also say to keep their default values [G2, G6]. Either way, leave them out; for determinism Google recommends explicit rules in the system instruction [G2]. Whether sending them returns an error or is ignored is not documented [UNVERIFIED].

**Thinking:** `thinking_level` is the control on 3.x. Sending it together with the legacy `thinking_budget` returns 400. `max_output_tokens` counts thinking tokens: to cut cost or latency, lower `thinking_level` instead of setting a small `max_output_tokens`, which can truncate the answer [G2, G3].

**Structured output [G8, G11]:**
- Interactions API: `response_format: {"type": "text", "mime_type": "application/json", "schema": {...}}`. `response_mime_type` was removed from this API.
- generateContent: JSON MIME type plus a JSON Schema; current Google pages show both `response_schema` and `response_json_schema`, so check the page for your SDK version [UNVERIFIED which is canonical].
- Classification: use a JSON Schema `enum` on a string property. (The older `text/x.enum` response type is no longer documented.)
- "Very large or deeply nested schemas may be rejected." and "While output is syntactically correct JSON, always validate values in your application."

**Function calling [G9, G2]:** `tool_choice` takes `auto` (default), `any`, `none` or `validated` (the model is held to the function schema) [G9]. Function-response `id`, name and count must match the preceding calls [G2]. In long agentic sessions `auto` can skip tool calls; switch to `any` when a call must happen. [Practice for the long-session note]

**Thought signatures [G3, G2]:** in the stateful Interactions mode (`store: true` plus `previous_interaction_id`) the server handles them. Stateless: "You MUST always resend all thought blocks exactly as they were received from the model." [G3] The official SDKs do this when you pass the full, unmodified history [G2].

**Multimodal:** Gemini takes text, image, video, audio and PDF in one request; Google documents strengths in long-document, chart and table understanding. Google publishes no head-to-head vision comparison against Claude or GPT, so test on your own inputs. [Judgment]

### Perplexity

Rules from Perplexity's prompt guides [P6, P7]:
- **Do not instruct it to search.** On legacy Sonar this does nothing: "Do not put search instructions in the system prompt. Phrases like 'search only on Wikipedia' or 'look for the latest results' have no effect." On Sonar "only the user message is used to drive that search." On the Agent API, `instructions` apply on every turn and can nudge the built-in tools, but it is rarely needed: built-in tools "are tuned to work well without prompt-side guidance".
- **Filters belong in parameters, not prose:** `search_domain_filter` (allowlist, or denylist with a `-` prefix, up to 20 entries), `search_recency_filter` (`hour`, `day`, `week`, `month`, `year`), date filters. On the Agent API they sit in the `web_search` tool's `filters` [P2, P8].
- **Be specific; cap lists.** "If you want a list, say how long."
- **Read sources from the `search_results` field**, never from URLs the model wrote in prose. (Perplexity's changelog says the older `citations` field "has been fully deprecated and removed" [P5].)
- **Few-shot the structure, not the content:** a written-out example answer can pull the search toward the example topic.
- **Agent API presets:** "Setting `instructions` with a preset replaces the preset's system prompt - it does not append."
- **Structured output:** `response_format` with `json_schema`; on the Agent API it is not restricted to specific models [P2], and the first request with a new schema can take 10-30 seconds [P9]. On legacy `sonar-reasoning-pro` a `<think>` block precedes the JSON, so strip it before parsing; the Agent API emits no think tags [P5, P9].
- Use it for answers that depend on current information. Do not use it for extraction from documents you already have, deterministic classification, or anything where an unsupported claim is unacceptable. [Judgment]

### Qwen (self-hosted)

Qwen's model cards give sampling and thinking control but no prompt-writing guide [Q1-Q3]. Markdown headers plus one realistic example work well in practice. [Practice]

- **Thinking control:** thinking is on by default (Qwen3.5-2B and 0.8B start in non-thinking mode). Turn it off per request with `"chat_template_kwargs": {"enable_thinking": false}` on vLLM or SGLang; Qwen3.8-2.4T-A95B is the exception, where thinking cannot be disabled. The `/think` and `/nothink` soft switch from Qwen3 (2025) is not supported on Qwen3.5 and 3.6.
- **Qwen3.8 adds** `reasoning_effort` (`xhigh` default, `medium`, `low`) and turns `preserve_thinking` on by default (it keeps thinking from earlier turns, useful for agents). Qwen3.6 has the same flag, off by default.
- **Sampling** (from the cards): Qwen3.8 and 3.6 thinking mode `temperature=1.0, top_p=0.95, top_k=20`; for precise coding on 3.5 / 3.6, `temperature=0.6`. Non-thinking mode `temperature=0.7, top_p=0.8, top_k=20, presence_penalty=1.5`. Raise `presence_penalty` (0-2) against endless repetition, at some risk of language mixing. Support for these parameters "varies according to inference frameworks".
- **Output budget:** for frameworks that support separate limits for reasoning and answer, the Qwen3.8 cards suggest up to 262,144 tokens for reasoning and 131,072 for the final answer (within the YaRN-extended 1M context); for Qwen3.5 / 3.6 keep the context at least 128K "to preserve thinking capabilities".
- **vLLM:** `--reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser qwen3_coder`. The Qwen3.6 cards recommend vLLM 0.19.0 or later and the Qwen3.8 cards "the latest framework versions"; Flash-Next needs vLLM 0.29.0+ from a dedicated Docker image per the vLLM recipe [Q3, Q5].
- **1M context** uses static YaRN, which "potentially impact[s] performance on shorter texts"; enable it only when you need the long context.

### Sources: per-model prompting

Read 2026-10-05 (keys [A1]-[A8], [O1]-[O4], [G1]-[G5], [P1]-[P5], [Q1]-[Q4] are listed under the model comparison).
- [A9] Prompting Claude Opus 5.5: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
- [A10] Prompting Claude Fable 5.1: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1
- [A11] Claude API and data retention: https://platform.claude.com/docs/en/manage-claude/api-and-data-retention
- [A12] Skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- [A13] Preserved thinking: https://platform.claude.com/docs/en/build-with-claude/preserved-thinking
- [C1] Claude Code model configuration: https://code.claude.com/docs/en/model-config
- [O5] OpenAI prompt guidance for GPT-5.6: https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6#prompting-best-practices
- [O6] OpenAI GPT-5.6 guide: https://developers.openai.com/api/docs/guides/latest-model/gpt-5.6
- [O7] OpenAI GPT-5.5 guide: https://developers.openai.com/api/docs/guides/latest-model/gpt-5.5
- [O8] OpenAI prompt engineering: https://developers.openai.com/api/docs/guides/prompt-engineering
- [O9] Upgrading to GPT-5.6 Sol: https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6#migrate-to-gpt-56
- [G6] Gemini prompting strategies: https://ai.google.dev/gemini-api/docs/prompting-strategies
- [G7] What's new in Gemini 3.8 Flash: https://ai.google.dev/gemini-api/docs/latest-model
- [G8] Gemini structured output: https://ai.google.dev/gemini-api/docs/structured-output
- [G9] Gemini function calling: https://ai.google.dev/gemini-api/docs/function-calling
- [G10] Gemini 3 developer guide (marked deprecated by Google): https://ai.google.dev/gemini-api/docs/gemini-3
- [G11] Interactions API breaking changes: https://ai.google.dev/gemini-api/docs/interactions-breaking-changes-may-2026
- [P6] Perplexity Sonar prompt guide: https://docs.perplexity.ai/docs/legacy/sonar/prompt-guide.md
- [P7] Perplexity Agent API prompt guide: https://docs.perplexity.ai/docs/agent-api/prompt-guide.md
- [P8] Perplexity Sonar search filters: https://docs.perplexity.ai/docs/legacy/sonar/filters.md
- [P9] Perplexity output control: https://docs.perplexity.ai/docs/agent-api/output-control.md ; sonar-reasoning-pro: https://docs.perplexity.ai/docs/legacy/sonar/models/sonar-reasoning-pro.md
- [Q5] vLLM recipes: https://recipes.vllm.ai/Qwen/Qwen3.8-27B , https://recipes.vllm.ai/Qwen/Qwen3.8-Flash-Next

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
EXAMPLE:      [Realistic input -> expected output]
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
-> IF message contains ["urgent", "critical", "down"]: HIGH priority
-> ELSE: MEDIUM priority

Action: search_kb(query=customer_message)
-> IF confidence > 0.8: Provide answer
-> IF confidence 0.5-0.8: Provide answer + flag for review
-> IF confidence < 0.5: Escalate to human

Errors:
-> search_kb timeout: Retry once -> if still fails, escalate
-> search_kb 500: Use cached response from last 24h
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
* 404: Customer not found -> Ask user to confirm ID
* 500: Server error -> Use cached data if available, else escalate
* rate_limit: Wait 2s -> Retry once
```

A prescriptive `Purpose` + `DO NOT use for:` per tool is the most direct fix for wrong-tool selection. Write it as a plain "Use this tool when..." trigger, not in capitals: current Claude models overtrigger on aggressive wording [A6], and OpenAI likewise asks for decision rules instead of absolutes [O5].

**Error handling pattern:**

```
Call: payment_api.process(order_id, amount)
-> SUCCESS: Validate response.transaction_id exists -> Confirm to user
-> TIMEOUT: Retry once after 5s -> If fails, flag as "pending manual check"
-> 400: Parse error_code from response -> Show user-friendly message
-> 500: Wait 30s -> Retry -> If fails, add to retry queue
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

On current Claude models, "prune conversation history" must not edit turns that precede a thinking block (see the Claude request rules); summarize into a new message or use the provider's compaction feature instead.

---

## JSON Output

### 1. Schema first

Define the schema in the prompt; include one example covering the key case.

```
Return ONLY valid JSON matching this schema - no markdown, no code blocks:
{
  "topics": [
    {
      "name": "string (3-50 chars)",
      "priority": "integer 1-5",
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

### 5. Provider-specific enforcement

Prefer API-level enforcement over prompting wherever it exists - it is strictly more reliable than asking nicely. Validate values in your code either way.

| Provider | Best practice |
|---|---|
| Claude (current) | `output_config.format` (JSON schema) on `messages.create()`, or `client.messages.parse()` with a Pydantic / Zod model [A4]. Prefill is gone on Claude 4.6+ [A6]. For answers that need working out, see the Sonnet 5.5 JSON notes above [A7]. |
| OpenAI (GPT-6, GPT-5.x) | Structured Outputs with a JSON Schema; OpenAI asks you to remove schema definitions from the prompt where Structured Outputs can enforce them [O7]. |
| Gemini 3.x | `response_format.schema` (Interactions API) or JSON MIME type plus schema (generateContent); `enum` for classification [G8]. |
| Perplexity | `response_format` with `json_schema`; strip the `<think>` block on `sonar-reasoning-pro` [P9]. |
| Self-hosted (vLLM, Qwen) | Use the server's structured-output / guided-decoding feature; parameter names differ between vLLM versions, so check the docs for yours [UNVERIFIED]. |

---

## Model Selection by Task

Starting points, cheapest sensible option first, as of 2026-10-05. Prices and limits are in `model-lineup.md`; validate any pick on 20-50 of your own samples before production. [Judgment]

| Task | Start with | Step up to | Why |
|---|---|---|---|
| Simple extraction, classification, routing | GPT-6 Luna (`low` effort), Gemini 3.1 Flash-Lite / 3.5 Flash-Lite | Claude Haiku 4.5, Gemini 3.8 Flash, Claude Sonnet 5.5 (`low`) | Cheapest current tiers; enforce the schema at the API |
| Complex extraction (OCR, messy documents) | Gemini 3.8 Flash | Claude Sonnet 5.5, GPT-6.1 Sol | Gemini takes PDF, image and audio natively; escalate on measured misses |
| Agent with a few tools | Claude Sonnet 5.5 (`medium`), GPT-6.1 Sol (`medium`) | Claude Opus 5.5 | Strong tool use at mid-tier price |
| Agent with many tools, long runs | Claude Opus 5.5 (`medium`), GPT-6.1 Sol | Claude Fable 5.1, GPT-6 Astra | Vendor positioning for long-horizon agentic work [A1, O4] |
| Agentic coding (hardest) | Claude Opus 5.5 | Claude Fable 5.1, GPT-6 Astra | Same |
| Complex reasoning step in a pipeline | Claude Opus 5.5, GPT-6.1 Sol (`high`) | GPT-6 Astra, Claude Fable 5.1 | Fix the prompt first (missing success criterion or check), then raise effort, then switch model [O5] |
| Content generation, localization | Claude Sonnet 5.5 | Claude Opus 5.5 | Test on native-speaker review, not on a benchmark |
| Real-time / web-grounded answers | Web search tool on your current model; Perplexity Agent API | Perplexity `high` / `xhigh` presets for deep research | Live retrieval with citations |
| Audio and video | Gemini 3.5 Flash-Lite | Gemini 3.8 Flash | Native audio and video input |
| Self-hosted production | Qwen3.8-27B (Apache 2.0) | Qwen3.6-35B-A3B, Qwen3.8-Flash-Next (check its license) | Open weights you can run on your own hardware |

---

## Quick Reference

### Anti-patterns

| Anti-pattern | Fix |
|---|---|
| `"Make it good"` | `"Logical flow + 3 supporting examples + conclusion with next step"` |
| Placeholder examples (`[your data here]`) | Realistic data that matches actual input |
| `"If necessary, handle errors"` | `"On timeout: retry 2x. On 500: queue for retry. On 400: return error_code to user"` |
| Critical constraint only in the middle of a long prompt | State it up front and repeat it at the end [Practice] |
| `"Think step by step"` scripted reasoning on current reasoning models | Remove; tune effort / thinking level instead [A6, O7, G2]. Keep explicit verification criteria, except on Opus 5 and on Fable in Claude Code, where reminders cause over-verification or are unnecessary [A6, C1] |
| `"CRITICAL: You MUST use this tool"` | `"Use this tool when..."` - aggressive wording overtriggers on current Claude [A6] |
| `temperature` / `top_p` / `top_k` on Claude 4.7+ | Returns 400; remove and steer with the prompt [A3] |
| `thinking: {"type":"disabled"}` or `budget_tokens` on Opus 5.5 / Sonnet 5.5 / Fable 5.1 | 400; omit `thinking` and pick an effort level (Sonnet 5.5: `between_tools` for no up-front thinking) [A4, A5] |
| Forced `tool_choice` (`any` / named tool) on Opus 5.5 / Sonnet 5.5 / Fable 5.1 | Error; use `auto` plus strict tools or structured outputs [A4, A5, A8] |
| Reading `content[0].text` on current Claude | Select blocks by `type`; responses can start with thinking blocks [A4] |
| Editing earlier turns, the system prompt or tools mid-conversation on current Claude | Keep history append-only; use mid-conversation system messages [A6] |
| Asking Claude to write its reasoning into the answer | Read summarized thinking; the request can be refused as `reasoning_extraction` [A9] |
| Assistant prefill (`{`) on Claude 4.6+ | 400; use structured outputs [A6] |
| `reasoning.effort: "none"` on GPT-6 Astra or GPT-6.1 Sol | Not supported (Astra returns 400); use `low` [O1, O3] |
| Sampling parameters on GPT-6 with effort above `none` | Remove `temperature`, `top_p`, `top_logprobs` (and `logprobs` / the `include` logprobs entry) [O2] |
| Tool calling via Chat Completions on GPT-6 Astra / 6.1 Sol | Use the Responses API [O3] |
| `temperature` / `top_p` / `top_k` on Gemini 3.x | Deprecated / no longer recommended; remove them [G5, G7, G2] |
| `thinking_level` and `thinking_budget` in one Gemini request | 400; use `thinking_level` only [G2] |
| `text/x.enum` for Gemini classification | No longer documented; use a JSON Schema `enum` [G8] |
| `"Search the web for..."` in a Perplexity system prompt | No effect on legacy Sonar, unnecessary on the Agent API; ask the question and put hard constraints in search filter parameters [P6, P7] |
| `/think` / `/nothink` on Qwen3.5 / 3.6 | Not supported; use `enable_thinking` in `chat_template_kwargs` [Q3] |
| Role-heavy framing (`"You are an expert..."`) with no stated goal | Purpose first (`<purpose>` / `# Goal`), role only if it changes the output |
| Writing the prompt in the output language | Prompt body is always English; state output language as a one-line constraint |

### Symptom -> Fix

| Symptom | Fix |
|---------|-----|
| Inconsistent output | Add specific format requirements with an example |
| JSON wrapped in markdown | Enforce the schema at the API; otherwise `"ONLY JSON, no code blocks, no markdown"` |
| Fields sometimes null, sometimes missing | Explicit null policy in the prompt |
| Agent picks the wrong tool | `DO NOT use for:` in each tool doc plus a "Use this tool when..." trigger |
| Claude agent UI goes silent between tool calls | Notes now arrive as `thinking` blocks: set `display: "updates"` (beta) and render them [A4] |
| Claude agent stops mid-task after a progress report | Treat `end_turn` text as a report; send a short message naming the open items; cap automatic continuations at 2-3 [A9] |
| Claude asks permission for work already requested | Fable 5.1 / Sonnet 5.5 autonomy paragraphs [A7, A10], or raise effort |
| Sonnet 5.5 adds unrequested tests, docs or review rounds | "When the work the user asked for is done and its checks pass, stop and report." [A7] |
| Claude answers from memory instead of searching | Remove "minimize tool calls" lines; tell it to search for specifics that may have changed [A7, A10] |
| `refusal` stop reason on benign requests | Read `stop_details.category`; rephrase (e.g. ask whether there are bugs rather than whether the program compiles); configure fallback [A10] |
| Claude JSON reasoning answers wrong at low effort | "Think the problem through before you answer." or `xhigh`; treat `max_tokens` stops as failures [A7] |
| GPT asks too many clarifying questions (Astra) | "Your job is to bias towards action and carry the user's intended task to completion." [O2] |
| GPT output quality low | Check the prompt for a missing success criterion or verification loop before raising effort [O5] |
| Gemini overuses tools | Lower `thinking_level`, then add an action budget line [G2] |
| Gemini 3.8 Flash burns many tokens | Lower `thinking_level`, or use 3.7 Flash [G7] |
| Long Gemini agent sessions skip tool calls | Switch `tool_choice` from `auto` to `any` [Practice] |
| Qwen repeats itself endlessly | Raise `presence_penalty` (0-2) and use the card's sampling values [Q1] |

### Pre-deploy checklist

```
ALL PROMPTS:
[] Test with 5+ realistic inputs
[] Test edge cases (empty input, missing fields, unexpected format)
[] Verify output consistency across runs
[] Prompt body is English; output language stated as a constraint
[] Model ID pinned (no floating alias) and checked against model-lineup.md

CLASSIC AUTOMATION:
[] Task is unambiguous
[] Format is explicit with an example
[] Null/missing data handling defined
[] JSON: enforced at the API where possible, validated in code

AGENTS:
[] SOP covers all expected states
[] Every tool has complete documentation (purpose, params, errors, "when to use")
[] IF/THEN logic is deterministic - no ambiguous branches
[] Error handling for each tool
[] State tracking defined if multi-turn

PROVIDER-SPECIFIC:
[] Claude 4.7+: no sampling params, no prefill, no budget_tokens
[] Fable 5.1 / Opus 5.5 / Sonnet 5.5: no forced tool_choice; blocks read by type;
   thinking blocks passed back unchanged; history append-only; effort set explicitly
[] OpenAI GPT-6: Responses API for tools; no `none` effort on Astra / 6.1 Sol;
   no sampling params above `none`
[] Gemini 3.x: no temperature/top_p/top_k; thinking_level set; schema enforced
[] Perplexity: Agent API for new work; filters as parameters; citations read from fields
[] Qwen: card sampling values; thinking switched with enable_thinking
```

---

## Claude Code Skills

### What skills are
A skill is a directory with a `SKILL.md` file (YAML frontmatter plus Markdown instructions) and optional supporting files. Claude loads a skill automatically when its description matches the task, or you invoke it with `/skill-name`. Custom commands have been merged into skills: `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both create `/deploy` [S1].

Claude Code skills follow the **Agent Skills** open standard (agentskills.io); Claude Code adds its own fields on top [S1, S2].

### SKILL.md template

```yaml
---
name: my-skill              # Optional in Claude Code (defaults to the directory name).
                            # Agent Skills spec: required, max 64 chars, lowercase a-z, 0-9
                            # and hyphens, must match the directory name.
description: >              # Recommended. What it does + when to use it + trigger phrases.
  Third person: "Extracts text from PDFs. Use when the user mentions PDFs or forms."
                            # Spec max 1,024 chars. Claude Code truncates description plus
                            # when_to_use at 1,536 chars in the skill listing.
when_to_use: >              # Optional (Claude Code): extra trigger phrases, appended to description.
argument-hint: "[issue-number]"   # Shown during autocomplete.
arguments: [target]               # Named positional arguments for $target substitution.
disable-model-invocation: false   # true = only you can invoke it, via /my-skill.
user-invocable: true              # false = hidden from the / menu; only Claude invokes it.
allowed-tools: Read Grep          # Pre-approved tools; the grant clears with your next message.
model: sonnet                     # Model for the rest of the current turn (same values as /model).
effort: medium                    # low | medium | high | xhigh | max (depends on the model).
context: fork                     # Run in a forked subagent context ...
agent: Explore                    # ... using this subagent type.
paths: ["src/**/*.ts"]            # Auto-load only when working on matching files.
hooks: {}                         # Hooks registered when the skill is invoked; format in the hooks docs.
license: Apache-2.0               # Spec field; accepted, not acted on by Claude Code.
metadata:                         # Free-form map for your own tooling.
  version: "1.0"
---

# Skill Name

Core instructions here. Keep the body concise: once loaded it stays in context.

## Workflow
1. Step one
2. Step two - see [reference](references/REFERENCE.md)
3. Step three - run scripts/validate.py

## Output Format
[What the skill produces]

## Examples
[1-2 examples of expected behavior]
```

Unknown frontmatter fields are ignored silently by Claude Code, so a typo disables a setting without an error. Skills uploaded to claude.ai or used through the Skills API accept only `name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools`; any other key fails the upload with a hard error [S1].

### Directory structure
```
my-skill/
├── SKILL.md              # Required - instructions
├── scripts/              # Executed, not loaded (only the output costs tokens)
│   └── validate.py
├── references/           # Loaded on demand into context
│   └── REFERENCE.md
└── assets/               # Templates, schemas
    └── template.json
```
Keep references one level deep from `SKILL.md`, and give reference files over 100 lines a table of contents [S3].

### Progressive disclosure (token budget) [S2, S3]
| Level | Loads | Cost | When |
|---|---|---|---|
| Metadata | name + description | ~100 tokens | Always |
| Instructions | Full SKILL.md body | under 5,000 tokens recommended; keep under 500 lines | When triggered |
| Resources | Supporting files | Variable | On demand |
| Scripts | Executed only | Only their output | When needed |

The skill listing (all names plus descriptions) has a budget of 1 % of the model's context window; when it overflows, Claude Code drops descriptions, and the affected skills stop triggering reliably. Run `/doctor` for the listing's cost and `/skill-doctor` to find unused skills [S1] (`/skill-doctor` needs feature-flag fetching, which `DISABLE_TELEMETRY=1` in this pack's settings turns off). After compaction, Claude Code re-attaches only the first 5,000 tokens of each invoked skill, from a combined budget of 25,000 tokens in which older skills can be dropped entirely, so put the most important instructions near the top [S1].

### Writing good descriptions (critical)

The description decides whether the skill triggers. Anthropic's rules [S3]:
- **"Always write in third person."** The description is injected into the system prompt; "inconsistent point-of-view can cause discovery problems."
- **Be specific and include key terms**: both what the skill does and when to use it.

**Good**: "Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction." [S2]

**Bad**: "Helps with documents."

If a skill does not trigger, add the keywords users would naturally say; if it triggers too often, make the description narrower or set `disable-model-invocation: true` [S1]. Test with every model you plan to run it on: "What works perfectly for Opus might need more detail for Haiku." [S3] Anthropic's `skill-creator` plugin (`/plugin install skill-creator@claude-plugins-official`) automates eval runs and comparisons when you change a skill [S1].

### Two kinds of skill content [S1]
| Kind | Purpose | Typical settings |
|---|---|---|
| Reference content | Conventions, style guides, domain knowledge applied to the current work | Defaults; auto-loads when relevant |
| Task content | Step-by-step actions such as deploy, commit, generate | Often `disable-model-invocation: true`; `context: fork` to run in its own subagent |

### Skill locations [S1]
- Personal: `~/.claude/skills/<name>/SKILL.md` (all your projects on this machine)
- Project: `.claude/skills/<name>/SKILL.md` (commit it to share with the team)
- Nested: `<subdir>/.claude/skills/<name>/SKILL.md` (loads when working in that subdirectory)
- Plugin: `<plugin>/skills/<name>/SKILL.md` (invoked as `/plugin-name:skill-name`)
- Enterprise: the managed settings directory
- claude.ai account: skills enabled there sync to Cowork, cloud sessions and signed-in terminal sessions

### Sources: skills
Read 2026-10-05.
- [S1] Claude Code skills: https://code.claude.com/docs/en/skills
- [S2] Agent Skills specification: https://agentskills.io/specification
- [S3] Skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

---

## Plugins (Claude Code and Cowork)

### What plugins are
A plugin bundles skills, commands, subagents, hooks, MCP and LSP servers, output styles and more into one installable package, distributed through a plugin marketplace. Everything is files (Markdown, JSON, scripts) [L1, L2].

### Standard layout [L1]
```
my-plugin/
├── .claude-plugin/
│   └── plugin.json        # Manifest (optional)
├── skills/                # One <name>/SKILL.md per skill
│   └── my-skill/
│       └── SKILL.md
├── commands/              # Flat Markdown command files (prefer skills/ for new plugins)
├── agents/                # Subagent Markdown files
├── hooks/
│   └── hooks.json         # Hook configuration
├── .mcp.json              # MCP server definitions
├── .lsp.json              # LSP server configuration
├── output-styles/         # Output style Markdown files
├── bin/                   # Executables on the Bash tool's PATH while enabled
└── settings.json          # Only `agent` and `subagentStatusLine` apply; other keys are dropped
```
Only `plugin.json` goes inside `.claude-plugin/`; every other file sits at the plugin root [L1].

### plugin.json manifest [L1]
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What this plugin does",
  "author": {"name": "Your Name"}
}
```

- `name` is the only required key; use kebab-case. Every component is namespaced under it.
- Without a manifest, Claude Code loads whatever it finds in the standard layout.
- `version` pins users to that version until you change it, so bump it on every release or users keep the old copy. (Exceptions: plugins with a `command` source, plugins from a marketplace hosted on claude.ai, and plugins loaded in place from a local-path marketplace.)
- Component path keys behave differently: `"skills": ["./extra-skills/"]` adds a folder to the default `skills/`, while `commands`, `agents` and `outputStyles` replace their default location.

### Building a plugin [L1, L2]
1. Create the layout above.
2. Validate: `claude plugin validate <dir>` (add `--strict` to fail on warnings).
3. Test without a marketplace: `claude --plugin-dir ./my-plugin`.
4. Publish through a marketplace and install with `/plugin` (a plugin marketplace is not the claude.com/marketplace website).

### Cowork and claude.ai
Organizations can distribute plugins through claude.ai organization settings. claude.ai and Cowork do not install a plugin that contains a `bin/` directory [L1].

### Sources: plugins
Read 2026-10-05.
- [L1] Plugin manifest reference: https://code.claude.com/docs/en/plugins-reference
- [L2] Plugins overview: https://code.claude.com/docs/en/plugins
