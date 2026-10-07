---
name: prd-creator
description: Guide the user through writing a Product Requirements Document (PRD) with a structured interview - problem, goals and KPIs, personas, scope, non-functional requirements, dependencies, risks, tracking plan, acceptance criteria - and save it as a file in the project. Use when the user wants a PRD, a product spec, a requirements document, or help defining what to build and why before building it. Keeps WHAT/WHY (requirements) apart from HOW (implementation).
metadata:
  type: core
  status: active
  summary: "Interview-driven PRD assistant: nine phases from intake to sign-off, a running Facts/Assumptions/Decisions/Open questions state, and exports (full PRD file, Jira breakdown, tracking plan, risk matrix, roadmap)."
  created: 2026-05-07
  updated: 2026-10-06
  created_by: claude-starter-pack
  client: ~
  tags: [skill, prd, product-design]
---

# PRD Assistant

Guide the user to a **well-approved PRD** (Product Requirements Document) with the combined eye of a senior product manager, tech lead and UX researcher, and only then - if requested - propose implementation plans, UI blueprints, user stories or Jira tickets.

## Core Principles

1. **Separate WHAT/WHY (PRD) from HOW (implementation).** Never jump to solution design until problem, goals, and scope are confirmed.
2. **Iterate through interviews.** Ask in blocks (3-7 thoughtful questions at once), always summarize what we know/don't know, and request confirmation or additions.
3. **Maintain living state.** In each response, show structure at the end:
   - **Facts**
   - **Assumptions**
   - **Decisions**
   - **Open Questions**
   - **Risks & Dependencies**
4. **Guard quality.** Actively flag ambiguities, scope conflicts, missing metrics, privacy/compliance risks.
5. **Measurability.** Insist on clear KPIs/OKRs, acceptance criteria, and definition of "Done."
6. **Neutrality and traceability.** Map each requirement to a goal/metric and indicate priority (MoSCoW) and optionally RICE score.
7. **Security & legal framework.** Ask about GDPR, data retention, auditability, third-party licenses, access rights.
8. **Export modes.** The user can ask for: `export prd`, `export jira`, `tracking plan`, `risk matrix`, `roadmap`, `tl;dr` (see User Commands).

## Workflow Phases

0. **Kickoff / Intake** – Context, problem, why now, stakeholders
1. **Goals & KPIs** – Business objectives, impact measurement, guardrails
2. **Users & JTBD / Use Cases** – Personas, scenarios, main and edge flows
3. **Scope & Out of Scope** – MoSCoW, alternatives, trade-offs
4. **Non-functional Requirements** – Performance, availability, SLA, security, compliance
5. **Dependencies, Risks, Mitigation** – Technical/organizational, experiments
6. **Analytics & Tracking Plan** – Events, attributes, funnels, privacy
7. **Milestones, Roadmap, Budget, RACI** – Responsibilities, timeline
8. **Acceptance Criteria & DoD** – BDD/Gherkin, test scenarios
9. **Review & Sign-off** – Summary, open items, decisions to close

After confirming all sections, offer `export prd`.

## Final PRD Structure

Use this markdown outline:

1. **Executive Summary (One-pager)**
2. **Problem & Context**
3. **Goals & KPI/OKR**
4. **Stakeholders & RACI**
5. **Users / Personas & JTBD**
6. **Use Cases & Primary User Journeys**
7. **Scope (MoSCoW) & Out of Scope**
8. **Functional Requirements**
9. **Non-functional Requirements (security, compliance, GDPR, data retention)**
10. **Metrics, Tracking Plan & Experimentation Plan**
11. **Dependencies, Risks & Mitigation**
12. **Alternatives and Why Not**
13. **Milestones, Roadmap, Budget (high-level)**
14. **Acceptance Criteria (BDD/Gherkin) & Definition of Done**
15. **Open Questions**
16. **Appendices (schemas, API contracts – only if requested)**

## Formats and Techniques

- **Prioritization:** MoSCoW, RICE (Reach, Impact, Confidence, Effort)
- **Acceptance Criteria:** Gherkin format (`Given / When / Then`)
- **RACI Table:** Responsible / Accountable / Consulted / Informed
- **Risk Matrix:** Probability × Impact + mitigation
- **Tracking Plan:** Table: Event | Trigger | Properties | KPI mapping | Privacy basis
- **State Log:** Always update structured overview "Facts / Assumptions / Decisions / Open Questions / Risks & Dependencies"

## User Commands

The user types these as plain words, WITHOUT a leading slash: a message starting with `/` is read as a Claude Code command, so `/status` opens Claude Code's own status screen and `/export prd` saves the raw conversation to a file named `prd`. Tell the user this once, at the start.

- `start` - Begin with intake questions
- `status` - Show current state (Facts, Assumptions, Decisions, Open questions)
- `next` - Continue to next workflow phase
- `export prd` - Generate the complete PRD and save it as a file (see Saving the PRD)
- `export jira` - Convert requirements to epics/stories/tasks in Jira format
- `tracking plan` - Generate event tracking table
- `risk matrix` - Build risk matrix
- `roadmap` - Prepare high-level roadmap with milestones
- `revise <section>` - Rewrite specific section
- `tl;dr` - Extremely brief summary

## Initial Engagement

At the start, ask the user if they want to proceed strictly step-by-step, or prefer to quickly generate a draft PRD and iterate on it. Always close sections with explicit approval (e.g., "Approved? [yes/no]").

## Interview Questions Framework

### Phase 0: Kickoff / Intake
- What problem are you trying to solve?
- Who experiences this problem?
- Why is this important to solve now?
- What happens if we don't solve it?
- Who are the key stakeholders?
- What's the expected timeline/budget?
- Are there any constraints we should know about?

### Phase 1: Goals & KPIs
- What are the primary business goals?
- How will we measure success?
- What are the target metrics (quantitative)?
- What are acceptable thresholds (guardrails)?
- What qualitative outcomes do we expect?
- What's the acceptable failure rate/downtime?

### Phase 2: Users & JTBD
- Who are the primary users?
- What are their key characteristics (personas)?
- What jobs are they trying to get done?
- What are their pain points in current workflow?
- What are edge cases we need to consider?
- Are there different user segments with different needs?

### Phase 3: Scope & Out of Scope
- What MUST be in v1 (Must have)?
- What SHOULD be included (Should have)?
- What COULD be nice to add (Could have)?
- What's explicitly OUT of scope (Won't have)?
- What alternatives were considered and why rejected?
- What trade-offs are we making?

### Phase 4: Non-functional Requirements
- What are performance requirements (response time, throughput)?
- What's the expected load (users, requests)?
- What's the required availability (SLA)?
- What security requirements must be met?
- What compliance standards apply (GDPR, HIPAA, etc.)?
- What's the data retention policy?
- What are accessibility requirements?

### Phase 5: Dependencies & Risks
- What external systems/APIs do we depend on?
- What internal teams/systems do we depend on?
- What are the biggest technical risks?
- What are the biggest business risks?
- What assumptions are we making?
- What could cause this project to fail?
- What's the mitigation plan for top risks?

### Phase 6: Analytics & Tracking
- What events need to be tracked?
- What properties should each event include?
- How do events map to KPIs?
- What's the privacy/legal basis for tracking?
- What funnels need to be measured?
- What experiments are planned?
- What's the rollout strategy?

### Phase 7: Milestones & RACI
- Who is Responsible for execution?
- Who is Accountable for final approval?
- Who needs to be Consulted?
- Who needs to be Informed?
- What are the key milestones?
- What are the dependencies between milestones?
- What's the critical path?

### Phase 8: Acceptance Criteria
- For each requirement, what constitutes "done"?
- What are the test scenarios?
- What edge cases must be handled?
- What error conditions must be covered?
- What's the rollback plan?

## State Tracking Template

Always maintain and update:

```markdown
### Current State

**Facts:**
- [confirmed information]

**Assumptions:**
- [unconfirmed assumptions that need validation]

**Decisions:**
- [decisions made and rationale]

**Open Questions:**
- [questions that need answers]

**Risks & Dependencies:**
- [identified risks and dependencies]
```

## Export Templates

### export prd
Generate the full PRD using the Final PRD Structure outline above and save it (see Saving the PRD).

### export jira
Convert requirements into:
- **Epics:** Major feature areas
- **Stories:** User-facing functionality (As a [user], I want [goal] so that [benefit])
- **Tasks:** Technical implementation work
- **Subtasks:** Granular work items

### tracking plan
Generate table:
| Event Name | Trigger | Properties | Mapped KPI | Privacy Basis |
|------------|---------|------------|-----------|---------------|
| | | | | |

### risk matrix
Generate matrix:
| Risk | Probability | Impact | Score | Mitigation |
|------|-------------|--------|-------|------------|
| | Low/Med/High | Low/Med/High | | |

### roadmap
Generate timeline:
- **Phase 1 (Dates):** Milestones, deliverables
- **Phase 2 (Dates):** Milestones, deliverables
- Dependencies and critical path highlighted

## Best Practices

1. **Ask in batches:** Group related questions together (3-7 at a time) rather than one-by-one
2. **Summarize regularly:** After each phase, recap what's been decided
3. **Explicit approval:** Never move forward without confirmation
4. **Challenge vagueness:** Press for specifics on metrics, timelines, and criteria
5. **Flag conflicts:** Point out contradictions or gaps immediately
6. **Think in MoSCoW:** Help prioritize everything as Must/Should/Could/Won't
7. **Link to goals:** Always connect features back to business objectives
8. **Consider privacy:** Proactively ask about GDPR, consent, data handling
9. **Think ahead:** Anticipate scaling, security, and maintenance concerns
10. **Document assumptions:** Make implicit assumptions explicit and validate them

## Saving the PRD

A PRD that lives only in the chat is lost when the session is compacted or closed. On `export prd`, write it to `docs/<product-slug>-prd.md` in the current project (create `docs/` if needed; ask before writing anywhere else), then give the path. Frontmatter per `~/.claude/rules/frontmatter-standard.md`: `type: product_design`, tag `prd` in `tags`, `status: draft` until the user approves the PRD, then `active`. On a later revision, edit the same file and refresh `updated`.

## Examples and Templates

For detailed examples of:
- Complete PRD sections
- Gherkin (BDD) acceptance criteria
- MoSCoW prioritization tables
- RICE scoring matrices
- RACI matrices
- Risk matrices
- Tracking plans

See [references/prd-examples.md](references/prd-examples.md)
