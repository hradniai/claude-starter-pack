# _CONTEXT

This directory holds the user's persistent context — information about you, your work, and your preferences that Claude reads across all projects.

## Files

| File | Purpose |
|------|---------|
| `user-profile.md` | Who you are, what you do, how you like to collaborate. Read by Claude on every session. |
| `notes.md` | Personal brain dump for ideas, impulses, things to explore. Supports the `→ research` auto-trigger. |
| `best-practices/` | Topic-organized notes on how *you* think about recurring problems. Distinct from generic online best practice. |

## How Claude uses this

When you start a session, Claude has access to `~/Documents/_CONTEXT/user-profile.md` if you reference it from your global `AGENTS.md`. It uses your profile to:

- Tailor explanations to your level of expertise
- Frame suggestions in your business and technical context
- Avoid wasting time explaining things you already know
- Push back appropriately given your role and authority

`best-practices/` is read selectively — when a topic comes up, Claude checks if you have a documented approach before defaulting to generic online best practice.

## How you should use this

- **Edit `user-profile.md` whenever something material changes** about your role, focus, tools, or preferences. Outdated profiles are worse than no profile.
- **Drop notes into `notes.md`** without overthinking format. Use `→ research` markers when you want auto-research dispatched (cost: tokens per trigger).
- **Add `best-practices/{topic}.md` files** when you've developed an approach to a recurring topic that differs from generic guidance. Crystallize, don't dump.
