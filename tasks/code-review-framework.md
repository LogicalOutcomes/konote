# KoNote — Independent Code Review Framework

**Version:** 2.0
**Created:** 2026-02-06
**Updated:** 2026-03-04
**Purpose:** Structured prompts for multi-dimensional code review using AI tools or human reviewers

---

## Why This Framework Exists

KoNote handles sensitive client data for nonprofits. A single security review is not enough — the codebase has multiple dimensions of quality that each require focused attention. This framework defines **11 review dimensions**, a **two-tier review model** (continuous + periodic), and **reusable prompts** that work with any AI code review tool.

The goal: any agency deploying KoNote can run these reviews themselves, and the development team can use them as ongoing quality gates.

---

## Part 1: Review Dimensions

### The 11 Dimensions

Each dimension addresses a different aspect of application quality. They are ordered by risk — the first six relate to data safety; the last five relate to operational quality.

| # | Dimension | Why It Matters for KoNote | Risk Level |
|---|-----------|---------------------------|------------|
| 1 | **Security (OWASP)** | Handles PII; target for data breaches | Critical |
| 2 | **Data Privacy (PIPEDA/PHIPA)** | Canadian privacy law; PHIPA cross-program consent; breach notification within 72 hours | Critical |
| 3 | **Encryption & Key Management** | All PII encrypted at rest; per-tenant keys; key compromise = full exposure | Critical |
| 4 | **Access Control (RBAC)** | Program-scoped data isolation; role hierarchy; portal auth; public survey access | Critical |
| 5 | **AI Governance** | LLM integration sends data externally; PII must never reach external APIs | Critical |
| 6 | **Audit Trail Integrity** | Compliance requirement; must be tamper-resistant | High |
| 7 | **Deployment Reliability** | Docker, entrypoint, multi-phase migration healing — failure = downtime | High |
| 8 | **Accessibility (WCAG 2.2 AA)** | AODA compliance; users include staff and participants with disabilities | High |
| 9 | **Bilingual Compliance (EN/FR)** | Official Languages Act; Ontario FLSA; funder requirements; WCAG 3.1.2 | High |
| 10 | **Code Quality & Maintainability** | Nonprofit project; must be maintainable by non-specialists | Medium |
| 11 | **Dependency Health** | Outdated packages = CVEs; supply chain risk | Medium |

### Dimensions NOT Included (and Why)

| Excluded | Reason |
|----------|--------|
| Performance / scalability | Documented ceiling of ~2,000 clients; premature to optimise beyond that |
| Disaster recovery / backup | Infrastructure-level concern, not code review (see OVHcloud DRR for backup strategy) |
| Documentation quality | Already covered by separate documentation review process |
| User Experience | Covered by `tasks/UX-REVIEW.md` framework |

These can be added as the application matures.

---

## Part 2: How Review Prompts Are Structured

Every review prompt follows the same five-section structure. This makes them portable across AI tools (Claude, GPT, Jules, Copilot, etc.) and usable by human reviewers.

### Prompt Anatomy

```
1. ROLE DEFINITION
   Who the reviewer is pretending to be (persona + expertise level)

2. APPLICATION CONTEXT
   What KoNote is, its threat model, tech stack, and constraints

3. SCOPE
   Which files to review, which to skip, and what's out of bounds

4. CHECKLIST
   Specific items to verify (pass/fail or scored)

5. OUTPUT FORMAT
   Exactly what the report should look like
```

### Design Decisions

**Checklist-style, not open-ended.** Open-ended prompts ("review this codebase for security issues") produce vague, inconsistent results. Checklists produce comparable results across reviewers and over time.

**Context about the threat model.** Every prompt includes a brief description of who the attackers are and what data is at risk. Without this, reviewers focus on theoretical vulnerabilities instead of realistic ones.

**Scoped to specific files.** Full-codebase reviews are shallow. Each dimension prompt lists the 5-15 most relevant files. A reviewer who reads those files deeply finds more than one who skims everything.

**Standardised output format.** Every prompt requests the same severity levels (Critical / High / Medium / Low) and the same finding format (Location, Issue, Impact, Fix). This makes findings comparable across dimensions and over time.

---

## Part 3: Two-Tier Review Model

### Tier 1: Continuous (Every PR or Weekly)

**Purpose:** Catch regressions and common mistakes before they reach production.
**Who runs it:** Developer (or CI/CD pipeline if automated).
**Time budget:** 15-30 minutes per review.

| Check | Tool | What It Catches |
|-------|------|-----------------|
| `python manage.py check --deploy` | Django | Missing security middleware, debug mode, insecure cookies |
| `python manage.py security_audit --json --fail-on-warn` | KoNote custom | Encryption config, RBAC, audit logging, plaintext PII |
| `python manage.py translate_strings --dry-run` | KoNote custom | New untranslated strings, empty translations (do NOT use `grep 'msgstr ""'` — .po multi-line strings and plural forms produce false positives) |
| `pip-audit` | pip-audit | Known CVEs in dependencies |
| `pytest` (full suite) | pytest | RBAC regressions, encryption round-trip, demo data isolation |
| HTMX endpoint spot-check | Manual / AI | New HTMX endpoints respect CSRF and RBAC |
| Public endpoint spot-check | Manual / AI | Survey/portal endpoints enforce rate limits and input validation |

**Tier 1 should cover:**
- All 11 Gate Checks from the security review plan (G1-G11)
- Dependency CVE scanning
- Test suite pass rate
- Any new endpoints have corresponding permission tests
- Translation coverage (no regressions in French strings)
- AI endpoints enforce rate limits and PII scrubbing

**Tier 1 should NOT cover:**
- Deep architecture review
- Privacy compliance assessment
- UX or accessibility audit
- Threat modelling

### Tier 2: Periodic Deep Review (Quarterly or Before Major Releases)

**Purpose:** Thorough assessment of one or more dimensions in depth.
**Who runs it:** Independent reviewer (AI tool with fresh context, external consultant, or internal team member who didn't write the code).
**Time budget:** 2-4 hours per dimension.

| Review | Frequency | Prompt to Use |
|--------|-----------|---------------|
| Security (OWASP + RBAC) | Quarterly | Prompt A (below) |
| Data Privacy (PIPEDA/PHIPA) | Quarterly | Prompt B (below) |
| AI Governance | Quarterly | Prompt E (below) |
| Accessibility (WCAG 2.2 AA) | Before each release | Prompt C (below) |
| Deployment Reliability | After infrastructure changes | Prompt D (below) |
| Bilingual Compliance | Before each release | Prompt F (below) |
| Code Quality | Semi-annually | (Prompt in development) |
| UX Review | Before each release | Use existing `tasks/UX-REVIEW.md` |
| Dependency Health | Quarterly | Automated with `pip-audit` + manual review |

**Trigger events that require an immediate Tier 2 review:**
- Any change to `konote/encryption.py` or encrypted model fields
- Any change to RBAC middleware or authentication views
- Any change to `entrypoint.sh`, `Dockerfile`, or migration logic
- Any new dependency added to `requirements.txt`
- Any new endpoint that accesses client data
- Any change to `konote/ai.py`, `konote/ai_views.py`, or AI prompts
- Any change to portal authentication (`apps/portal/backends.py`, `apps/portal/middleware.py`)
- Any change to public survey views (`apps/surveys/public_views.py`)
- Any change to multi-tenancy routing (`konote/db_router.py`, `apps/tenants/`)
- Any change to data export commands (`apps/exports/`, `apps/reports/export_engine.py`)

---

## Part 4: Sample Prompts

---

### Prompt A: Security Review (OWASP + RBAC + Encryption)

This is the most comprehensive prompt. It combines three critical dimensions into one because they overlap heavily.

```markdown
## Role

You are a senior application security engineer conducting a white-box security
review. You have expertise in Django security, OWASP Top 10, healthcare
data protection, and multi-surface authentication (staff SSO + participant
portal + public unauthenticated forms).

## Application Context

KoNote is a Django 5 web application that stores sensitive client information
(names, dates of birth, progress notes, outcome ratings, survey responses,
family/circle relationships) for nonprofit social service agencies in Canada.
Each agency runs its own instance.

**Three authentication surfaces:**
- Staff UI: Azure AD SSO (primary) or local Argon2 (fallback), with optional
  MFA (TOTP). Session-based. All staff routes behind ProgramAccessMiddleware.
- Participant Portal: Separate ParticipantUser model, email + Argon2 password.
  HMAC-hashed email for O(1) lookup. Portal users see only their own data.
- Public Survey Forms: No authentication. Token-based access via /s/<token>/.
  Rate-limited. Optional single-response cookie. Anonymous responses supported.

**Threat model:**
- PRIMARY THREAT: Unauthorised access by authenticated users who should not
  see certain clients (program-scoped data isolation failure)
- SECONDARY THREAT: External attacker exploiting web vulnerabilities
  (injection, XSS, CSRF, authentication bypass)
- TERTIARY THREAT: Data exposure through infrastructure compromise
  (database breach mitigated by field-level encryption)
- QUATERNARY THREAT: PII leakage through AI/LLM integration (data sent to
  external OpenRouter API must be de-identified first)
- QUINARY THREAT: Cross-surface authentication confusion (staff session used
  to access portal routes, or portal user accessing staff routes)
- OUT OF SCOPE: Physical access, social engineering, denial of service

**Key architectural decisions:**
- All PII encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256)
- Per-tenant encryption keys (multi-tenancy foundation)
- Encryption key loaded from environment variable, never in code
- MFA secrets encrypted at rest (mfa_secret_encrypted field)
- RBAC enforced at middleware level (ProgramAccessMiddleware) — users only
  access clients in their assigned programs
- PHIPA cross-program consent enforcement on progress notes
- DV-safe fields protect domestic violence survivors (restricted access)
- Audit logs stored in a separate database with INSERT-only permissions
- Server-rendered Django templates + HTMX (no JavaScript framework)
- CSP headers restrict script and style sources
- AI endpoints use PII scrubbing before sending to external LLM
- Two-tier AI feature toggles (tools-only vs. participant-data)
- Suppression thresholds on funder reports to prevent re-identification

## Scope

**Read these files first (critical path):**
- konote/encryption.py
- konote/middleware/program_access.py
- konote/middleware/audit.py
- konote/settings/base.py
- konote/settings/production.py
- apps/auth_app/views.py
- apps/auth_app/models.py
- apps/clients/models.py
- apps/clients/views.py
- apps/clients/forms.py
- apps/portal/models.py
- apps/portal/backends.py
- apps/portal/middleware.py
- apps/portal/views.py
- konote/ai.py
- konote/ai_views.py

**Then review these (high priority):**
- apps/notes/views.py
- apps/notes/models.py
- apps/plans/views.py
- apps/reports/views.py
- apps/reports/export_engine.py
- apps/reports/pii_scrub.py
- apps/clients/erasure_views.py
- apps/clients/data_access_views.py
- apps/clients/dv_views.py
- apps/surveys/models.py
- apps/surveys/public_views.py
- apps/surveys/views.py
- apps/circles/models.py
- apps/circles/views.py
- apps/circles/helpers.py
- apps/programs/models.py
- apps/programs/access.py
- apps/tenants/models.py
- apps/events/views.py
- apps/communications/services.py
- apps/reports/management/commands/export_agency_data.py
- konote/db_router.py
- konote/urls.py
- static/js/app.js
- static/js/portal.js

**Out of scope:** venv/, locale/, docs/, .mo files, migration files (unless
they contain data manipulation logic)

## Checklist

### Gate Checks (all must pass — any failure = FAIL verdict)

| Gate | Requirement |
|------|-------------|
| G1 | No Critical vulnerabilities found |
| G2 | All PII fields use _*_encrypted BinaryField + property accessor |
| G3 | ProgramAccessMiddleware in MIDDLEWARE and enforcing on all client routes |
| G4 | AuditMiddleware logging to separate "audit" database |
| G5 | Session cookies: HttpOnly=True, Secure=True, SameSite=Lax |
| G6 | DEBUG=False in production settings |
| G7 | FIELD_ENCRYPTION_KEY loaded from environment (not hardcoded) |
| G8 | Portal authentication is fully separate from staff authentication |
| G9 | Public survey endpoints enforce rate limiting |
| G10 | AI endpoints never send raw PII to external APIs |
| G11 | Management commands (export_agency_data, etc.) respect demo/real data boundaries |

### OWASP Top 10 Checks

For each, note: PASS / FAIL / NOT APPLICABLE, with file:line evidence.

- A01 Broken Access Control: Can User A access Client X in User B's program?
  Can a portal user access another participant's data? Can a public survey
  token be reused to access other surveys?
- A02 Cryptographic Failures: Any weak algorithms? Key exposed in logs/errors?
  MFA secrets properly encrypted? Portal email HMAC using constant-time
  comparison?
- A03 Injection: Any raw SQL with user input? Any eval/exec? Template |safe
  with user data? AI prompt injection possible via user-supplied text?
- A04 Insecure Design: Does failure grant access? Is least privilege applied?
  Do feature toggles fail-closed (AI disabled if toggle missing)?
- A05 Security Misconfiguration: ALLOWED_HOSTS, CSP, security headers?
  X-Frame-Options on portal? CORS on public survey endpoints?
- A06 Vulnerable Components: Check requirements.txt versions against known CVEs
- A07 Auth Failures: Rate limiting on login (staff and portal)? Generic error
  messages? Session fixation? MFA bypass possible?
- A08 Data Integrity: CSRF on all forms? SRI on CDN scripts? CSRF on HTMX
  endpoints? Public survey forms use CSRF tokens?

### RBAC-Specific Attack Scenarios

Test each scenario by tracing the code path:

1. IDOR: Staff user calls GET /participants/999/ where client 999 is in a
   different program — is this blocked? Where?
2. Vertical escalation: Front desk user submits POST to a staff-only endpoint —
   is this blocked? Where?
3. Admin bypass: Admin user (no program roles) tries to access
   /participants/123/ — is this blocked? Where?
4. Executive bypass: Executive-only user tries to access individual client
   data — is this blocked? Where?
5. HTMX abuse: Can an attacker craft an HTMX request that bypasses middleware?
6. Note access via ID: User accesses /notes/456/ for a note belonging to a
   client in another program — is this blocked?
7. Portal crossover: Portal user attempts to access staff routes (/admin/,
   /participants/) — is this blocked?
8. Staff-to-portal: Staff user attempts to access portal routes (/my/) using
   staff session — does this grant portal access?
9. Circle visibility: User views a circle containing members from programs
   they don't have access to — can they see those members' details?
10. DV-safe bypass: User without DV access tries to view a DV-flagged client's
    restricted fields — is this blocked?
11. Public survey enumeration: Attacker tries sequential /s/<token>/ values
    to discover active surveys — are tokens unpredictable?
12. Cross-program note access: Staff user views a progress note from another
    program without PHIPA consent — is consent enforcement applied?
13. Management command data leak: export_agency_data includes demo records
    in production export — does it filter correctly?
14. Funder report suppression: Program has only 3 participants — does the
    suppression threshold prevent re-identification? Can an admin set the
    threshold below a safe minimum (e.g., n<5)?
15. ODK sync boundary: Staff user configures field collection for a program,
    then syncs data from ODK Central — does the sync validate that the
    syncing user has program access to the records being imported?

### Encryption Checks

1. List every model field that stores PII — is it encrypted? Include:
   ClientFile, ProgressNote, Circle, ParticipantUser, SurveyResponse,
   Registration, Communication models
2. Search for any PII logged to stdout/stderr (check logger.* calls)
3. Check if form validation errors echo back submitted PII
4. Check if [decryption error] marker could appear in user-facing templates
5. Verify key rotation command works without data loss (review the code path)
6. Verify MFA secrets are encrypted at rest (mfa_secret_encrypted field)
7. Verify portal email addresses use HMAC hashing for lookup
8. Verify circle names are encrypted (reveals family relationships)
9. Check that AI PII scrubber (pii_scrub.py) does not miss any PII patterns

## Output Format

### Executive Summary
Gate Check Status: PASS / FAIL
Maturity Score: XX/100 (use the scoring from tasks/security-review-plan.md)
Production Ready: Yes / No / With Fixes
Critical Issues: count
High Issues: count
Medium Issues: count
Low Issues: count

### Gate Check Results Table
(one row per gate, status + evidence)

### Findings

For each finding:

**[SEVERITY-NUMBER] Title**
- Location: file.py:line_number
- Issue: What is wrong
- Impact: What an attacker could achieve
- Fix: Specific code change needed
- Test: How to verify the fix works

### Regression Tests Needed
Table of findings that need automated tests added

### Recommendations
Improvements that are not findings but would strengthen the security posture
```

---

### Prompt B: Data Privacy (PIPEDA/PHIPA Compliance)

```markdown
## Role

You are a Canadian privacy compliance specialist with expertise in PIPEDA
(Personal Information Protection and Electronic Documents Act), PHIPA
(Personal Health Information Protection Act), and Ontario's AODA. You
understand how privacy law applies to nonprofit social service agencies
handling client records, including cross-program clinical data sharing
and participant-facing portals.

## Application Context

KoNote is used by Canadian nonprofits to manage participant outcomes —
tracking client progress, recording session notes, and generating reports
for funders. It stores the following PII:

- Client names (first, middle, last, preferred) — encrypted
- Dates of birth — encrypted
- Progress notes (narrative text about sessions) — encrypted
- Outcome ratings (numerical scores on validated scales)
- Custom demographic fields (configurable per agency)
- Circle/family network names — encrypted (reveals relationships)
- Survey responses (may contain narrative text) — partially encrypted
- Participant portal accounts (email, password hash)
- Staff email addresses
- Registration submissions (name, email, phone)
- Journal entries (participant self-authored) — encrypted
- Communication records (messages sent to participants)
- DV-safe indicators (domestic violence risk flags)
- Service episode records (enrollment dates, status changes)

**Regulatory context:**
- PIPEDA applies to commercial activities by nonprofits
- PHIPA applies if the nonprofit provides health services — cross-program
  clinical note sharing requires explicit consent
- Ontario nonprofits must also comply with AODA (accessibility)
- Breach notification is mandatory within 72 hours under PIPEDA
- Organisations must designate a privacy officer
- Data access requests must be responded to within 30 days (PIPEDA)

**Architecture relevant to privacy:**
- Field-level encryption (Fernet/AES) on all PII listed above
- Per-tenant encryption keys (multi-tenancy foundation)
- Separate audit database (INSERT-only) logging all data access
- Program-scoped RBAC (staff only see clients in their programs)
- PHIPA cross-program consent enforcement on progress notes
  (see apps/programs/access.py: apply_consent_filter,
  check_note_consent_or_403)
- Tiered data erasure (anonymise / purge / full erasure)
- Demo/real data separation (demo users never see real clients)
- Consent capture before data collection
- Data retention tracking with expiry dates
- Export controls with audit trail
- DataAccessRequest workflow for PIPEDA right-of-access
- DV-safe field restrictions for domestic violence protection
- AI PII scrubbing before external LLM calls
- Suppression thresholds on funder reports to prevent re-identification
- Participant portal: participants can view their own plans, journal,
  and messages — but NOT other participants' data
- Public survey forms: anonymous responses supported; respondent name
  optional; single-response cookie option

## Scope

**Files to review:**
- apps/clients/models.py (client data model, encryption, consent fields,
  DV-safe, service episodes)
- apps/clients/erasure_views.py (data erasure workflow)
- apps/clients/data_access_views.py (PIPEDA data access request workflow)
- apps/clients/forms.py (consent capture, data collection)
- apps/clients/dv_views.py (domestic violence protection)
- apps/notes/models.py (progress note storage, encryption)
- apps/programs/access.py (PHIPA consent enforcement logic)
- apps/portal/models.py (participant accounts, journal entries)
- apps/portal/views.py (what participants can see)
- apps/surveys/models.py (survey responses, anonymous option)
- apps/surveys/public_views.py (public survey data collection)
- apps/circles/models.py (family/network relationships)
- apps/registration/models.py (self-service registration, PII)
- apps/registration/views.py (registration data handling)
- apps/reports/views.py (data export, what PII leaves the system)
- apps/reports/export_engine.py (unified export pipeline)
- apps/reports/pii_scrub.py (PII removal before AI)
- apps/reports/funder_report.py (aggregated reporting, suppression)
- apps/reports/management/commands/export_agency_data.py (bulk export)
- apps/communications/models.py (messages to participants)
- apps/communications/services.py (message delivery)
- apps/audit/models.py (what is logged, retention)
- konote/middleware/audit.py (what triggers logging)
- konote/ai.py (what data is sent to external LLM)
- konote/ai_views.py (AI endpoint data handling)
- konote/encryption.py (encryption implementation)
- konote/settings/base.py (session, cookie, security config)
- templates/ (check for PII in page source, error messages)
- docs/privacy-policy-template.md (provided template adequacy)

## Checklist

### PIPEDA Principle 1: Accountability
- [ ] Is there a designated privacy contact? (check docs, settings)
- [ ] Are privacy policies provided to agencies? (check templates)
- [ ] Is there a documented process for handling privacy complaints?
- [ ] Is there a data processing agreement template for agencies using
      AI features (data sent to OpenRouter)?

### PIPEDA Principle 2: Identifying Purposes
- [ ] Is the purpose of each PII field documented?
- [ ] Are purposes communicated to data subjects before collection?
- [ ] Is any PII collected without a stated purpose?
- [ ] Are survey response purposes communicated to respondents?
- [ ] Is the purpose of portal data collection (journal, messages) clear?

### PIPEDA Principle 3: Consent
- [ ] Is consent captured before PII is stored?
- [ ] What type of consent? (express, implied, opt-out)
- [ ] Can consent be withdrawn? What happens to the data?
- [ ] Is consent withdrawal logged in the audit trail?
- [ ] Is there separate consent for each processing purpose?
- [ ] Is PHIPA consent captured for cross-program note sharing?
- [ ] Can PHIPA consent be revoked? What happens to shared notes?
- [ ] Do public surveys clearly state how responses will be used?
- [ ] Is consent for AI processing separate from general consent?
- [ ] Do participants consent to portal data collection on registration?

### PIPEDA Principle 4: Limiting Collection
- [ ] Is all collected PII necessary for the stated purpose?
- [ ] Are there fields that could be removed or made optional?
- [ ] Could any fields be anonymised rather than stored identifiably?
- [ ] Do surveys collect only necessary respondent information?
- [ ] Is the "respondent name" field on public surveys truly optional?

### PIPEDA Principle 5: Limiting Use, Disclosure, and Retention
- [ ] Is PII used only for the purpose it was collected?
- [ ] Are retention periods defined and enforced?
- [ ] Does expired data actually get purged? (check the code path for
      execute_pending_erasures and alert_expired_retention)
- [ ] Are exports limited to authorised users?
- [ ] Do exports contain only necessary PII?
- [ ] Does export_agency_data correctly exclude demo data?
- [ ] Do funder reports use suppression thresholds to prevent
      re-identification of individuals in small groups?
- [ ] Is AI-processed data (sent to OpenRouter) limited to de-identified
      content only?
- [ ] Are portal communications (messages) retained appropriately?
- [ ] Are inactive portal accounts deactivated?
      (check deactivate_inactive_portal_accounts command)

### PIPEDA Principle 6: Accuracy
- [ ] Can data subjects view their own information?
      (check portal plan viewing, journal entries)
- [ ] Can data subjects request corrections?
- [ ] Are corrections logged?

### PIPEDA Principle 7: Safeguards
- [ ] Is PII encrypted at rest? (list all fields and verify — include
      Circle names, portal emails, journal entries, survey responses)
- [ ] Is PII encrypted in transit? (HTTPS, TLS config)
- [ ] Are access controls proportional to sensitivity?
      (DV-safe fields have highest restriction)
- [ ] Is there physical/organisational security guidance for deployers?
- [ ] Are per-tenant encryption keys properly isolated?
- [ ] Is MFA available for staff accounts?

### PIPEDA Principle 8: Openness
- [ ] Is the privacy policy accessible to data subjects?
- [ ] Does it describe what PII is collected and why?
- [ ] Does it describe who has access?
- [ ] Does it describe retention periods?
- [ ] Does it describe AI data processing (if AI features enabled)?
- [ ] Is privacy information available in both official languages?

### PIPEDA Principle 9: Individual Access
- [ ] Can clients request a copy of their data?
      (check DataAccessRequest workflow and export feature)
- [ ] Can clients request erasure? (check erasure workflow)
- [ ] Is the erasure process complete? (no orphaned data — check circles,
      survey responses, portal accounts, communications)
- [ ] Are erasure actions logged?
- [ ] Is there a response time commitment (30 days under PIPEDA)?
- [ ] Does erasure extend to AI-processed data? (already de-identified,
      but verify no cached copies)

### PIPEDA Principle 10: Challenging Compliance
- [ ] Is there a documented complaint process?
- [ ] Are complaints tracked?

### PHIPA Cross-Program Consent (if health services)
- [ ] Does apply_consent_filter correctly restrict cross-program notes?
- [ ] Does check_note_consent_or_403 block access to non-consented notes?
- [ ] Are consent settings per-agency and per-participant?
- [ ] Is the consent enforcement fail-closed (block if consent unclear)?
- [ ] Are exemptions documented (aggregate counts, de-identified reports,
      plan views, portal views)?

### Breach Readiness
- [ ] Can the system detect suspicious access patterns?
- [ ] Can affected records be identified within 72 hours?
- [ ] Is there an incident response procedure?
- [ ] Are there alerting mechanisms for anomalous activity?
- [ ] Can per-tenant keys be rotated independently after a breach?

## Output Format

### Compliance Summary

| PIPEDA Principle | Status | Notes |
|-----------------|--------|-------|
| 1. Accountability | Compliant / Partial / Non-Compliant | |
| 2. Identifying Purposes | ... | |
| ... | ... | |
| 10. Challenging Compliance | ... | |
| PHIPA Cross-Program Consent | ... | |

### Findings by Severity

For each finding:
**[SEVERITY-NUMBER] Title**
- Principle: Which PIPEDA/PHIPA principle is affected
- Location: file.py:line_number or process description
- Gap: What is missing or inadequate
- Risk: What could happen (regulatory, reputational, to clients)
- Recommendation: How to address it
- Agency action needed: What the deploying agency must do (vs. code changes)

### Agency Deployment Checklist
Items that are the agency's responsibility (not code issues):
- Designate a privacy officer
- Configure retention periods
- Customise privacy policy template
- Set up breach notification procedure
- Train staff on privacy obligations
- Configure AI feature toggles based on agency's privacy assessment
- Complete a Data Processing Impact Assessment (DPIA) if enabling AI features
  (required under PIPEDA amendments for automated processing of personal information)
- Review PHIPA consent settings for cross-program note sharing
- Configure suppression thresholds for funder reports

### Recommendations
Improvements for future development
```

---

### Prompt C: Accessibility (WCAG 2.2 AA / AODA)

```markdown
## Role

You are a WCAG 2.2 AA accessibility specialist with expertise in testing
web applications used by people with diverse abilities. You understand AODA
(Accessibility for Ontarians with Disabilities Act) requirements for software
used by Ontario organisations. You have experience testing multi-surface
applications (staff UI, participant portal, public forms).

## Application Context

KoNote is used by nonprofit caseworkers and their participants in Ontario,
Canada. The user base includes:

**Staff users:**
- Staff with visual impairments (screen readers, magnification)
- Staff with motor impairments (keyboard-only navigation)
- Staff with cognitive disabilities (need clear, simple interfaces)
- Staff with low digital literacy (need obvious affordances)
- Staff working in noisy environments (cannot rely on audio cues)

**Participant portal users:**
- Participants with varying digital literacy (may be first-time web users)
- Participants using mobile devices (small screens, touch targets)
- Participants with disabilities (the population KoNote serves often
  includes people with disabilities)
- Participants using assistive technology

**Public survey respondents:**
- Anyone — surveys may be embedded in external sites or shared via link
- Must be accessible without any account or login
- May be accessed on any device

**Tech stack relevant to accessibility:**
- Server-rendered Django templates (not a JavaScript SPA)
- Pico CSS framework (provides baseline accessibility)
- HTMX for partial page updates (dynamic content concerns)
- Chart.js for data visualisation (canvas-based, accessibility concerns)
- Bilingual interface (EN/FR) — language switching must be accessible
- No custom JavaScript framework

**Known accessibility features already implemented:**
- Skip navigation links
- Semantic HTML (header, nav, main, footer)
- Visible focus indicators
- Screen reader announcements for form errors
- aria-live regions for HTMX updates
- Colour contrast meets AA standards (light mode)
- Automated accessibility tests (test_a11y_ci.py)

## Scope

**Templates to review (all in templates/ directory):**
- base.html (layout, skip links, landmarks)
- components/ (reusable components: nav, forms, modals)
- clients/ (client list, detail, edit forms, service episodes, DV indicators)
- notes/ (note creation form — most complex form, AI suggestions)
- plans/ (plan detail with accordions, goal builder AI chat)
- reports/ (charts, data tables, insights dashboard, funder reports)
- auth/ (staff login, registration)
- admin/ (admin settings pages, plausibility tuning, SRE categories)
- portal/ (participant portal: plans, journal, messages, resources, surveys)
- surveys/ (survey creation, public survey form, thank-you page,
  already-responded page, multi-page navigation)
- circles/ (circle list, detail, member management)
- events/ (calendar, event form, SRE report, timeline)
- communications/ (message templates, reminder previews)
- ai/ (AI suggestion panels, goal builder chat)
- 403.html, 404.html, 500.html (error pages)

**JavaScript to review:**
- static/js/app.js (HTMX configuration, dynamic behaviour, plausibility
  checks, copy-to-clipboard)
- static/js/portal.js (participant portal interactions)
- static/js/followup-picker.js (date picker widget)
- static/js/meeting-picker.js (meeting selection widget)

**CSS to review:**
- static/css/theme.css (custom styles, colour overrides)

**Out of scope:** Backend Python code (unless it generates HTML directly
in views without templates)

## Checklist

### WCAG 2.2 AA — Perceivable

**1.1 Text Alternatives**
- [ ] All images have meaningful alt text (or alt="" for decorative)
- [ ] Chart.js canvases have aria-label or fallback text description
- [ ] Icons used without text have accessible labels
- [ ] Form controls have associated labels (not just placeholders)
- [ ] Copy-to-clipboard buttons have accessible labels

**1.2 Time-Based Media**
- [ ] N/A (no video or audio content)

**1.3 Adaptable**
- [ ] Heading hierarchy is correct (h1 > h2 > h3, no skips)
- [ ] Tables have proper th elements and scope attributes
- [ ] Forms use fieldset/legend for related groups
- [ ] Reading order matches visual order
- [ ] Content is understandable without CSS
- [ ] Multi-page survey navigation conveys current position (step X of Y)

**1.4 Distinguishable**
- [ ] Text colour contrast >= 4.5:1 (normal text)
- [ ] Text colour contrast >= 3:1 (large text, 18pt+)
- [ ] Non-text contrast >= 3:1 (borders, icons, focus indicators)
- [ ] Text can be resized to 200% without loss of content
- [ ] No text in images
- [ ] DV-safe visual indicators maintain contrast

### WCAG 2.2 AA — Operable

**2.1 Keyboard Accessible**
- [ ] All interactive elements reachable by Tab key
- [ ] Tab order follows logical reading order
- [ ] No keyboard traps (can always Tab away)
- [ ] Focus visible on all interactive elements
- [ ] Custom widgets (accordions, dropdowns) keyboard-operable
- [ ] HTMX-loaded content is keyboard-accessible
- [ ] AI goal builder chat is keyboard-operable
- [ ] Multi-page survey navigation keyboard-accessible
- [ ] Portal journal entry creation keyboard-accessible
- [ ] Date picker widgets keyboard-accessible

**2.2 Enough Time**
- [ ] Session timeout warning before auto-logout (staff)
- [ ] User can extend session
- [ ] No content that auto-advances without user control
- [ ] Portal session timeout warning before auto-logout
- [ ] Public survey does not time out during completion

**2.3 Seizures**
- [ ] No content flashes more than 3 times per second

**2.4 Navigable**
- [ ] Skip navigation link works and is first focusable element
- [ ] Page titles are descriptive and unique
- [ ] Link text is meaningful (no "click here" without context)
- [ ] Multiple ways to find pages (nav, search, breadcrumbs)
- [ ] Focus indicator is visible and high-contrast
- [ ] Portal navigation is separate and clear
- [ ] Public survey shows progress (which page/section)

**2.5 Input Modalities**
- [ ] Touch targets are at least 24x24 CSS pixels (WCAG 2.2)
- [ ] No functionality requires specific gestures (pinch, swipe)
- [ ] Drag-and-drop has keyboard alternative

### WCAG 2.2 AA — Understandable

**3.1 Readable**
- [ ] Page language declared (lang="en" or lang="fr" on html element)
- [ ] Language changes within page are marked (lang="fr" on French text)
- [ ] Bilingual survey content correctly marks language on each element
- [ ] Language switcher is accessible and clearly labelled

**3.2 Predictable**
- [ ] Focus changes don't cause unexpected navigation
- [ ] Form submission doesn't auto-redirect without warning
- [ ] HTMX content updates don't move focus unexpectedly
- [ ] AI suggestion insertion doesn't move focus unexpectedly
- [ ] Survey conditional section show/hide doesn't disorient users

**3.3 Input Assistance**
- [ ] Form errors are announced to screen readers (aria-live)
- [ ] Error messages identify which field has the error
- [ ] Required fields are indicated (not just by colour)
- [ ] Error suggestions help the user fix the problem
- [ ] Confirmation before destructive actions (delete, erasure)
- [ ] Plausibility warnings on metric entry are accessible
- [ ] Survey validation errors are announced on public form
- [ ] Portal form errors are announced

### WCAG 2.2 AA — Robust

**4.1 Compatible**
- [ ] HTML validates (no duplicate IDs, proper nesting)
- [ ] ARIA roles and states used correctly
- [ ] HTMX dynamic content triggers screen reader announcements
- [ ] Name, role, value exposed for all custom controls

### HTMX-Specific Accessibility

- [ ] HTMX swap targets have aria-live="polite" or aria-live="assertive"
- [ ] Loading indicators are announced to screen readers
- [ ] Swapped content does not steal focus unless appropriate
- [ ] Error responses from HTMX are announced (htmx:responseError handler)
- [ ] HTMX-loaded forms are properly labelled
- [ ] AI suggestion loading states are announced

### Chart.js Accessibility

- [ ] Each chart has a text description or data table alternative
- [ ] Colour is not the only way to distinguish data series
- [ ] Chart data is available in a non-visual format
- [ ] Insights dashboard charts have accessible alternatives

### Public Survey Accessibility

- [ ] Survey form is accessible without authentication
- [ ] Multi-page navigation announces page transitions
- [ ] Conditional sections announce visibility changes
- [ ] Score display on thank-you page is accessible
- [ ] Embedded survey (iframe) maintains accessibility
- [ ] ResizeObserver doesn't break assistive technology

### Portal Accessibility

- [ ] Portal login form is accessible
- [ ] Emergency exit button is prominent and keyboard-accessible
- [ ] Journal entry creation is accessible
- [ ] Message inbox is navigable with screen reader
- [ ] Resource links have descriptive text

## Output Format

### Summary

| Category | Issues Found | Critical | High | Medium | Low |
|----------|-------------|----------|------|--------|-----|
| Perceivable | | | | | |
| Operable | | | | | |
| Understandable | | | | | |
| Robust | | | | | |
| Portal-Specific | | | | | |
| Survey-Specific | | | | | |
| **Total** | | | | | |

WCAG 2.2 AA Compliant: Yes / No / With Fixes

### Findings

For each finding:
**[SEVERITY-NUMBER] Title**
- WCAG Criterion: X.X.X Level AA
- Location: template_file.html:line or description
- Issue: What fails the criterion
- Impact: Who is affected (screen reader users, keyboard users, etc.)
- Fix: Specific HTML/CSS/JS change needed
- Test: How to verify (tool or manual test)

### Testing Notes
Tools used or recommended:
- axe DevTools (browser extension)
- WAVE (web accessibility evaluator)
- NVDA or JAWS screen reader testing
- Keyboard-only navigation testing
- Colour contrast checker
- Mobile device testing (portal and public surveys)

### Recommendations
Improvements beyond AA compliance
```

---

### Prompt D: Deployment Reliability

```markdown
## Role

You are a DevOps engineer specialising in Docker deployments for small
organisations. You understand that the teams deploying this software may
not have dedicated ops staff — the deployment must be resilient and
self-healing.

## Application Context

KoNote is deployed via Docker Compose to various hosting providers
(Azure Container Apps, Railway, OVHcloud Beauharnois, self-hosted).
Each deployment is a single agency instance. OVHcloud deployments use
a 4-layer self-healing automation stack.

**Deployment architecture:**
- Python 3.12-slim Docker image
- PostgreSQL 16 (two databases: app + audit)
- Gunicorn WSGI server (2 workers)
- WhiteNoise for static files
- Caddy as reverse proxy (OVHcloud) or platform-provided (Railway, Azure)
- Ollama inference endpoint on separate VPS (optional, for AI features)
- No Redis, no Celery, no async workers

**Startup sequence (entrypoint.sh):**
1. Run Django migrations (app database) — with 5-phase ghost migration healer
2. Run audit migrations (audit database)
3. Run tenant migrations (if multi-tenancy enabled)
4. Seed data (metrics, features, settings, templates, event types,
   SRE categories, note templates)
5. Security check (blocks startup in production if critical issues found)
6. Translation check (non-blocking warning)
7. Start gunicorn

**Multi-phase migration healing (startup):**
- Phase 1: Detect ghost migration records (applied but file missing)
- Phase 2: Remove orphan records with cross-app dependency propagation
- Phase 3: Run swappable-dep consistency checks
- Phase 4: Catch cross-app dependency errors Phase 2 misses
- Phase 5: Handle duplicate column/table errors with auto-fake

**Known deployment learnings:**
- Docker locale must be UTF-8 for French translations
- .po file compilation is fragile; .mo files are pre-compiled and committed
- SafeLocaleMiddleware falls back to English if translations fail
- Seed commands must never silently fail (use get_or_create, not guards)
- Entrypoint must be in railway.json watchPatterns
- setup_public_tenant prefers custom domain over azurecontainerapps.io
  in ALLOWED_HOSTS
- Backups use pg_dump custom format with retry logic

## Scope

**Files to review:**
- Dockerfile (and Dockerfile.alpine if present)
- docker-compose.yml
- docker-compose.demo.yml
- entrypoint.sh
- requirements.txt
- railway.json
- konote/settings/base.py (database config, security settings)
- konote/settings/production.py
- konote/settings/build.py
- konote/db_router.py
- seeds/ (all seed commands)
- apps/audit/management/commands/startup_check.py
- apps/audit/management/commands/lockdown_audit_db.py
- apps/tenants/management/commands/provision_tenant.py
- apps/tenants/management/commands/rotate_tenant_key.py
- apps/tenants/management/commands/setup_public_tenant.py
- apps/tenants/management/commands/migrate_default.py
- apps/auth_app/management/commands/rotate_encryption_key.py
- apps/admin_settings/management/commands/check_translations.py
- scripts/ (any deployment scripts)

## Checklist

### Container Security
- [ ] Non-root user configured (USER directive in Dockerfile)
- [ ] No secrets baked into image (check ENV, COPY, ARG directives)
- [ ] Base image is current and receives security updates
- [ ] Unnecessary packages not installed
- [ ] .dockerignore excludes sensitive files (.env, .git, venv)
- [ ] COPY . . does not include development/test files unnecessarily

### Startup Reliability
- [ ] Migrations run before app starts (order in entrypoint.sh)
- [ ] Migration failure blocks startup (set -e in entrypoint)
- [ ] Audit database migration runs separately
- [ ] Tenant migration runs after app migration
- [ ] Ghost migration healer runs before normal migrations
- [ ] Ghost healer phases are ordered correctly (1→2→3→4→5)
- [ ] Phase 5 auto-fake handles duplicate column/table errors gracefully
- [ ] Seed failure does not block startup (but warns loudly)
- [ ] Security check blocks startup in production mode
- [ ] Security check warns-only in demo mode
- [ ] Translation check is non-blocking
- [ ] Startup does not depend on external services being available
  (Ollama, OpenRouter, Azure AD)

### Database Safety
- [ ] DATABASE_URL required (not optional with fallback)
- [ ] AUDIT_DATABASE_URL required (not optional with fallback)
- [ ] Connection timeouts configured
- [ ] Database router correctly routes audit models
- [ ] Database router correctly routes tenant models
- [ ] TenantSyncRouter does not block TENANT_APPS migrations in
      migrate_default command
- [ ] No migration creates irreversible data changes without backup warning
- [ ] Backup command uses pg_dump custom format with retry logic

### Configuration Hygiene
- [ ] All required env vars use require_env() (fail loudly if missing)
- [ ] Optional env vars have safe defaults
- [ ] No default SECRET_KEY or FIELD_ENCRYPTION_KEY in code
- [ ] DEBUG defaults to False (not True)
- [ ] ALLOWED_HOSTS is not ['*'] in production
- [ ] AI_API_KEY is optional (AI features degrade gracefully without it)
- [ ] OLLAMA_BASE_URL is optional (self-hosted LLM is not required)

### Static Files
- [ ] collectstatic runs at build time (not startup)
- [ ] WhiteNoise configured for compressed static files
- [ ] Build settings (konote.settings.build) work without database

### Recovery
- [ ] Application recovers from temporary database outage
- [ ] Application recovers from temporary audit database outage
- [ ] Seed commands are idempotent (safe to run multiple times)
- [ ] No startup race conditions between migrations and seeds
- [ ] Key rotation commands are safe (no data loss during rotation)
- [ ] Tenant provisioning is idempotent

### Hosting Provider Compatibility
- [ ] railway.json watchPatterns include all deployment-relevant files
- [ ] PORT environment variable respected (not hardcoded)
- [ ] Health check endpoint available (health_check middleware)
- [ ] Logs go to stdout/stderr (no log files inside container)
- [ ] OVHcloud deploy script handles credential storage correctly
- [ ] Azure Container Apps ALLOWED_HOSTS prefers custom domain

## Output Format

### Summary

| Category | Pass | Fail | Warning |
|----------|------|------|---------|
| Container Security | | | |
| Startup Reliability | | | |
| Database Safety | | | |
| Configuration Hygiene | | | |
| Static Files | | | |
| Recovery | | | |
| Hosting Compatibility | | | |

Deployment Reliable: Yes / No / With Fixes

### Findings

For each finding:
**[SEVERITY-NUMBER] Title**
- Location: file:line
- Issue: What is wrong
- Impact: What fails (startup crash? data loss? silent failure?)
- Fix: Specific change needed
- Test: How to verify

### Deployment Runbook Gaps
Items that should be documented but are not:
- Backup procedure before migration
- Rollback procedure if migration fails
- Key rotation steps (app-level and per-tenant)
- Database restore procedure
- Ghost migration healer troubleshooting
- Tenant provisioning procedure
- Ollama endpoint setup and monitoring

### Recommendations
Improvements for deployment resilience
```

---

### Prompt E: AI Governance (LLM Integration Safety)

This prompt was added in v2.0 to cover the AI/LLM integration introduced in 2026.

```markdown
## Role

You are an AI safety and governance specialist with expertise in LLM
integration patterns, PII protection, and responsible AI deployment in
healthcare-adjacent applications. You understand Canadian privacy law
(PIPEDA, PHIPA) as it applies to sending data to third-party AI services.

## Application Context

KoNote integrates AI features via external LLM APIs (OpenRouter, routing
to Claude Sonnet 4 by default) and optionally via a self-hosted Ollama
endpoint (Qwen3.5-35B-A3B on OVHcloud VPS-4 in Beauharnois, QC).

**AI features (gated by two-tier feature toggles):**

Tier 1 — `ai_assist_tools_only` (default: enabled):
- Metric suggestions from target descriptions (no participant data)
- Outcome statement improvement (template text, no names)
- Goal builder AI chat (multi-turn, metric definitions only)

Tier 2 — `ai_assist_participant_data` (default: disabled):
- Progress note structure suggestions (de-identified content)
- Outcome insights from qualitative data (anonymised quotes with
  ephemeral source mapping — never persisted, never sent to AI)
- Narrative generation from aggregate statistics

**PII protection architecture:**
- pii_scrub.py removes names, dates, record IDs before sending to LLM
- No client names, no identifying information in any AI prompt
- Quote anonymisation uses ephemeral in-memory mapping (never persisted)
- Rate limiting on all AI endpoints (20 req/hr for tools, 10 req/hr
  for insights)
- Feature toggles fail-closed (if toggle missing, AI is disabled)

**Self-hosted LLM path (future/optional):**
- Ollama on VPS-4 (48 GB RAM, Beauharnois QC — Canadian data residency)
- Used for PII stripping stage before frontier LLM analysis
- Two-stage survey pipeline: self-hosted strips PII → frontier analyses
- No participant data ever leaves Canada in self-hosted path

## Scope

**Files to review:**
- konote/ai.py (OpenRouter integration, API client, error handling)
- konote/ai_views.py (all AI endpoints, rate limiting, input validation)
- konote/ai_urls.py (route definitions)
- konote/forms.py (AI-related form validation)
- apps/reports/pii_scrub.py (PII removal/anonymisation)
- apps/reports/insights.py (qualitative data collection for AI)
- apps/reports/insights_views.py (insights dashboard)
- apps/reports/metric_insights.py (distribution analysis)
- apps/admin_settings/models.py (FeatureToggle definitions)
- apps/admin_settings/forms.py (toggle management UI)
- konote/settings/base.py (AI configuration, API keys)
- templates/ai/ (AI suggestion panels, goal builder chat)
- static/js/app.js (client-side AI interaction)

**Out of scope:** Ollama server configuration (infrastructure, not code),
OpenRouter account setup, model selection rationale

## Checklist

### PII Protection
- [ ] pii_scrub.py removes all name patterns (first, last, preferred)
- [ ] pii_scrub.py removes dates of birth
- [ ] pii_scrub.py removes record IDs and internal references
- [ ] pii_scrub.py removes email addresses and phone numbers
- [ ] No PII appears in AI prompts (search all prompt templates)
- [ ] No PII appears in AI API request logs
- [ ] Ephemeral quote mapping is never persisted to database
- [ ] Ephemeral quote mapping is never included in API requests
- [ ] Error responses from AI do not echo back submitted content
- [ ] AI responses are not cached with PII keys

### Feature Toggle Safety
- [ ] ai_assist_tools_only defaults to enabled (safe — no participant data)
- [ ] ai_assist_participant_data defaults to disabled
- [ ] Toggles fail-closed (missing toggle = feature disabled)
- [ ] Toggle state is checked in every AI view (not just URL routing)
- [ ] Toggle changes are logged in audit trail
- [ ] UI clearly communicates what each toggle enables

### Rate Limiting
- [ ] All AI endpoints enforce rate limits
- [ ] Rate limits are per-user (not per-IP, to prevent bypass)
- [ ] Rate limit responses return proper HTTP 429
- [ ] Rate limit headers are set (Retry-After, X-RateLimit-*)
- [ ] Goal builder multi-turn chat cannot be used to exhaust API quota

### Input Validation
- [ ] AI forms use Django ModelForm (not raw request.POST)
- [ ] User input is sanitised before inclusion in prompts
- [ ] Prompt injection is mitigated (user text is clearly delimited)
- [ ] Maximum input length is enforced
- [ ] AI endpoint responses are validated before rendering

### Data Flow Integrity
- [ ] Tier 1 features never include participant data in prompts
- [ ] Tier 2 features only include de-identified data
- [ ] Aggregate statistics cannot be reverse-engineered to individuals
      (check minimum group sizes)
- [ ] Insights quotes are anonymised before analysis
- [ ] AI-generated content is clearly labelled as AI-generated
- [ ] AI suggestions can be edited before saving (human-in-the-loop)

### API Security
- [ ] AI_API_KEY loaded from environment (not hardcoded)
- [ ] API key is not logged or exposed in error messages
- [ ] API calls use HTTPS
- [ ] API timeout is configured (no indefinite waits)
- [ ] API errors are handled gracefully (no stack traces to user)
- [ ] Fallback behaviour when API is unavailable

### Canadian Data Residency (if self-hosted path active)
- [ ] Self-hosted LLM is hosted in Canada (Beauharnois, QC)
- [ ] PII stripping happens on self-hosted before frontier LLM
- [ ] No participant data transits outside Canada
- [ ] Data residency is documented for agencies

## Output Format

### Summary

| Category | Pass | Fail | Warning |
|----------|------|------|---------|
| PII Protection | | | |
| Feature Toggle Safety | | | |
| Rate Limiting | | | |
| Input Validation | | | |
| Data Flow Integrity | | | |
| API Security | | | |
| Data Residency | | | |

AI Governance Adequate: Yes / No / With Fixes

### Findings

For each finding:
**[SEVERITY-NUMBER] Title**
- Location: file.py:line_number
- Issue: What is wrong
- Impact: What data could be exposed, to whom
- Fix: Specific code change needed
- Test: How to verify

### Data Flow Diagram
Describe the data flow for each AI feature:
- What data enters → what processing occurs → what leaves the system

### Recommendations
Improvements for AI safety and governance
```

---

### Prompt F: Bilingual Compliance (EN/FR)

This prompt was added in v2.0. French translation is now live and bilingual
compliance is a legal requirement (see DRR: bilingual-requirements.md).

```markdown
## Role

You are a bilingual compliance specialist familiar with Canada's Official
Languages Act, Ontario's French Language Services Act (FLSA), and WCAG
3.1.2 (Language of Parts). You understand the technical challenges of
maintaining bilingual Django applications.

## Application Context

KoNote serves nonprofits in Ontario, Canada. Many agencies are required
to offer services in both English and French. The application uses Django's
i18n framework with .po/.mo files for translations.

**Bilingual architecture:**
- Django i18n with gettext (.po/.mo files)
- translate_strings management command (extracts + compiles)
- SafeLocaleMiddleware falls back to English if translations fail
- Language preference stored in user profile and cookie
- Bilingual survey content (per-field EN/FR text, not gettext)
- Templates use {% trans %} and {% blocktrans %} tags
- Pre-compiled .mo files committed to repo (compilation is fragile)
- System check W010 warns if template string count exceeds .po entries
- Pre-commit hook warns if .html files change without .po updates
- Container startup runs check_translations (non-blocking)

**Known requirements (from DRR: bilingual-requirements.md):**
- Official Languages Act: federally regulated services
- Ontario FLSA: designated agencies must offer French services
- Funder requirements: many funders require bilingual reporting
- WCAG 3.1.2: language of parts must be programmatically determined

## Scope

**Files to review:**
- locale/fr/LC_MESSAGES/django.po (French translations)
- locale/fr/LC_MESSAGES/django.mo (compiled translations)
- apps/admin_settings/management/commands/translate_strings.py
- apps/admin_settings/management/commands/check_translations.py
- konote/middleware/safe_locale.py
- konote/middleware/terminology.py
- templates/ (all templates using {% trans %} or {% blocktrans %})
- apps/surveys/models.py (bilingual survey fields)
- apps/portal/templatetags/survey_tags.py (bilingual template filter)
- apps/surveys/public_views.py (public form language handling)
- apps/portal/views.py (portal language handling)
- static/js/app.js (any client-side language strings)

**Out of scope:** Translation quality (whether the French is good French),
content strategy, translation of user-generated content

## Checklist

### Translation Coverage
- [ ] Count empty msgstr entries in django.po — what percentage is
      translated? (Target: 100% of UI-facing strings)
- [ ] Are all template {% trans %} strings present in django.po?
- [ ] Are all {% blocktrans %} strings present in django.po?
- [ ] Are JavaScript strings (if any) translated?
- [ ] Are email templates translated?
- [ ] Are error messages translated?
- [ ] Are form labels and help text translated?
- [ ] Are admin-only strings translated? (lower priority but needed)
- [ ] Are portal-specific strings translated?
- [ ] Are public survey UI strings translated?

### Translation Infrastructure
- [ ] translate_strings command extracts all strings correctly
- [ ] translate_strings command compiles .mo files correctly
- [ ] .mo files are committed to repo (not generated at runtime)
- [ ] SafeLocaleMiddleware falls back gracefully to English
- [ ] System check W010 correctly counts template vs .po entries
- [ ] Pre-commit hook fires when .html files change
- [ ] Container startup check_translations runs without blocking

### Language Switching
- [ ] Language switcher is visible and accessible
- [ ] Language preference persists across sessions (cookie + profile)
- [ ] Language switch does not lose form data or navigation context
- [ ] All pages render correctly in French (no layout breaks)

### Bilingual Survey Content
- [ ] Survey model has separate EN/FR fields for titles and descriptions
- [ ] Bilingual template filter correctly selects language
- [ ] Public survey form displays in user's preferred language
- [ ] Survey scoring labels are bilingual
- [ ] Thank-you page content is bilingual

### Bilingual Data Export
- [ ] Funder report column headers use the user's language
- [ ] CSV export column headers are bilingual or match user's language
- [ ] Error messages in export files are translated
- [ ] PDF export templates render correctly in French

### WCAG 3.1.2 Compliance
- [ ] html element has correct lang attribute (en or fr)
- [ ] Language attribute updates when user switches language
- [ ] Mixed-language content marks language changes (lang="fr" on
      French text within English page, and vice versa)
- [ ] Bilingual survey questions mark each language portion

## Output Format

### Summary

| Category | Complete | Partial | Missing |
|----------|----------|---------|---------|
| Translation Coverage | | | |
| Translation Infrastructure | | | |
| Language Switching | | | |
| Bilingual Survey Content | | | |
| WCAG 3.1.2 Compliance | | | |

Translation Coverage: XX% (translated / total strings)
Bilingual Compliant: Yes / No / With Fixes

### Findings

For each finding:
**[SEVERITY-NUMBER] Title**
- Location: file:line or string identifier
- Issue: What is missing or incorrect
- Impact: Who is affected (French-speaking users, compliance risk)
- Fix: Specific change needed
- Test: How to verify

### Missing Translation Inventory
List of untranslated strings by category:
- UI labels: count
- Error messages: count
- Email templates: count
- Admin strings: count
- Portal strings: count
- Survey strings: count

### Recommendations
Improvements for bilingual compliance
```

---

## Part 4.5: Cross-Prompt Deduplication

Some concerns span multiple prompts. To prevent duplicate findings, one prompt "owns" each concern and other prompts should reference it rather than writing a separate finding.

| Concern | Primary Owner | Also Checked In | Rule |
|---------|--------------|-----------------|------|
| PII in AI prompts | Prompt E (AI Governance) | A (Encryption #9), B (Principle 7) | E owns the finding; A and B reference it |
| Portal authentication | Prompt A (RBAC #7-#8) | B (Principle 7, safeguards) | A owns auth; B checks privacy implications only |
| Export demo/real boundaries | Prompt B (Privacy, Principle 5) | A (G11) | B owns the finding; A's gate check references B |
| Bilingual error messages | Prompt F (Bilingual) | C (Accessibility, 3.3) | F owns translation; C checks screen reader announcement |
| DV-safe access control | Prompt A (RBAC #10) | B (Principle 7, safeguards) | A owns access control; B checks data minimisation |
| Suppression thresholds | Prompt B (Privacy, Principle 5) | A (RBAC #14) | B owns re-identification risk; A checks enforcement |
| Rate limiting on public endpoints | Prompt A (G9) | E (Rate Limiting) | A owns survey rate limits; E owns AI rate limits |

When running multiple prompts in the same session, the reviewer should check this table and skip items already covered by a completed prompt. When running prompts independently, duplicate findings across prompts are acceptable — they will be deduplicated when creating tasks.

---

## Part 5: Running a Review — Practical Guide

### For AI Code Review Tools

1. **Open a new conversation** with the AI tool (fresh context, no prior assumptions)
2. **Paste the full prompt** from Part 4
3. **Attach or provide access to the codebase** (GitHub URL, zip file, or file-by-file)
4. **Let the tool work through the checklist** — do not interrupt or guide it
5. **Save the output** to `../konote-qa-scenarios/reviews/YYYY-MM-DD/dimension.md` (private repo)
6. **Create tasks in TODO.md** for any Critical or High findings

### For Human Reviewers

1. **Read the prompt** to understand what you are looking for
2. **Use the file list** as your reading order
3. **Work through the checklist** item by item, noting evidence
4. **Fill in the output format** — this is your report
5. **Flag anything not on the checklist** that concerns you in a "Notes" section

### Comparing Results Over Time

Store all review results in the **private** `konote-qa-scenarios` repo under `reviews/`, organized by date:

```
konote-qa-scenarios/reviews/
  2026-02-06/
    security.md
    privacy.md
  2026-03-04/
    deep-review.md
    security.md
    accessibility.md
```

Each review references the previous one and tracks:
- New findings since last review
- Findings fixed since last review
- Score trend (for scored dimensions)

---

## Part 6: When to Use Which Prompt

| Situation | Use This |
|-----------|----------|
| PR that changes auth or RBAC code | Prompt A (Security) — scoped to changed files |
| PR that changes client models or forms | Prompt A + Prompt B (Security + Privacy) |
| PR that changes templates or CSS | Prompt C (Accessibility) |
| PR that changes Dockerfile or entrypoint | Prompt D (Deployment) |
| PR that changes AI code or prompts | Prompt E (AI Governance) |
| PR that changes portal authentication | Prompt A (Security) — focus on portal scenarios |
| PR that changes public survey views | Prompt A + Prompt E (Security + AI if survey data used by AI) |
| PR that changes circles/family models | Prompt A + Prompt B (Security + Privacy — relationship data is PII) |
| PR that adds/changes templates with {% trans %} | Prompt F (Bilingual) |
| PR that changes multi-tenancy code | Prompt A + Prompt D (Security + Deployment) |
| PR that changes export commands | Prompt B (Privacy) — verify demo/real data boundaries |
| Quarterly review | All six prompts, one at a time |
| New agency evaluating KoNote | Prompt A (Security) — they care most about data safety |
| Before a major release | All six prompts + full test suite |
| After adding a new dependency | `pip-audit` + brief Prompt A with focus on A06 |
| UX concern raised by users | Use existing `tasks/UX-REVIEW.md` framework |

---

## Part 7: Relationship to Existing Review Infrastructure

This framework builds on what already exists in the KoNote codebase:

| Existing Asset | How This Framework Uses It |
|---------------|---------------------------|
| `tasks/security-review-plan.md` | Prompt A incorporates its gate checks and scoring |
| `tasks/security-review-prompt.md` | Prompt A is a refined, expanded version |
| `tasks/independent-security-review.md` | Agency-facing prompt remains separate (simpler) |
| `SECURITY.md` | Referenced by all prompts for architecture context |
| `python manage.py security_audit` | Part of Tier 1 continuous checks |
| `python manage.py check --deploy` | Part of Tier 1 continuous checks |
| `python manage.py check_translations` | Part of Tier 1 continuous checks (added v2.0) |
| `tasks/UX-REVIEW.md` | Covers UX dimension; this framework does not replace it |
| Test suite (`tests/test_security.py`, etc.) | Regression tests from review findings go here |
| `tests/test_a11y_ci.py` | Automated accessibility checks complement Prompt C |
| `tasks/design-rationale/ai-feature-toggles.md` | Prompt E references this for toggle design |
| `tasks/design-rationale/bilingual-requirements.md` | Prompt F references this for legal requirements |
| `tasks/design-rationale/phipa-consent-enforcement.md` | Prompt B references this for consent logic |
| `tasks/design-rationale/data-access-residency-policy.md` | Prompt E references this for data residency |
| `tasks/design-rationale/no-live-api-individual-data.md` | Prompt B references this for export architecture |

---

## Appendix A: Prompt Template (Blank)

Use this to create new dimension-specific prompts as needed.

```markdown
## Role

You are a [specialist type] with expertise in [specific domain].
[Additional context about perspective and priorities.]

## Application Context

KoNote is a Django 5 web application that [brief description relevant
to this dimension]. It handles [relevant data types] for [relevant users].

[Key architectural facts relevant to this dimension]

## Scope

**Files to review:**
- [List of 5-15 files most relevant to this dimension]

**Out of scope:**
- [What to skip]

## Checklist

### Category 1: [Name]
- [ ] Check item 1
- [ ] Check item 2
- [ ] ...

### Category 2: [Name]
- [ ] Check item 1
- [ ] ...

## Output Format

### Summary
[Table or scorecard format]

### Findings
For each finding:
**[SEVERITY-NUMBER] Title**
- Location: file:line
- Issue: What is wrong
- Impact: What could happen
- Fix: How to address it
- Test: How to verify

### Recommendations
[Forward-looking improvements]
```

---

## Appendix B: Change Log

### v2.0 (2026-03-04)

**New dimensions added:**
- AI Governance (dimension 5, Critical) — covers LLM integration safety
- Bilingual Compliance (dimension 9, High) — French translations now live

**Dimensions updated:**
- Internationalisation moved from "excluded" to Bilingual Compliance dimension
- Data Privacy renamed to Data Privacy (PIPEDA/PHIPA) — PHIPA consent added
- Access Control expanded to cover portal auth and public survey access

**Prompt A (Security) — major updates:**
- Added three authentication surfaces (staff, portal, public survey)
- Added threat model entries: AI data leakage, cross-surface auth confusion
- Added 20+ new files to scope (portal, surveys, circles, AI, tenants, etc.)
- Added gate checks G8-G11 (portal auth, survey rate limits, AI PII, export boundaries)
- Added 7 new RBAC attack scenarios (portal crossover, DV-safe, circle visibility, PHIPA consent, management command data leak)
- Added encryption checks for MFA secrets, portal emails, circle names

**Prompt B (Privacy) — major updates:**
- Added new PII categories: circles, surveys, portal, journals, communications, DV-safe
- Added PHIPA cross-program consent section
- Added AI data processing consent checks
- Added DataAccessRequest workflow checks
- Added DV-safe field protection checks
- Added suppression threshold checks for funder reports
- Added portal and survey-specific consent and collection checks
- Added export_agency_data demo/real boundary check

**Prompt C (Accessibility) — major updates:**
- Added participant portal users and public survey respondents to user base
- Added portal, survey, circles, events, communications, AI template directories
- Added portal.js, followup-picker.js, meeting-picker.js to JS scope
- Added public survey accessibility section (multi-page nav, conditional sections)
- Added portal accessibility section (emergency exit, journal, inbox)
- Added AI-specific checks (goal builder keyboard, suggestion loading states)
- Added bilingual language switching accessibility

**Prompt D (Deployment) — major updates:**
- Added OVHcloud and Azure Container Apps to hosting providers
- Added Ollama inference endpoint to architecture
- Added 5-phase ghost migration healer to startup sequence
- Added tenant migration, translation check to startup sequence
- Added tenant management commands to scope
- Added ghost migration healer checks
- Added tenant provisioning and key rotation recovery checks
- Added AI configuration hygiene (optional keys, graceful degradation)

**New Prompt E: AI Governance** — new prompt covering:
- PII protection (scrubbing, ephemeral mapping, no persistence)
- Feature toggle safety (two-tier, fail-closed)
- Rate limiting (per-user, proper HTTP 429)
- Input validation (prompt injection mitigation)
- Data flow integrity (tier 1 vs tier 2 separation)
- API security (key management, timeout, error handling)
- Canadian data residency (self-hosted path)

**New Prompt F: Bilingual Compliance** — new prompt covering:
- Translation coverage (% of strings translated)
- Translation infrastructure (extract, compile, checks)
- Language switching (persistence, accessibility)
- Bilingual survey content (per-field EN/FR)
- WCAG 3.1.2 compliance (lang attributes)

**Expert panel recommendations applied:**
- Added RBAC scenarios #14 (funder report suppression) and #15 (ODK sync boundaries)
- Added cross-prompt deduplication table (Part 4.5)
- Added DPIA template to Prompt B Agency Deployment Checklist
- Added bilingual data export checks to Prompt F

**Tier 1 continuous checks updated:**
- Added translate_strings --dry-run to continuous checks
- Added public endpoint spot-check
- Added AI rate limit check

**Tier 2 trigger events expanded:**
- Added AI code changes, portal auth changes, survey views, multi-tenancy routing, export commands

**Part 6 (When to Use) updated:**
- Added 7 new situation rows for new features

**Part 7 (Relationships) updated:**
- Added 7 new existing assets (tests, DRRs, commands)

### v1.0 (2026-02-06)
- Initial framework with 10 dimensions, 4 prompts (A-D)
