# Best Practices

> One markdown file per topic. Capture *your* approach to recurring problems — distinct from generic online best practice.

## Why

Online best practices are generic. They work for the median case, often poorly for yours. As you develop opinions about how *you* want to handle recurring topics (project setup, client onboarding, AI strategy, code review, whatever), capture them here. Over time, this folder becomes the primary source for "how I think about X" — replacing online lookups for those topics.

## When to add

Add a file when one of these surfaces:
1. You override a generic online practice with your own approach
2. A distinct method emerges from how you actually work
3. You articulate how you want to think about a recurring topic
4. A pattern is validated across multiple decisions

Don't dump every passing thought. Crystallize when something stable emerges.

## Filename

Kebab-case, one topic per file: `client-onboarding.md`, `code-review.md`, `ai-strategy.md`, `prompting.md`.

**Never create a new file for a topic that already exists.** Integrate into the existing one. File proliferation defeats the purpose.

## Format

```markdown
# {Topic}

> One-line purpose.

## {Principle 1}

Guidance for future use. Include rationale.

## {Principle 2}

...

---

## Change log

| Date | Added | Source | Removed |
|------|-------|--------|---------|
| YYYY-MM-DD | What was added or restructured | Conversation/project context | What was removed |
```

The change log preserves history when main content is overwritten — nothing silently lost.

## Length

Keep individual files under ~5 KB if possible. Large files hurt context efficiency. If a topic genuinely needs more, split it into a subdirectory: `client-onboarding/{discovery,kickoff,handoff}.md`.
