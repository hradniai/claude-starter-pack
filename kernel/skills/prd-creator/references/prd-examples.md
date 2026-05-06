# PRD Examples and Templates

This file contains example PRD sections to illustrate best practices and expected output quality.

## Example: Complete Mini-PRD for a Feature

### 1. Executive Summary
**Feature:** Real-time Collaboration in Document Editor  
**Problem:** Users currently must save and refresh to see teammate changes, causing confusion and lost work.  
**Goal:** Enable simultaneous editing with instant change visibility.  
**Success Metric:** 40% reduction in edit conflicts, 25% increase in collaborative session duration.  
**Timeline:** Q2 2025 launch  
**Owner:** Product Team (Engineering: Sarah Chen, PM: Alex Kim)

### 2. Problem & Context
**Current State:** Users editing the same document see changes only after manual refresh. This leads to:
- Overwritten work (3.2% of collaborative sessions)
- User frustration (NPS -15 for collaboration)
- Workarounds via Slack/email ("who's editing what?")

**Market Context:** Competitors (Google Docs, Notion) offer real-time collab as baseline.

**Why Now:** Customer feedback (#1 requested feature), strategic push for team plans.

### 3. Goals & KPIs

**Primary Goal:** Enable frictionless simultaneous editing

**Success Metrics:**
- **North Star:** 40% reduction in edit conflicts (from 3.2% to <2%)
- **Engagement:** 25% increase in avg. collaborative session duration
- **Adoption:** 60% of team plan users try feature within 2 weeks
- **Quality:** <0.5% data loss incidents

**Guardrails:**
- No increase in document load time (maintain <2s)
- Server costs increase <20%
- No security regressions

### 4. Stakeholders & RACI

| Role | Name | R/A/C/I |
|------|------|---------|
| Product Manager | Alex Kim | A |
| Tech Lead | Sarah Chen | R |
| Backend Team | Dev Team | R |
| Frontend Team | Dev Team | R |
| Design | Jordan Lee | C |
| Security | Taylor Park | C |
| Customer Success | Morgan Smith | I |
| Executive Sponsor | VP Product | I |

### 5. Users / Personas & JTBD

**Primary Persona:** "Collaborative Chris"
- Role: Content team lead
- Team size: 3-8 members
- Use case: Co-authoring proposals, reports, documentation
- Pain: "I never know if my teammate is editing the same section"
- JTBD: Write and edit content with my team without stepping on each other's toes

**Secondary Persona:** "Remote Rachel"
- Role: Distributed team member
- Context: Different timezones, async work
- Pain: "By the time I see comments, the discussion has moved on"
- JTBD: Stay in sync with team decisions on document changes

### 6. Use Cases & Primary User Journeys

**UC1: Simultaneous Editing**
1. Chris opens shared document
2. Sees that Sarah is actively editing (presence indicator)
3. Chris edits paragraph 3 while Sarah edits paragraph 5
4. Both see each other's changes appear in real-time (<500ms)
5. No conflicts, no lost work

**UC2: Cursor Following**
1. Jordan joins document where team is discussing section 2
2. Clicks on Sarah's avatar to jump to her cursor position
3. Sees changes as Sarah types
4. Adds inline comment that Sarah sees immediately

**UC3: Conflict Detection**
1. Chris and Sarah unknowingly start editing same sentence
2. System detects overlap, highlights conflict zone
3. Shows both versions side-by-side
4. Users resolve with one click ("keep mine" / "keep theirs" / "merge")

**Edge Cases:**
- Network interruption during edit (offline buffer, conflict resolution on reconnect)
- User with read-only access (see live changes but can't edit)
- Document locked for compliance (no real-time changes, audit trail)
- 50+ simultaneous users (performance degradation, cap at 50)

### 7. Scope (MoSCoW) & Out of Scope

**Must Have (v1):**
- Real-time text editing synchronization
- Presence indicators (who's viewing/editing)
- Cursor position visibility
- Basic conflict detection and resolution
- Offline mode with sync on reconnect

**Should Have (v1):**
- Selection highlighting
- Following another user's cursor
- Edit history with attribution

**Could Have (v1.1):**
- Voice/video chat integration
- Suggested edits mode
- Change notifications

**Won't Have:**
- Real-time formatting sync (images, tables) - v2
- Mobile app support - separate roadmap
- Version branching - future consideration

### 8. Functional Requirements

**FR1: Real-time Sync**
- Priority: Must Have
- Description: Propagate text changes to all active clients within 500ms (p95)
- Dependencies: WebSocket infrastructure
- RICE Score: Reach=8, Impact=10, Confidence=8, Effort=8 → Score=10

**FR2: Presence System**
- Priority: Must Have
- Description: Show avatars of active users with cursor positions
- Acceptance: User sees list of active collaborators within 2s of joining

**FR3: Conflict Resolution**
- Priority: Must Have
- Description: Detect overlapping edits, present resolution UI
- Acceptance: No data loss in conflict scenarios (100% of conflicts caught)

### 9. Non-functional Requirements

**Performance:**
- Real-time latency: <500ms (p95), <200ms (p50)
- Document load time: <2s (no regression from current)
- Support 50 concurrent editors per document
- Offline buffer: Up to 5 minutes of edits

**Availability:**
- 99.9% uptime for collaboration service
- Graceful degradation: Fall back to polling if WebSocket fails

**Security:**
- End-to-end encryption for document content
- Access control: No permission escalation via real-time features
- Audit trail: All changes attributed to user ID with timestamp

**Compliance:**
- GDPR: User consent for presence data, right to be "invisible"
- Data retention: Sync logs retained 30 days, audit logs 2 years
- SOC 2: Real-time features in compliance scope

**Scalability:**
- Horizontal scaling of collaboration servers
- Document sharding by ID
- Rate limiting: 100 operations/user/second

### 10. Metrics, Tracking Plan & Experimentation

**Tracking Plan:**

| Event | Trigger | Properties | KPI Mapping | Privacy |
|-------|---------|------------|-------------|---------|
| collab_session_start | User opens shared doc with others online | doc_id, user_id, num_collaborators | Adoption | Legitimate interest |
| collab_edit | User makes change while others present | doc_id, user_id, edit_type, latency_ms | Engagement, Quality | Legitimate interest |
| collab_conflict | System detects overlapping edit | doc_id, users_involved, resolution_method | Quality | Legitimate interest |
| collab_presence_view | User views collaborators list | doc_id, user_id, num_visible | Adoption | Legitimate interest |

**Funnels:**
- Activation: Doc open → See collaborator → Make edit → Complete session
- Conflict resolution: Conflict detected → Resolution UI shown → User action → Resolution success

**Experimentation:**
- **Test 1:** Cursor position visibility (on/off) - measure edit conflicts
- **Test 2:** Conflict resolution UI (side-by-side vs. inline) - measure resolution time
- **Rollout:** 5% (week 1) → 25% (week 2) → 100% (week 4)

### 11. Dependencies, Risks & Mitigation

**Dependencies:**
- WebSocket infrastructure (Tech team, Q1 complete)
- Conflict-free Replicated Data Type (CRDT) library evaluation
- Load balancer upgrade for sticky sessions

**Technical Risks:**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CRDT performance at scale | Medium | High | Benchmark with 100k char docs, 50 users |
| WebSocket connection stability | Medium | High | Implement polling fallback |
| Data loss in edge cases | Low | Critical | Comprehensive conflict testing, staged rollout |
| Latency spikes under load | High | Medium | Load testing, caching strategy |

**Business Risks:**
- User confusion with new UI (Medium/Medium) → User testing, in-app tutorial
- Adoption slower than expected (Low/Medium) → Proactive comms, CS training
- Competitive feature parity claims (Low/Low) → Marketing positioning

### 12. Alternatives and Why Not

**Alternative 1: Polling-based sync (every 5s)**
- Why not: Poor UX, feels laggy, not "real-time"
- Trade-off: Simpler implementation but fails to meet user expectations

**Alternative 2: Operational Transform (OT) instead of CRDT**
- Why not: Higher complexity, central server dependency
- Trade-off: Mature tech but scaling concerns

**Alternative 3: Lock-based editing (one user at a time)**
- Why not: Defeats purpose of collaboration
- Trade-off: Zero conflicts but terrible UX

### 13. Milestones, Roadmap, Budget

**Phase 1: Foundation (Weeks 1-4)**
- WebSocket infrastructure setup
- CRDT library integration
- Basic sync prototype

**Phase 2: Core Features (Weeks 5-8)**
- Presence system
- Real-time text sync
- Conflict detection

**Phase 3: Polish (Weeks 9-10)**
- Offline mode
- Performance optimization
- Error handling

**Phase 4: Launch (Weeks 11-12)**
- Beta testing (week 11)
- Staged rollout (week 12)

**Budget (high-level):**
- Engineering: 3 backend, 2 frontend, 1 QA → 6 engineers × 12 weeks
- Infrastructure: $5k/month for WebSocket servers (scaled)
- Third-party: CRDT library license if needed ($0 for open-source option)

### 14. Acceptance Criteria (BDD/Gherkin) & Definition of Done

**AC1: Real-time Text Sync**
```gherkin
Scenario: User sees collaborator's edits in real-time
  Given two users, Alice and Bob, have the same document open
  And both users have active internet connections
  When Alice types "Hello World" in paragraph 1
  Then Bob sees "Hello World" appear in paragraph 1 within 500ms
  And the change is attributed to Alice in the presence indicator
```

**AC2: Conflict Detection**
```gherkin
Scenario: System detects and resolves overlapping edits
  Given Alice and Bob are editing the same sentence
  When Alice changes "quick brown fox" to "slow brown fox"
  And Bob changes "quick brown fox" to "quick red fox" within 2 seconds
  Then the system detects a conflict
  And displays both versions: "slow brown fox" (Alice) and "quick red fox" (Bob)
  And provides resolution options: "Keep Alice's", "Keep Bob's", "Merge"
  When Alice selects "Merge" and creates "slow red fox"
  Then the merged version is synced to all users
  And no data loss occurs
```

**AC3: Offline Mode**
```gherkin
Scenario: User continues editing when network drops
  Given Alice is editing a document with real-time sync active
  When Alice's network connection is lost
  Then Alice sees an "Offline" indicator
  And can continue making edits locally
  When Alice's connection is restored within 5 minutes
  Then local edits are synced to the server
  And conflicts (if any) are resolved using conflict detection flow
```

**Definition of Done:**
- [ ] All acceptance criteria pass (automated tests)
- [ ] Load tested with 50 concurrent users
- [ ] Security review completed (no vulnerabilities)
- [ ] Documentation updated (user guide, API docs)
- [ ] Monitoring/alerting configured (latency, error rate)
- [ ] Rollback plan tested
- [ ] Beta feedback incorporated (≥80% satisfaction)
- [ ] Stakeholder sign-off (PM, Tech Lead, Security)

### 15. Open Questions

- **Q1:** Should we support real-time sync for document formatting (bold, italic) in v1?
  - Owner: Sarah (Tech Lead)
  - Deadline: Week 2
  
- **Q2:** What's the policy for users with unstable connections (frequent offline/online)?
  - Owner: Alex (PM)
  - Deadline: Week 1

- **Q3:** Do we need admin controls to disable real-time collab for certain documents?
  - Owner: Taylor (Security)
  - Deadline: Week 3

---

## Gherkin (BDD) Examples

### Format
```gherkin
Scenario: [Title describing user goal]
  Given [initial context/state]
  And [additional context]
  When [action/trigger]
  And [additional actions]
  Then [expected outcome]
  And [additional outcomes]
```

### Example 1: User Registration
```gherkin
Scenario: Successful user registration with valid email
  Given the user is on the registration page
  And the email "user@example.com" is not already registered
  When the user enters "user@example.com" in the email field
  And enters a password with at least 8 characters
  And clicks the "Sign Up" button
  Then the system creates a new account
  And sends a verification email to "user@example.com"
  And redirects the user to the "Check Your Email" page
  And displays the message "Verification email sent"
```

### Example 2: Error Handling
```gherkin
Scenario: Registration fails with already-used email
  Given the user is on the registration page
  And the email "existing@example.com" is already registered
  When the user enters "existing@example.com" in the email field
  And enters a valid password
  And clicks the "Sign Up" button
  Then the system does not create a new account
  And displays the error message "This email is already registered"
  And highlights the email input field in red
  And the user remains on the registration page
```

### Example 3: Complex Workflow
```gherkin
Scenario: User completes checkout with discount code
  Given the user has 3 items in their cart totaling $100
  And the user is logged in
  And a valid discount code "SAVE20" exists for 20% off
  When the user proceeds to checkout
  And enters "SAVE20" in the discount code field
  And clicks "Apply"
  Then the discount is applied
  And the new total is $80
  When the user enters valid payment information
  And clicks "Complete Purchase"
  Then the order is processed successfully
  And the user receives an order confirmation email
  And the inventory is updated for all 3 items
  And the discount code "SAVE20" is marked as used
```

### Example 4: Edge Case
```gherkin
Scenario: User attempts to apply expired discount code
  Given the user has items in their cart
  And is on the checkout page
  And the discount code "EXPIRED2024" existed but expired on 2024-12-31
  When the user enters "EXPIRED2024" in the discount code field
  And clicks "Apply"
  Then the system rejects the discount code
  And displays the message "This discount code has expired"
  And the cart total remains unchanged
  And the discount code field is cleared
```

---

## MoSCoW Prioritization Example

| Requirement | Priority | Rationale | Dependencies |
|-------------|----------|-----------|--------------|
| User login | **Must Have** | Core functionality, no product without it | Auth service |
| Password reset | **Must Have** | Critical for user retention | Email service |
| Social login (Google) | **Should Have** | Reduces friction, but workaround exists | OAuth integration |
| Social login (Facebook) | **Could Have** | Nice to have, limited user demand | OAuth integration |
| Biometric login | **Won't Have** | Complex, low ROI for v1 | Device APIs, security audit |
| Remember me checkbox | **Should Have** | Convenience feature, commonly expected | Session management |
| Two-factor auth (2FA) | **Must Have** | Security requirement, compliance | SMS gateway or TOTP |

---

## RICE Scoring Example

**Formula:** RICE Score = (Reach × Impact × Confidence) / Effort

| Feature | Reach | Impact | Confidence | Effort | RICE Score | Priority |
|---------|-------|--------|------------|--------|------------|----------|
| Real-time collab | 8 (80% of team users) | 3 (massive impact) | 80% | 8 (2 months) | 2.4 | High |
| Dark mode | 6 (60% users want it) | 2 (moderate) | 100% | 2 (2 weeks) | 6.0 | High |
| API webhooks | 3 (power users) | 3 (massive for them) | 70% | 5 (1 month) | 1.26 | Medium |
| Mobile app | 7 (many mobile users) | 2 (moderate) | 60% | 13 (3 months) | 0.65 | Low |

**Reach:** How many users impacted (scale 1-10)  
**Impact:** How much it helps each user (1=minimal, 2=moderate, 3=massive)  
**Confidence:** How sure we are of Reach/Impact (percentage)  
**Effort:** Engineering months (person-months)

---

## RACI Matrix Template

| Task / Decision | Product Manager | Tech Lead | Design | Engineering | QA | Legal | Stakeholder |
|-----------------|----------------|-----------|--------|-------------|----|----|-------------|
| Define requirements | A | C | C | C | I | I | I |
| Technical architecture | C | A | I | R | I | I | I |
| UI/UX design | C | C | A | I | I | I | I |
| Implementation | I | R | I | R | I | I | I |
| Testing | I | C | I | I | A/R | I | I |
| Legal/compliance review | I | I | I | I | I | A | I |
| Launch decision | A | C | I | I | I | I | C |

**Legend:**
- **R** = Responsible (does the work)
- **A** = Accountable (final approval, only one per task)
- **C** = Consulted (provides input)
- **I** = Informed (kept in the loop)

---

## Risk Matrix Example

| Risk | Probability | Impact | Risk Score | Mitigation | Owner |
|------|-------------|--------|------------|------------|-------|
| Third-party API goes down | Medium | High | 🔴 High | Implement caching, fallback mode, SLA monitoring | Backend Lead |
| GDPR compliance issue | Low | Critical | 🔴 High | Legal review, privacy impact assessment, audit trail | Legal + PM |
| Launch delayed 2 weeks | High | Medium | 🟡 Medium | Buffer time in roadmap, parallel workstreams | PM |
| User adoption below target | Medium | Medium | 🟡 Medium | User testing, phased rollout, feedback loops | PM + Design |
| Database performance at scale | Low | High | 🟡 Medium | Load testing, query optimization, caching | Backend Lead |
| Security vulnerability | Low | Critical | 🔴 High | Security audit, penetration testing, bug bounty | Security Team |

**Risk Score Calculation:**
- 🔴 **High:** Probability=High × Impact=High/Critical OR Probability=Medium × Impact=Critical
- 🟡 **Medium:** Probability=Medium × Impact=Medium/High OR Probability=High × Impact=Low/Medium
- 🟢 **Low:** Probability=Low × Impact=Low/Medium

---

## Tracking Plan Example

| Event Name | Trigger | Properties | Mapped KPI | Privacy Basis |
|------------|---------|------------|------------|---------------|
| `user_signup` | User completes registration | `user_id`, `email`, `signup_method` (email/google/facebook), `referral_source`, `timestamp` | User acquisition | Legitimate interest |
| `document_created` | User creates new document | `user_id`, `doc_id`, `doc_type`, `template_used`, `timestamp` | Engagement | Legitimate interest |
| `collaboration_started` | 2+ users open same doc | `doc_id`, `user_ids[]`, `num_collaborators`, `timestamp` | Collaboration adoption | Legitimate interest |
| `conflict_detected` | System detects edit overlap | `doc_id`, `user_ids[]`, `conflict_type`, `resolution_method`, `resolution_time_ms`, `timestamp` | Quality (conflict rate) | Legitimate interest |
| `feature_used` | User interacts with new feature | `user_id`, `feature_name`, `usage_context`, `timestamp` | Feature adoption | Legitimate interest |
| `error_occurred` | System error impacts user | `user_id`, `error_type`, `error_message`, `page_url`, `timestamp` | Reliability (error rate) | Legitimate interest |
| `subscription_upgraded` | User upgrades to paid plan | `user_id`, `from_plan`, `to_plan`, `payment_method`, `timestamp` | Revenue | Contract necessity |
| `user_feedback` | User submits feedback form | `user_id`, `feedback_text`, `rating`, `page_context`, `timestamp` | Satisfaction | Consent |

**Privacy Notes:**
- **Legitimate interest:** Used for product improvement, operational necessity
- **Contract necessity:** Required to fulfill service (e.g., billing)
- **Consent:** Explicitly opt-in (e.g., marketing, optional surveys)
- All events must respect GDPR right to erasure (delete user data on request)
