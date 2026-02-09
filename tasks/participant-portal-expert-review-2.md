# Participant Portal — Expert Panel Review #2

**Date:** 2026-02-09
**Panel:** Django Implementation Specialist, Nonprofit Technology Operations Consultant, Penetration Testing Specialist, Social Work Ethics & Client-Informed Practice Researcher
**Format:** 3-round multi-round discussion
**Input:** tasks/participant-portal-design.md + tasks/participant-portal-expert-review.md (first panel findings)

## Purpose

Second expert panel examining blind spots from Panel 1. Focused on: Django implementation realism, nonprofit operational burden, actual attack vectors, and social work ethics.

## Key Findings

### Architecture: Simpler than Panel 1 suggested

| Panel 1 said | Panel 2 says | Resolution |
|-------------|-------------|------------|
| Use `django-hosts` or ROOT_URLCONF switch | **Neither.** 10-line middleware enforces domain/path boundary | Simpler |
| Separate session cookie names needed | **Not needed.** Default `SESSION_COOKIE_DOMAIN=None` isolates cookies by subdomain automatically | Simpler |
| Consider third database for portal data | **No.** FK to ClientFile requires same database. Audit entries go to existing audit DB | Simpler |
| `email_hash` as USERNAME_FIELD | **Won't work.** Use UUID as USERNAME_FIELD, email_hash for lookup only | Fixed |

### Domain enforcement middleware (the whole thing)

```python
class DomainEnforcementMiddleware:
    def __call__(self, request):
        host = request.get_host().split(":")[0]
        if host == settings.PORTAL_DOMAIN and not request.path.startswith("/my/"):
            return HttpResponse("Not Found", status=404, content_type="text/plain")
        if host == settings.STAFF_DOMAIN and request.path.startswith("/my/"):
            return HttpResponse("Not Found", status=404, content_type="text/plain")
        return self.get_response(request)
```

No third-party dependencies. Degrades gracefully when subdomains aren't configured.

### Existing middleware stack: Minimal changes needed

| Middleware | Portal interaction | Change needed? |
|-----------|-------------------|----------------|
| SecurityMiddleware | Works as-is | No |
| WhiteNoiseMiddleware | Works as-is (static files) | No |
| SessionMiddleware | Works as-is (separate cookies per subdomain) | No |
| CsrfViewMiddleware | Works as-is (separate CSRF cookies per subdomain) | No |
| AuthenticationMiddleware | Sets request.user = AnonymousUser for portal | No (this is correct) |
| **NEW: DomainEnforcementMiddleware** | Block invalid domain/path combos | **Add** |
| **NEW: PortalAuthMiddleware** | Set request.participant_user from session | **Add** |
| SafeLocaleMiddleware | Read participant_user.preferred_language | **Small tweak** |
| AuditMiddleware | Log portal access with participant_user_id | **Small tweak** |
| ProgramAccessMiddleware | Short-circuits (user not authenticated) | No |
| TerminologyMiddleware | Portal needs terminology too | No |

### Session isolation: Add Django system check

```python
# Startup check: portal.W001
if settings.SESSION_COOKIE_DOMAIN is not None:
    warn("SESSION_COOKIE_DOMAIN is set — portal sessions may leak between subdomains")
```

## Operational Burden Assessment

### New staff tasks (realistic estimate)

| Task | Who | Frequency | Time per instance | Training |
|------|-----|-----------|-------------------|----------|
| Invite participant | Direct service staff | Per participant | 10 min (incl. consent + MFA setup) | Medium |
| Program alias config | Admin | Once per program | 2 min | Low |
| Password reset | Self-service (no staff) | N/A | N/A | N/A |
| Review correction request | Direct service staff | Occasional | 5 min | Medium |
| Revoke access (safety) | Staff or PM | Rare | 2 min | High (knowing WHEN) |
| Read "Message to Worker" | Direct service staff | As received | 2 min | Low |
| Read pre-session prompt | Direct service staff | Before sessions | 0 min (inline display) | None |

### Operational design decisions

1. **Password reset: Self-service only.** Email-based code. No staff involvement.
2. **Invite flow: <10 minutes.** Must complete consent + account + MFA in one sitting.
3. **No bulk invites.** Consent must be individual and face-to-face.
4. **Program aliases: Smart defaults.** Don't block portal if unconfigured. Flag sensitive keywords ("substance", "mental health", "HIV", "DV", "violence") with a warning nudge.
5. **Feature toggle:** `features.participant_portal` — off by default, per agency.
6. **Pre-session prompts:** Inline in staff client view, not a separate inbox.
7. **"Message to Worker" notice:** "This is not for emergencies" + crisis hotline displayed.

### Required training materials (before launch, not after)

- [ ] One-page staff guide: "How to invite a participant" (print, laminate)
- [ ] One-page participant guide: "How to use your portal" (large print, bilingual, illustrated)
- [ ] 5-min video for staff
- [ ] 5-min video for participants
- [ ] "When to revoke access" decision guide for PMs
- [ ] Ethics discussion guide for staff supervision sessions

## Security: Attack Vectors & Pen Test Plan

### Threat actors

| Actor | Goal | Capability |
|-------|------|------------|
| Malicious participant | Access another participant's data | Valid portal account |
| Abusive partner | Access victim's data | Physical device access, may know email |
| Compromised staff account | Create fake invites to exfiltrate data | Full staff access |
| External attacker | Breach any portal account | Network access, no credentials |

### Attack vectors identified

| ID | Vector | Severity | Mitigation |
|----|--------|----------|-----------|
| AV-1 | IDOR via target_id, metric_def_id in portal URLs | Critical | Every query constrained to participant's client_file |
| AV-2 | Session confusion (staff + portal in same browser) | High | SESSION_COOKIE_DOMAIN=None; explicit test |
| AV-3 | Invite token interception | Medium | Single-use, 7-day expiry, optional verbal confirmation code |
| AV-4 | CSRF across subdomains | High | CSRF_COOKIE_DOMAIN=None; explicit test |
| AV-5 | Brute force login | Medium | Per-account lockout + per-IP rate limit + timing equalization |
| AV-6 | XSS via reflection content in staff view | Critical | Django auto-escaping; explicit test with script injection |
| AV-7 | Timing-based email enumeration | Medium | Dummy hash on unknown email |
| AV-8 | Fake invites from compromised staff | Medium | Post-hoc alerting on unusual patterns; audit trail |

### Automated pen test suite (build alongside features)

| Test | Priority | Type |
|------|----------|------|
| IDOR on every portal endpoint | Critical | Parameterized: second participant's object IDs |
| Session isolation dual-login | Critical | Staff + participant simultaneous sessions |
| XSS in staff view of reflections | Critical | `<script>alert(1)</script>` in reflection content |
| CSRF cross-subdomain | High | Cross-origin request with other domain's token |
| Brute force login resistance | High | Rate limit verification |
| Timing-based enumeration | High | Response time comparison (known vs unknown email) |
| Invite token entropy | Medium | Token format and randomness verification |
| Concurrent session handling | Medium | Login from second device invalidates first |
| Quick-exit session destruction | Medium | Verify session actually destroyed |
| Audit log completeness | Medium | Every portal action creates audit entry |

## Social Work Ethics Assessment

### OCSWSSW Code of Ethics alignment

| Principle | Alignment | Notes |
|-----------|-----------|-------|
| 1.5 Client Empowerment | Strong | Portal supports meaningful participation |
| 5.3 Use of Technology | Satisfied | Informed consent flow addresses this |
| 2.1 Confidentiality | Satisfied with mitigations | Quick-exit, neutral title, safety help page |

### Risks to therapeutic relationship

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Staff inflate metrics knowing participants see them | Medium | `portal_visibility` per MetricDefinition; collaborative scoring training |
| Portal creates pressure to engage | Medium | Never show login activity to staff; frame as right not tool |
| Digital divide (users get better service) | Medium | Ensure non-portal participants get same info by other means |
| "Message to Worker" creates response expectations | High | "Not for emergencies" notice; no read receipts; crisis resources |

### New features recommended by Panel 2

1. **`portal_visibility` field on MetricDefinition** — "Show in portal: Yes / No / Only when self-reported"
2. **"What I want to discuss next time"** — pre-session prompt, inline in staff client view
3. **Correction request soft step** — "Would you like to discuss this with your worker first?" before formal PHIPA request
4. **Verbal confirmation code on invite** — optional 4-digit code told verbally, entered at acceptance

## Updated Critical Path (Both Panels Combined)

1. Legal review of consent language (Canadian privacy lawyer)
2. Ethics consultation with OCSWSSW or equivalent
3. Identify 1-2 pilot agencies
4. Create training materials BEFORE building code
5. DV threat modelling session
6. Build automated security test suite alongside features
7. Erasure workflow extension for portal data

## Updated Phasing (Both Panels Combined)

### Phase A: Foundation
- Feature toggle (off by default)
- Domain enforcement middleware
- Portal auth middleware
- ParticipantUser model (UUID PK, email_hash for lookup)
- PortalInvite with optional verbal confirmation code
- Visual consent flow
- Tiered MFA (TOTP, email code, admin exemption)
- Quick-exit button
- Neutral `<title>`, generic favicon
- "Staying safe online" help page
- Django system check for SESSION_COOKIE_DOMAIN
- Automated IDOR + session + XSS test suite (from day one)

### Phase B: Core Value
- Progressive disclosure dashboard
- Goals with client_goal text
- Progress descriptors timeline
- Metric charts (respecting portal_visibility)
- Milestones
- "What I've been saying" (participant_reflection + client_words)
- "Something doesn't look right?" → soft step → formal correction
- Participant-friendly language (Grade 6 reading level)
- Pen test: IDOR on every new endpoint

### Phase C: Participant Voice
- "My Journal" (private) with one-time disclosure screen
- "Message to My Worker" (shared) with duty-to-act notice + crisis resources
- "What I want to discuss next time" (pre-session, inline in staff view)
- XSS test for all participant-generated content in staff view
- No read receipts, no response expectations

### Phase D: Polish + Groups
- Group visibility (with alias infrastructure, deferred from Phase B)
- 90-day inactivity deactivation
- Staff-side "Manage portal access" UI
- PWA manifest
- Pen test: full suite (10 categories)
- Population-specific accessibility audit (WCAG 2.2 AA + low literacy)
- Staff-assisted login flow (Tier 4) with verbal confirmation
