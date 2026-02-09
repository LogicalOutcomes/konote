# Participant Portal — Expert Panel Review

**Date:** 2026-02-09
**Panel:** Privacy & Health Information Specialist, Social Service Technology Architect, Application Security Engineer, Trauma-Informed UX Designer
**Format:** 3-round multi-round discussion
**Input:** tasks/participant-portal-design.md

## Key Decisions (Consensus)

| Decision | Recommendation | Confidence |
|----------|---------------|------------|
| Separate subdomain | **Yes** | Very high |
| ParticipantUser separate from User | **Yes** | Very high |
| MFA model | **Tiered (4 levels)** | High |
| Reflection model | **Two features, not toggle** | High |
| Programme names in portal | **Mandatory aliases** | Very high |
| Group visibility | **Defer to later phase** | High |
| Quick-exit button | **Mandatory** | Very high |
| Session timeout | **30 min idle / 4 hr absolute** | High |
| Right to correction | **Required (PHIPA s.55)** | Very high |
| Dashboard design | **Progressive disclosure** | High |
| Login identifier | **Email default, assigned-code option** | Medium |
| Consent capture | **Visual flow, not text document** | High |
| Staff sees portal usage | **"Has access" to assigned worker only** | Medium |
| Portal login branding | **Light agency logo, generic tab title** | Medium |
| Offline access | **No** | Very high |
| Notifications | **In-app "new since last visit" only** | High |

## Design Changes Required

### 1. Reflection model: Two features, not a toggle
- **"My Journal"** — private, never seen by staff, with honest disclosure about court-compellable limits
- **"Message to My Worker"** — explicitly shared, with notice that staff may need to act on safety concerns
- Reason: participant must know the audience BEFORE writing, not after

### 2. Dashboard: Progressive disclosure
- One warm greeting + one highlight + simple navigation
- NOT four content panels simultaneously
- Each section on its own page
- Grade 6 reading level for all text

### 3. Programme aliases: Mandatory before portal access
- Every programme must have a portal-display name configured
- Prevents clinical information disclosure via programme names
- Block portal invites until alias is configured

### 4. Group visibility: Defer entirely
- Risk-to-value ratio too high for initial release
- Requires same alias infrastructure as programmes
- Revisit in Phase D

### 5. Quick-exit button: Mandatory from day one
- Fixed-position button visible at all times
- `sendBeacon` logout + `location.replace('https://www.google.ca')`
- Supplemented by "staying safe online" help page
- Generic `<title>` tag ("My Account") and generic favicon

### 6. Consent: Visual flow, not just a checkbox
- 3-4 screens with simple illustrations explaining what's visible
- "I understand" tap on each screen, timestamps recorded
- Defensible as meaningful consent while accessible to low-literacy participants

### 7. MFA: Tiered system
- Tier 1: TOTP (recommended)
- Tier 2: Email one-time codes
- Tier 3: Agency admin exemption with documented reason
- Tier 4: Staff-assisted login during in-person visits (short session)

### 8. Right to correction: Required
- "Something doesn't look right?" button on displayed data
- Creates structured correction request in staff workflow
- Legal requirement under PHIPA Section 55

### 9. Journal privacy disclosure
- One-time screen before first journal use
- Plain language: "These notes are for you. Your worker won't see them. But a court could require the agency to share them. This is very rare."
- Not buried in terms of service

## Critical Path (Before Building)

1. Legal review of consent language by Canadian privacy lawyer
2. Agency buy-in on staff workflow changes
3. Dedicated DV threat modelling session
4. Erasure workflow extension for portal data

## Adjusted Phasing

### Phase A: Foundation
- As designed + subdomain routing, quick-exit, visual consent, programme alias config, tiered MFA, neutral title/favicon, safety help page

### Phase B: Core Value
- Goals and progress (no groups)
- Correction request mechanism
- Progressive disclosure dashboard
- Participant-friendly language throughout

### Phase C: Participant Voice
- "My Journal" (private) with disclosure screen
- "Message to My Worker" (shared) with duty-to-act notice
- No share/unshare toggle

### Phase D: Polish + Groups
- Group visibility with alias infrastructure
- Pen testing with participant-impersonation scenarios
- Population-specific accessibility audit
- Staff-assisted login flow
