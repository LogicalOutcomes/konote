# Participant Portal — Implementation Plan

**Consolidation of:** design document + 4 expert panel reviews (12+ experts)
**Date:** 2026-02-09
**Status:** Ready for pre-build steps — plan is now frozen

---

## What we're building

A separate, secure portal where participants can log in and see their own progress — goals in their own words, progress charts, milestones, and reflections captured during sessions. They can also write private journal entries and send messages to their worker. They never see staff clinical notes, engagement observations, or alerts.

The portal lives on its own subdomain (e.g., `myjourney.agencyname.org`), has its own login system completely separate from staff, and is structurally unable to show one participant another participant's data.

---

## Before building: Pre-build checklist

These must happen before writing code. They're not optional.

- [ ] **PB-1: Legal review of consent language** — Canadian privacy lawyer reviews the informed consent flow, the journal privacy disclosure, and the "Message to My Worker" duty-to-act notice
- [ ] **PB-2: Identify 1-2 pilot agencies** — agencies willing to trial, with at least one tech-comfortable staff member
- [ ] **PB-3: Create training materials** — one-page staff guide, one-page participant guide (bilingual, illustrated), "when to revoke access" guide for PMs
- [ ] **PB-4: DV threat modelling session** — dedicated session focused on intimate partner violence and coerced access scenarios
- [ ] **PB-5: Ethics consultation** — OCSWSSW or equivalent, to validate the digital access approach

---

## Decided: Key design decisions (locked)

These were debated across two expert panels (8 experts total) and are settled.

| # | Decision | Answer | Why |
|---|----------|--------|-----|
| D1 | Separate subdomain | **Yes** | Cookie isolation, trust, neutral browser history |
| D2 | ParticipantUser separate from staff User | **Yes** | Structural isolation — staff decorators auto-deny portal users |
| D3 | MFA model | **Tiered (4 levels)** | TOTP > email code > admin exemption > staff-assisted login |
| D4 | Reflection model | **Two features, not a toggle** | "My Journal" (private) + "Message to My Worker" (shared) |
| D5 | Program names in portal | **Smart-default aliases** | Default = program name; flag sensitive keywords with warning |
| D6 | Group visibility | **Defer to Phase D** | Risk-to-value ratio too high for initial release |
| D7 | Quick-exit button | **Mandatory from day one** | Fixed-position, sendBeacon logout, redirect to Google.ca |
| D8 | Session timeout | **30 min idle / 4 hr absolute** | Generous enough for population; no persistent sessions |
| D9 | Right to correction | **Required (PHIPA s.55)** | "Something doesn't look right?" → soft step → formal request |
| D10 | Dashboard | **Progressive disclosure** | Greeting + one highlight + simple nav. One section per page. |
| D11 | Login identifier | **Email default, agency-assigned code option** | Supports populations with unstable email |
| D12 | Consent capture | **Visual flow (3-4 screens)** | Accessible to low-literacy; defensible as meaningful consent |
| D13 | Staff sees portal usage | **"Has access" only, never activity** | No login timestamps visible to any staff |
| D14 | Offline access | **No** | Shared device risk too high |
| D15 | Notifications | **In-app "new since last visit" only** | No push/email — lock screen visibility risk |
| D16 | Feature toggle | **Off by default, per agency** | `features.participant_portal` in feature toggles |
| D17 | Third database | **No** | Portal tables go in default DB (FK to ClientFile). Audit entries to existing audit DB. |
| D18 | Metric visibility | **`portal_visibility` on MetricDefinition** | "Yes / No / Only when self-reported" per metric type |
| D19 | Pre-session prompt | **"What I want to discuss next time"** | Inline in staff client view, not a separate inbox |
| D20 | Portal branding | **Light agency logo, generic tab title** | `<title>My Account</title>`, generic favicon |

---

## Architecture overview

### Subdomain routing (10-line middleware, no dependencies)

```python
class DomainEnforcementMiddleware:
    """Block cross-domain path access. Portal domain can only reach /my/."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]
        if host == settings.PORTAL_DOMAIN and not request.path.startswith("/my/"):
            return HttpResponse("Not Found", status=404, content_type="text/plain")
        if host == settings.STAFF_DOMAIN and request.path.startswith("/my/"):
            return HttpResponse("Not Found", status=404, content_type="text/plain")
        return self.get_response(request)
```

Settings: `PORTAL_DOMAIN` and `STAFF_DOMAIN` env vars. When not configured, middleware does nothing (graceful degradation — portal still accessible at `/my/` on main domain).

Deployment: Same Django process, same container, same database. Railway: add second custom domain. FullHost: add nginx server_name alias.

### Session isolation (zero code — browser-enforced)

`SESSION_COOKIE_DOMAIN = None` (already the default). Browser scopes the `sessionid` cookie to the exact domain that set it. Portal subdomain and staff subdomain get separate session cookies automatically. Add Django system check `portal.W001` to warn if this setting is changed.

### Middleware stack (only 2 additions, 2 small tweaks)

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.portal.middleware.DomainEnforcementMiddleware",    # NEW
    "apps.portal.middleware.PortalAuthMiddleware",           # NEW
    "konote.middleware.safe_locale.SafeLocaleMiddleware",    # TWEAK: also read participant_user
    "konote.middleware.audit.AuditMiddleware",               # TWEAK: log portal participant_user_id
    "konote.middleware.program_access.ProgramAccessMiddleware",  # No change (auto-skips portal)
    "konote.middleware.terminology.TerminologyMiddleware",       # No change (portal uses terminology too)
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
]
```

### Data isolation (structural, not filtered)

Every portal view uses the same pattern:

```python
# The participant's ClientFile — direct FK, not a query filter
client_file = request.participant_user.client_file

# For sub-object lookups, always constrain to their client_file
target = get_object_or_404(PlanTarget, pk=target_id, client_file=client_file)
```

No `client_id` appears in any portal URL. No queryset filtering — it's a direct FK lookup. Cross-participant data access is structurally impossible.

### request.user vs request.participant_user

For portal requests:
- `request.user` = `AnonymousUser` (Django's auth middleware finds no staff session)
- `request.participant_user` = the `ParticipantUser` instance (set by PortalAuthMiddleware)

This means all existing staff-side decorators (`@login_required`, `@requires_permission`, `@admin_required`) automatically deny portal users. No code changes to staff views needed.

---

## Data model

### New app: `apps/portal/`

```
apps/portal/
    __init__.py
    models.py          # ParticipantUser, PortalInvite, ParticipantJournalEntry, ParticipantMessage, CorrectionRequest
    views.py           # Dashboard, goals, progress, journal, messages, settings
    forms.py           # Login, password change, journal form, message form, MFA setup
    urls.py            # All under /my/
    middleware.py       # DomainEnforcementMiddleware, PortalAuthMiddleware
    backends.py        # authenticate_participant()
    checks.py          # Django system checks (portal.W001, portal.W002)
    templatetags/
        portal_tags.py
    templates/portal/
        base_portal.html       # Standalone (does NOT extend staff base.html)
        login.html
        mfa_setup.html
        consent_flow.html
        dashboard.html
        goals.html
        goal_detail.html
        progress.html
        my_words.html          # "What I've been saying"
        journal.html           # Private journal
        journal_disclosure.html  # One-time privacy notice
        message_to_worker.html
        discuss_next.html      # "What I want to discuss next time"
        correction_request.html
        settings.html
        safety_help.html       # "Staying safe online" (pre-auth, no login required)
    tests/
        test_idor.py           # Automated IDOR test suite
        test_session_isolation.py
        test_xss.py
        test_auth.py
```

### Models

**ParticipantUser** — login account, 1:1 with ClientFile
- UUID primary key (USERNAME_FIELD for Django internals)
- `email_hash` (HMAC-SHA-256 with server-side `EMAIL_HASH_KEY`, for lookup during login — NOT the USERNAME_FIELD). Email must be `.lower()`-normalised before hashing. Implementation: `hmac.new(settings.EMAIL_HASH_KEY, email.lower().encode(), 'sha256').hexdigest()`. Bare SHA-256 is trivially reversible — HMAC with a secret is required.
- `_email_encrypted` (Fernet, for display/password reset)
- `display_name` (preferred name, from ClientFile at invite time)
- `client_file` (OneToOneField — the structural constraint)
- `is_active`, `preferred_language`
- `mfa_method` (totp / email / exempt)
- `totp_secret_encrypted` (Fernet)
- `failed_login_count`, `locked_until`
- `last_login` (Django built-in, but NEVER exposed to staff)

**PortalInvite** — staff-initiated, invite-only access
- `client_file` (FK)
- `invited_by` (FK to staff User)
- `token` (64-char cryptographic, single-use)
- `verbal_code` (optional 4-digit code for in-person verification)
- `consent_screens_shown` (JSON: which screens, timestamps)
- `consent_document_version`
- `status` (pending / accepted / expired / revoked)
- `expires_at` (7 days from creation)

**ParticipantJournalEntry** — private, never seen by staff
- `participant_user` (FK)
- `client_file` (FK — redundant but ensures CASCADE works cleanly)
- `plan_target` (FK, optional — can be general)
- `_content_encrypted` (Fernet)
- `created_at`

**ParticipantMessage** — shared with worker
- `participant_user` (FK)
- `client_file` (FK)
- `message_type`: "general" or "pre_session"
- `_content_encrypted` (Fernet)
- `created_at`
- `archived_at` (pre-session messages archived after next note is recorded)

**CorrectionRequest** — "Something doesn't look right?"
- `participant_user` (FK)
- `client_file` (FK)
- `data_type` (goal / metric / reflection — what they're questioning)
- `object_id` (which specific record)
- `_description_encrypted` (Fernet — their explanation of the issue)
- `status` (pending / discussed / corrected / no_change)
- `staff_response` (optional — what was done)
- `created_at`, `resolved_at`

### Model change to existing app

**MetricDefinition** — add `portal_visibility` field:
```python
portal_visibility = models.CharField(
    max_length=20, default="no",  # Default "no" — staff must explicitly opt in each metric
    choices=[
        ("yes", "Visible in participant portal"),
        ("no", "Hidden from participant portal"),
        ("self_reported", "Only when self-reported"),
    ],
)
```

**Program** — add `portal_display_name` field:
```python
portal_display_name = models.CharField(
    max_length=255, blank=True, default="",
    help_text="Name shown in participant portal. Leave blank to use program name.",
)
```

---

## What participants see (portal-friendly labels)

| KoNote data model term | Portal label | Source |
|----------------------|-------------|--------|
| Plan sections | "Areas I'm working on" | `PlanSection.name` |
| Plan targets | "My goals" | `PlanTarget.client_goal` (their words) |
| Progress descriptors | The actual phrases | "Harder right now", "Something's shifting", etc. |
| Metric values | "How I'm doing" + chart | `MetricValue.value` (where `portal_visibility != "no"`) |
| participant_reflection | "What I said" | `ProgressNote.participant_reflection` |
| participant_suggestion | "What I suggested" | `ProgressNote.participant_suggestion` |
| client_words | "What I said about this goal" | `ProgressNoteTarget.client_words` |
| Completed targets | "Milestones" | PlanTarget with status=completed |

### What participants NEVER see

- `ProgressNote.notes_text` (staff clinical notes)
- `ProgressNote.summary` (staff summary)
- `ProgressNote.engagement_observation` (staff assessment)
- `ProgressNoteTarget.notes` (staff target-specific notes)
- `Alert` (safety alerts)
- `Event` (may contain safety info)
- `GroupSession.notes` (staff observations)
- `GroupSessionHighlight` (staff observations about individuals)
- `ClientDetailValue` (custom field intake data)
- Other participants' data (structurally impossible)
- Other group members' names

---

## Security

### Quick-exit button

On every portal page, fixed-position:
```html
<button id="quick-exit" onclick="quickExit()" aria-label="Leave this page quickly">
    Leave quickly
</button>
```

```javascript
function quickExit() {
    navigator.sendBeacon('/my/emergency-logout/');
    window.location.replace('https://www.google.ca');
}
```

**Limitations (be honest with agencies):** The quick-exit button replaces the current browser history entry but cannot clear browser autocomplete suggestions, synced browsing history (e.g., Chrome signed into a shared Google account), or DNS cache. `sendBeacon` is best-effort — if the network is down, the session may not be destroyed server-side (it will still expire via idle timeout). The "Staying safe online" page (A11) covers how to use private browsing and clear history, but participants most at risk may not find it without staff guidance.

### MFA tiers

| Tier | Method | When to use |
|------|--------|-------------|
| 1 | TOTP (authenticator app) | Default for participants with smartphones |
| 2 | Email one-time code (6-digit, 10-min expiry) | Participants without authenticator apps |
| 3 | Agency admin exemption | Documented reason (cognitive disability, no email/phone) |
| 4 | Staff-assisted login | In-person at agency, short session, agency IP range |

### Login security

- Per-account lockout: 5 failures → 15 min lock
- Per-IP rate limit: 20 failures across any accounts → 30 min IP block
- Timing equalization: dummy `make_password()` on unknown email to prevent enumeration
- No "remember me" option — ever
- Single active session (new login invalidates old)

### Automated security tests (built alongside features, not after)

| Test | Priority | When |
|------|----------|------|
| IDOR on every portal endpoint | Critical | Phase A + every new endpoint |
| Session isolation (staff + portal dual-login) | Critical | Phase A |
| XSS via participant content in staff view | Critical | Phase C |
| CSRF cross-subdomain | High | Phase A |
| Brute force resistance | High | Phase A |
| Timing-based email enumeration | High | Phase A |
| Invite token entropy + expiry | Medium | Phase A |
| Quick-exit session destruction | Medium | Phase A |
| Audit log completeness | Medium | Every phase |

---

## Consent and safety

### Visual consent flow (at invite acceptance)

3-4 simple screens, tapped through one at a time:

1. **"What you'll see"** — your goals, your progress, your own words (with simple illustration)
2. **"What you won't see"** — staff notes, other people's information
3. **"Who sees what you write"** — your journal is private; messages go to your worker; your worker may need to act on safety concerns
4. **"You're in control"** — you can stop using this anytime, ask your worker to remove your account

Each screen: "I understand" button, timestamp recorded, stored in `PortalInvite.consent_screens_shown`.

### Journal privacy disclosure (one-time, before first journal entry)

> **Before you start writing**
>
> These notes are just for you. Your worker won't see them.
>
> In some situations — like a court order — the agency could be required to share records, and these notes could be included. This doesn't happen often, but we want you to know before you start writing.
>
> [I understand, let me write] [Maybe later]

### "Message to My Worker" notice

Shown above the message form:

> Your worker will see this next time they check. **This is not for emergencies.**
>
> If you need help right now:
> - **Crisis line:** 1-833-456-4566 (Talk Suicide Canada)
> - **211 Ontario:** dial 211 for community services

### Correction request soft step

When participant taps "Something doesn't look right?":

> Would you like to talk about this with your worker at your next session?
>
> [Yes, I'll bring it up] [I'd like to submit a request now]

"I'll bring it up" = no record created, just a reminder shown in their portal. "Submit a request" = creates a CorrectionRequest visible to staff.

---

## Account lifecycle

| Event | Portal action |
|-------|-------------|
| Staff invites participant | PortalInvite created (7-day expiry) |
| Participant accepts invite | ParticipantUser created, MFA configured |
| Participant logs in | Session created, audit logged |
| Client status → discharged | Portal account deactivated immediately |
| Client erased | Portal account deleted (CASCADE) |
| Client merged | Portal account transfers to surviving ClientFile |
| Staff revokes access | Account deactivated, invite set to "revoked" |
| 90 days of inactivity | Account deactivated (reactivation requires new invite) |
| Participant requests removal | Account deactivated, staff notified |

---

## Implementation phases

**Phase A + B = Minimum Lovable Product (MLP).** These two phases together are a complete, shippable product — participants can log in, see their goals, progress, and own words. If adoption is low after A+B, Phases C and D should not be built. Phases C and D are enhancements, not promises.

### Phase A: Foundation

**Goal:** Portal shell — you can log in, see your name, and log out. Secure infrastructure in place.

| Task | Details |
|------|---------|
| A1: Feature toggle | Add `features.participant_portal` (off by default). Gate all portal functionality. |
| A2: Portal Django app | Create `apps/portal/` with models, middleware, URLs, templates. |
| A3: ParticipantUser model | UUID PK, email_hash lookup, Fernet-encrypted email, MFA fields, account lockout. |
| A4: PortalInvite model | Token generation, verbal code, consent screen tracking, expiry. |
| A5: Domain enforcement middleware | 10-line middleware. Settings: `PORTAL_DOMAIN`, `STAFF_DOMAIN`. |
| A6: Portal auth middleware | `request.participant_user` from session. Login/logout views. |
| A7: MFA setup flow | TOTP setup with QR code. Email code fallback. Admin exemption flag. **"Lost phone" recovery:** staff can reset a participant's MFA method via the portal management UI, allowing them to set up a new authenticator on next login. No printed recovery codes (DV risk — physical card reveals portal's existence). |
| A8: Visual consent flow | 3-4 screen walkthrough at invite acceptance. |
| A9: Portal login page | Light agency branding, generic `<title>`, generic favicon. |
| A10: Quick-exit button | Fixed-position on every page. sendBeacon + location.replace. |
| A11: "Staying safe online" page | Pre-auth, no login required. How to use private browsing, clear history. |
| A12: Django system checks | `portal.W001` (SESSION_COOKIE_DOMAIN), `portal.W002` (program aliases). |
| A13: Audit logging extension | AuditMiddleware logs `participant_user_id` + `portal_access=True`. |
| A14: SafeLocaleMiddleware tweak | Read `participant_user.preferred_language` for portal requests. |
| A15: Staff-side "Invite to Portal" button | On client detail page. Generates invite link. Consent confirmation. **Must check for existing portal account** — if client already has one, show "already has access" with option to resend invite or reactivate. |
| A16: Program portal_display_name field | Add field to Program model. Smart default with keyword warning. |
| A17: Migrations | makemigrations + migrate for all new models and field additions. |
| A18: Security test suite | IDOR tests, session isolation test, CSRF cross-domain test, brute force test, timing test. |
| A19: Basic dashboard | Greeting with preferred name. "Portal is being set up" placeholder for future content. |
| A20: Self-service password reset | Email-based code flow (reuses MFA Tier 2 infrastructure). |

| A21: Session timeout warning | At 25 minutes idle, show "Are you still here?" modal with "I'm still here" button. Prevents data loss for slow readers or interrupted users. |
| A22: Staff-side "Reset MFA" | In portal management UI: button to reset a participant's MFA method so they can re-enrol on next login. Needed for "lost phone" recovery. |

**Phase A exit criterion:** Before locking Phase B priorities, usability-test login + dashboard with 3-5 real participants at a pilot agency. Their feedback shapes Phase B.

**Test:** Staff can invite a participant. Participant accepts, sets up MFA, sees dashboard with their name. Logging in on portal doesn't affect staff session. IDOR tests pass.

### Phase B: Core Value

**Goal:** Participant can see their goals, progress, and own words. This is the reason the portal exists.

| Task | Details |
|------|---------|
| B1: MetricDefinition.portal_visibility | Add field. Migration. Admin UI to configure. |
| B2: Dashboard redesign | Progressive disclosure: greeting + one highlight + nav links. |
| B3: "My Goals" page | Plan sections as "Areas I'm working on". Targets with `client_goal` text. |
| B4: Goal detail page | Target name, description, client_goal. Progress descriptor timeline. Metric chart. |
| B5: "My Progress" page | Chart.js charts for portal-visible metrics. Start value → current value. |
| B6: "What I've been saying" page | `participant_reflection` + `client_words` from progress notes, in date order. |
| B7: Milestones | Completed plan targets displayed as achievements. |
| B8: "New since last visit" banner | Show count of new data since last login. |
| B9: Correction request (soft step) | "Something doesn't look right?" → discuss or formal request. |
| B10: CorrectionRequest model | Migration. Staff-side list view for pending requests. |
| B11: Participant-friendly language | All labels at Grade 6 reading level. No clinical terminology. |
| B12: Bilingual support | All portal strings in {% trans %} / {% blocktrans %}. FR translations. |
| B13: IDOR tests for new endpoints | Every new URL tested with second participant's object IDs. |
| B14: Staff-side portal reminder | After recording a progress note for a participant who has portal access, show brief reminder: "Reminder: [Name] has portal access — their updated progress will be visible next time they log in." Drives re-engagement through the existing worker relationship. |

**Test:** Participant sees their goals with their own words. Progress charts show metrics (respecting portal_visibility). "What I've been saying" shows their reflections from sessions. Correction request creates a pending item in staff view.

### Phase C: Participant Voice

**Goal:** Participants can write — private journal, messages to worker, pre-session prompts.

| Task | Details |
|------|---------|
| C1: ParticipantJournalEntry model | Migration. Encrypted content. Optional link to plan target. |
| C2: Journal privacy disclosure | One-time screen before first entry. |
| C3: Journal page | Write, view history. Clear "only you can see this" framing. |
| C4: ParticipantMessage model | Migration. "general" + "pre_session" types. Encrypted. |
| C5: "Message to My Worker" page | Form with duty-to-act notice + crisis resources. |
| C6: "What I want to discuss next time" | Pre-session prompt form. |
| C7: Staff-side message display | Inline banner on client detail page. "Participant wrote this" label. |
| C8: Staff-side pre-session display | Inline at top of client page before session. Auto-archives after next note. |
| C9: XSS security tests | Script injection in journal + message content, verified escaped in staff view. |
| C10: Message worker assignment | If worker leaves, messages route to successor or PM. |
| C11: No read receipts | Explicitly: staff view never sends "read" signal to participant. |

**Test:** Participant writes journal entry — not visible in staff view. Participant sends message — appears in staff client view with "Participant wrote this" label. Pre-session prompt appears before worker opens client record. XSS payloads are escaped.

### Phase D: Polish, Safety, and Groups

**Goal:** Production-ready for pilot agencies. Lifecycle automation. Accessibility audit.

| Task | Details |
|------|---------|
| D1: 90-day inactivity deactivation | Management command (run via cron/scheduled task). |
| D2: Account deactivation on discharge | Signal on ClientFile status change. |
| D3: Account transfer on client merge | Extend merge logic to handle portal_account. |
| D4: Erasure workflow extension | Include journal entries + messages in erasure. |
| D5: Staff-side "Manage portal access" UI | View invites, active accounts, revoke access. |
| D6: Staff-assisted login (MFA Tier 4) | Short session, agency IP validation, audit logged. |
| D7: PWA manifest | "Add to home screen" for mobile. |
| D8: WCAG 2.2 AA accessibility audit | Focus on population needs: low literacy, motor difficulty, older devices. |
| D9: Full pen test suite | All 10 categories from the automated test plan. |
| D10: Group visibility (optional, alias-dependent) | If agencies request it: group names with aliases, no member names. |
| D11: Portal usage analytics (agency-only) | Aggregate stats (how many participants use portal). Never per-participant. |
| D12: Training material finalization | Staff guide, participant guide, video walkthroughs, ethics discussion guide. |

---

## Deployment

### Railway

- Add second custom domain in Railway dashboard (e.g., `myjourney.agencyname.org`)
- Both domains point to same service
- Add env vars: `PORTAL_DOMAIN`, `STAFF_DOMAIN`, `EMAIL_HASH_KEY` (cryptographic secret for HMAC email hashing)
- Add `PORTAL_DOMAIN` to `ALLOWED_HOSTS`
- SSL handled by Railway automatically for both domains

### FullHost (Jelastic)

- Add `server_name` alias in nginx for portal subdomain
- Both subdomains proxy to same Docker container
- SSL: Let's Encrypt covers both subdomains (add SAN or separate cert)
- Add env vars same as Railway (`PORTAL_DOMAIN`, `STAFF_DOMAIN`, `EMAIL_HASH_KEY`)

### Data residency

Both deployment targets store data in Canada (Railway: Montreal region; FullHost: Canadian data centre). Any future hosting migration must maintain Canadian data residency for PHIPA/PIPEDA compliance. No third-party analytics, CDN, or external service may process portal PII.

### For agencies without subdomain

Portal works at `/my/` on the main domain. No domain enforcement (middleware does nothing when `PORTAL_DOMAIN` is empty). Session cookies still isolate staff/portal because they use different session keys (`_portal_participant_id` vs Django's default user session). Less secure than subdomain (shared CSRF cookies), but functional for agencies that can't configure DNS.

---

## What this costs (operational summary for agencies)

| Category | One-time | Ongoing |
|----------|----------|---------|
| Admin: configure program aliases | 5 min per program | Rare |
| Admin: enable portal feature toggle | 1 min | One-time |
| Staff: invite a participant | 10 min (consent + MFA setup) | Per participant |
| Staff: review correction requests | 5 min each | Occasional |
| Staff: read participant messages | 2 min each | As received |
| Staff: revoke access (safety) | 2 min | Rare but urgent |
| Participant: forgot password | Self-service | N/A (no staff time) |
| Participant: locked account | Admin toggle | Occasional |

---

## Known limitations

These are documented trade-offs, not bugs. They do not need to be fixed before shipping.

- **Fernet key rotation:** If the encryption key is compromised or needs rotation, every encrypted field across 5+ models needs re-encryption via a data migration. No automated rotation mechanism exists. Mitigated by standard key management practices (env vars, not in code).
- **Correction requests are informal:** The portal's "Something doesn't look right?" button is a conversation starter, not a formal PHIPA s.55 correction request process. Formal correction requests and refusals should follow the agency's existing privacy policy, off-system. The IPC complaint right is documented in the agency's privacy policy, not in the portal software.
- **Mandatory reporting:** "Message to My Worker" includes a duty-to-act notice, but mandatory reporting workflows are a professional obligation of the worker, not a software feature. Training materials should note: "Treat messages from participants the same as in-person disclosures with respect to your mandatory reporting obligations."
- **90-day deactivation:** Deactivating a login does not violate PHIPA access rights (participants can still request information through the agency). Journal entries are never deleted on deactivation. Reactivation through a simplified process (not a full new invite) is a nice-to-have for Phase D.

---

## Reference documents

| Document | Purpose |
|----------|---------|
| [participant-portal-design.md](participant-portal-design.md) | Original design with data model details and wireframe |
| [participant-portal-expert-review.md](participant-portal-expert-review.md) | Panel 1: privacy law, security architecture, social service tech, trauma-informed UX |
| [participant-portal-expert-review-2.md](participant-portal-expert-review-2.md) | Panel 2: Django implementation, nonprofit operations, pen testing, social work ethics |
| Panels 3-4 (inline, 2026-02-09) | Panel 3: operations, Django production, digital equity, Canadian privacy law, failure modes. Panel 4: meta-review stress-testing Panel 3 findings — confirmed 9 changes, rejected 6 over-engineered recommendations. Results incorporated into this document. |
