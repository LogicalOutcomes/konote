# KoNote — Independent Code Review Framework

**Version:** 1.0
**Created:** 2026-02-06
**Purpose:** Structured prompts for multi-dimensional code review using AI tools or human reviewers

---

## Why This Framework Exists

KoNote handles sensitive client data for nonprofits. A single security review is not enough — the codebase has multiple dimensions of quality that each require focused attention. This framework defines **10 review dimensions**, a **two-tier review model** (continuous + periodic), and **reusable prompts** that work with any AI code review tool.

The goal: any agency deploying KoNote can run these reviews themselves, and the development team can use them as ongoing quality gates.

---

## Part 1: Review Dimensions

### The 10 Dimensions

Each dimension addresses a different aspect of application quality. They are ordered by risk — the first five relate to data safety; the last five relate to operational quality.

| # | Dimension | Why It Matters for KoNote | Risk Level |
|---|-----------|---------------------------|------------|
| 1 | **Security (OWASP)** | Handles PII; target for data breaches | Critical |
| 2 | **Data Privacy (PIPEDA)** | Canadian privacy law; breach notification required within 72 hours | Critical |
| 3 | **Encryption & Key Management** | All PII encrypted at rest; key compromise = full exposure | Critical |
| 4 | **Access Control (RBAC)** | Program-scoped data isolation; role hierarchy enforcement | Critical |
| 5 | **Audit Trail Integrity** | Compliance requirement; must be tamper-resistant | High |
| 6 | **Deployment Reliability** | Docker, entrypoint, migrations — failure = downtime | High |
| 7 | **Accessibility (WCAG 2.2 AA)** | AODA compliance; users include staff with disabilities | High |
| 8 | **Code Quality & Maintainability** | Nonprofit project; must be maintainable by non-specialists | Medium |
| 9 | **User Experience** | Caseworkers are not tech-savvy; friction = abandonment | Medium |
| 10 | **Dependency Health** | Outdated packages = CVEs; supply chain risk | Medium |

### Dimensions NOT Included (and Why)

| Excluded | Reason |
|----------|--------|
| Performance / scalability | Documented ceiling of ~2,000 clients; premature to optimise beyond that |
| Disaster recovery / backup | Infrastructure-level concern, not code review |
| Documentation quality | Already covered by separate documentation review process |
| Internationalisation | Active development (French UI); too early to review |

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
| `pip-audit` | pip-audit | Known CVEs in dependencies |
| `pytest` (full suite) | pytest | RBAC regressions, encryption round-trip, demo data isolation |
| HTMX endpoint spot-check | Manual / AI | New HTMX endpoints respect CSRF and RBAC |

**Tier 1 should cover:**
- All 7 Gate Checks from the security review plan (G1-G7)
- Dependency CVE scanning
- Test suite pass rate
- Any new endpoints have corresponding permission tests

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
| Data Privacy (PIPEDA) | Quarterly | Prompt B (below) |
| Accessibility (WCAG 2.2 AA) | Before each release | Prompt C (below) |
| Deployment Reliability | After infrastructure changes | Prompt D (below) |
| Code Quality | Semi-annually | (Prompt in development) |
| UX Review | Before each release | Use existing `tasks/UX-REVIEW.md` |
| Dependency Health | Quarterly | Automated with `pip-audit` + manual review |

**Trigger events that require an immediate Tier 2 review:**
- Any change to `konote/encryption.py` or encrypted model fields
- Any change to RBAC middleware or authentication views
- Any change to `entrypoint.sh`, `Dockerfile`, or migration logic
- Any new dependency added to `requirements.txt`
- Any new endpoint that accesses client data

---

## Part 4: Sample Prompts

---

### Prompt A: Security Review (OWASP + RBAC + Encryption)

This is the most comprehensive prompt. It combines three critical dimensions into one because they overlap heavily.

```markdown
## Role

You are a senior application security engineer conducting a white-box security
review. You have expertise in Django security, OWASP Top 10, and healthcare
data protection.

## Application Context

KoNote is a Django 5 web application that stores sensitive client information
(names, dates of birth, progress notes, outcome ratings) for nonprofit social
service agencies in Canada. Each agency runs its own instance.

**Threat model:**
- PRIMARY THREAT: Unauthorised access by authenticated users who should not
  see certain clients (program-scoped data isolation failure)
- SECONDARY THREAT: External attacker exploiting web vulnerabilities
  (injection, XSS, CSRF, authentication bypass)
- TERTIARY THREAT: Data exposure through infrastructure compromise
  (database breach mitigated by field-level encryption)
- OUT OF SCOPE: Physical access, social engineering, denial of service

**Key architectural decisions:**
- All PII encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256)
- Encryption key loaded from environment variable, never in code
- RBAC enforced at middleware level (ProgramAccessMiddleware) — users only
  access clients in their assigned programs
- Audit logs stored in a separate database with INSERT-only permissions
- Authentication via Azure AD SSO (primary) or local Argon2 (fallback)
- Server-rendered Django templates + HTMX (no JavaScript framework)
- CSP headers restrict script and style sources

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

**Then review these (high priority):**
- apps/notes/views.py
- apps/notes/models.py
- apps/plans/views.py
- apps/reports/views.py
- apps/reports/csv_utils.py
- apps/clients/erasure_views.py
- apps/programs/models.py
- konote/db_router.py
- konote/urls.py
- static/js/app.js

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

### OWASP Top 10 Checks

For each, note: PASS / FAIL / NOT APPLICABLE, with file:line evidence.

- A01 Broken Access Control: Can User A access Client X in User B's program?
- A02 Cryptographic Failures: Any weak algorithms? Key exposed in logs/errors?
- A03 Injection: Any raw SQL with user input? Any eval/exec? Template |safe
  with user data?
- A04 Insecure Design: Does failure grant access? Is least privilege applied?
- A05 Security Misconfiguration: ALLOWED_HOSTS, CSP, security headers?
- A06 Vulnerable Components: Check requirements.txt versions against known CVEs
- A07 Auth Failures: Rate limiting on login? Generic error messages?
  Session fixation?
- A08 Data Integrity: CSRF on all forms? SRI on CDN scripts?

### RBAC-Specific Attack Scenarios

Test each scenario by tracing the code path:

1. IDOR: Staff user calls GET /clients/999/ where client 999 is in a different
   program — is this blocked? Where?
2. Vertical escalation: Front desk user submits POST to a staff-only endpoint —
   is this blocked? Where?
3. Admin bypass: Admin user (no program roles) tries to access /clients/123/ —
   is this blocked? Where?
4. Executive bypass: Executive-only user tries to access individual client
   data — is this blocked? Where?
5. HTMX abuse: Can an attacker craft an HTMX request that bypasses middleware?
6. Note access via ID: User accesses /notes/456/ for a note belonging to a
   client in another program — is this blocked?

### Encryption Checks

1. List every model field that stores PII — is it encrypted?
2. Search for any PII logged to stdout/stderr (check logger.* calls)
3. Check if form validation errors echo back submitted PII
4. Check if [decryption error] marker could appear in user-facing templates
5. Verify key rotation command works without data loss (review the code path)

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

### Prompt B: Data Privacy (PIPEDA Compliance)

```markdown
## Role

You are a Canadian privacy compliance specialist with expertise in PIPEDA
(Personal Information Protection and Electronic Documents Act) and Ontario's
AODA. You understand how privacy law applies to nonprofit social service
agencies handling client records.

## Application Context

KoNote is used by Canadian nonprofits to manage participant outcomes —
tracking client progress, recording session notes, and generating reports
for funders. It stores the following PII:

- Client names (first, middle, last, preferred)
- Dates of birth
- Progress notes (narrative text about sessions)
- Outcome ratings (numerical scores on validated scales)
- Custom demographic fields (configurable per agency)
- Staff email addresses
- Registration submissions (name, email, phone)

**Regulatory context:**
- PIPEDA applies to commercial activities by nonprofits
- Ontario nonprofits must also comply with AODA (accessibility)
- If the nonprofit provides health services, PHIPA may also apply
- Breach notification is mandatory within 72 hours under PIPEDA
- Organisations must designate a privacy officer

**Architecture relevant to privacy:**
- Field-level encryption (Fernet/AES) on all PII listed above
- Separate audit database (INSERT-only) logging all data access
- Program-scoped RBAC (staff only see clients in their programs)
- Tiered data erasure (anonymise / purge / full erasure)
- Demo/real data separation (demo users never see real clients)
- Consent capture before data collection
- Data retention tracking with expiry dates
- Export controls with audit trail

## Scope

**Files to review:**
- apps/clients/models.py (client data model, encryption, consent fields)
- apps/clients/erasure_views.py (data erasure workflow)
- apps/clients/forms.py (consent capture, data collection)
- apps/notes/models.py (progress note storage, encryption)
- apps/registration/models.py (self-service registration, PII)
- apps/registration/views.py (registration data handling)
- apps/reports/views.py (data export, what PII leaves the system)
- apps/reports/csv_utils.py (export sanitisation)
- apps/audit/models.py (what is logged, retention)
- konote/middleware/audit.py (what triggers logging)
- konote/encryption.py (encryption implementation)
- konote/settings/base.py (session, cookie, security config)
- templates/ (check for PII in page source, error messages)
- docs/privacy-policy-template.md (provided template adequacy)

## Checklist

### PIPEDA Principle 1: Accountability
- [ ] Is there a designated privacy contact? (check docs, settings)
- [ ] Are privacy policies provided to agencies? (check templates)
- [ ] Is there a documented process for handling privacy complaints?

### PIPEDA Principle 2: Identifying Purposes
- [ ] Is the purpose of each PII field documented?
- [ ] Are purposes communicated to data subjects before collection?
- [ ] Is any PII collected without a stated purpose?

### PIPEDA Principle 3: Consent
- [ ] Is consent captured before PII is stored?
- [ ] What type of consent? (express, implied, opt-out)
- [ ] Can consent be withdrawn? What happens to the data?
- [ ] Is consent withdrawal logged in the audit trail?
- [ ] Is there separate consent for each processing purpose?

### PIPEDA Principle 4: Limiting Collection
- [ ] Is all collected PII necessary for the stated purpose?
- [ ] Are there fields that could be removed or made optional?
- [ ] Could any fields be anonymised rather than stored identifiably?

### PIPEDA Principle 5: Limiting Use, Disclosure, and Retention
- [ ] Is PII used only for the purpose it was collected?
- [ ] Are retention periods defined and enforced?
- [ ] Does expired data actually get purged? (check the code path)
- [ ] Are exports limited to authorised users?
- [ ] Do exports contain only necessary PII?

### PIPEDA Principle 6: Accuracy
- [ ] Can data subjects view their own information?
- [ ] Can data subjects request corrections?
- [ ] Are corrections logged?

### PIPEDA Principle 7: Safeguards
- [ ] Is PII encrypted at rest? (list all fields and verify)
- [ ] Is PII encrypted in transit? (HTTPS, TLS config)
- [ ] Are access controls proportional to sensitivity?
- [ ] Is there physical/organisational security guidance for deployers?

### PIPEDA Principle 8: Openness
- [ ] Is the privacy policy accessible to data subjects?
- [ ] Does it describe what PII is collected and why?
- [ ] Does it describe who has access?
- [ ] Does it describe retention periods?

### PIPEDA Principle 9: Individual Access
- [ ] Can clients request a copy of their data? (check export feature)
- [ ] Can clients request erasure? (check erasure workflow)
- [ ] Is the erasure process complete? (no orphaned data)
- [ ] Are erasure actions logged?
- [ ] Is there a response time commitment?

### PIPEDA Principle 10: Challenging Compliance
- [ ] Is there a documented complaint process?
- [ ] Are complaints tracked?

### Breach Readiness
- [ ] Can the system detect suspicious access patterns?
- [ ] Can affected records be identified within 72 hours?
- [ ] Is there an incident response procedure?
- [ ] Are there alerting mechanisms for anomalous activity?

## Output Format

### Compliance Summary

| PIPEDA Principle | Status | Notes |
|-----------------|--------|-------|
| 1. Accountability | Compliant / Partial / Non-Compliant | |
| 2. Identifying Purposes | ... | |
| ... | ... | |
| 10. Challenging Compliance | ... | |

### Findings by Severity

For each finding:
**[SEVERITY-NUMBER] Title**
- Principle: Which PIPEDA principle is affected
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
used by Ontario organisations.

## Application Context

KoNote is used by nonprofit caseworkers in Ontario, Canada. The user base
includes:
- Staff with visual impairments (screen readers, magnification)
- Staff with motor impairments (keyboard-only navigation)
- Staff with cognitive disabilities (need clear, simple interfaces)
- Staff with low digital literacy (need obvious affordances)
- Staff working in noisy environments (cannot rely on audio cues)

**Tech stack relevant to accessibility:**
- Server-rendered Django templates (not a JavaScript SPA)
- Pico CSS framework (provides baseline accessibility)
- HTMX for partial page updates (dynamic content concerns)
- Chart.js for data visualisation (canvas-based, accessibility concerns)
- No custom JavaScript framework

**Known accessibility features already implemented:**
- Skip navigation links
- Semantic HTML (header, nav, main, footer)
- Visible focus indicators
- Screen reader announcements for form errors
- aria-live regions for HTMX updates
- Colour contrast meets AA standards (light mode)

## Scope

**Templates to review (all in templates/ directory):**
- base.html (layout, skip links, landmarks)
- components/ (reusable components: nav, forms, modals)
- clients/ (client list, detail, edit forms)
- notes/ (note creation form — most complex form)
- plans/ (plan detail with accordions)
- reports/ (charts, data tables)
- auth/ (login, registration)
- admin/ (admin settings pages)
- 403.html, 404.html, 500.html (error pages)

**JavaScript to review:**
- static/js/app.js (HTMX configuration, dynamic behaviour)

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

**1.2 Time-Based Media**
- [ ] N/A (no video or audio content)

**1.3 Adaptable**
- [ ] Heading hierarchy is correct (h1 > h2 > h3, no skips)
- [ ] Tables have proper th elements and scope attributes
- [ ] Forms use fieldset/legend for related groups
- [ ] Reading order matches visual order
- [ ] Content is understandable without CSS

**1.4 Distinguishable**
- [ ] Text colour contrast >= 4.5:1 (normal text)
- [ ] Text colour contrast >= 3:1 (large text, 18pt+)
- [ ] Non-text contrast >= 3:1 (borders, icons, focus indicators)
- [ ] Text can be resized to 200% without loss of content
- [ ] No text in images
- [ ] Dark mode maintains contrast ratios

### WCAG 2.2 AA — Operable

**2.1 Keyboard Accessible**
- [ ] All interactive elements reachable by Tab key
- [ ] Tab order follows logical reading order
- [ ] No keyboard traps (can always Tab away)
- [ ] Focus visible on all interactive elements
- [ ] Custom widgets (accordions, dropdowns) keyboard-operable
- [ ] HTMX-loaded content is keyboard-accessible

**2.2 Enough Time**
- [ ] Session timeout warning before auto-logout
- [ ] User can extend session
- [ ] No content that auto-advances without user control

**2.3 Seizures**
- [ ] No content flashes more than 3 times per second

**2.4 Navigable**
- [ ] Skip navigation link works and is first focusable element
- [ ] Page titles are descriptive and unique
- [ ] Link text is meaningful (no "click here" without context)
- [ ] Multiple ways to find pages (nav, search, breadcrumbs)
- [ ] Focus indicator is visible and high-contrast

**2.5 Input Modalities**
- [ ] Touch targets are at least 24x24 CSS pixels (WCAG 2.2)
- [ ] No functionality requires specific gestures (pinch, swipe)
- [ ] Drag-and-drop has keyboard alternative

### WCAG 2.2 AA — Understandable

**3.1 Readable**
- [ ] Page language declared (lang="en" on html element)
- [ ] Language changes within page are marked (lang="fr" on French text)

**3.2 Predictable**
- [ ] Focus changes don't cause unexpected navigation
- [ ] Form submission doesn't auto-redirect without warning
- [ ] HTMX content updates don't move focus unexpectedly

**3.3 Input Assistance**
- [ ] Form errors are announced to screen readers (aria-live)
- [ ] Error messages identify which field has the error
- [ ] Required fields are indicated (not just by colour)
- [ ] Error suggestions help the user fix the problem
- [ ] Confirmation before destructive actions (delete, erasure)

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

### Chart.js Accessibility

- [ ] Each chart has a text description or data table alternative
- [ ] Colour is not the only way to distinguish data series
- [ ] Chart data is available in a non-visual format

## Output Format

### Summary

| Category | Issues Found | Critical | High | Medium | Low |
|----------|-------------|----------|------|--------|-----|
| Perceivable | | | | | |
| Operable | | | | | |
| Understandable | | | | | |
| Robust | | | | | |
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
(Azure, Railway, Elest.io, self-hosted). Each deployment is a single
agency instance.

**Deployment architecture:**
- Python 3.12-slim Docker image
- PostgreSQL 16 (two databases: app + audit)
- Gunicorn WSGI server (2 workers)
- WhiteNoise for static files
- Caddy as reverse proxy (optional)
- No Redis, no Celery, no async workers

**Startup sequence (entrypoint.sh):**
1. Run Django migrations (app database)
2. Run audit migrations (audit database)
3. Seed data (metrics, features, settings, templates)
4. Security check (blocks startup in production if critical issues found)
5. Start gunicorn

**Known deployment learnings (from MEMORY.md):**
- Docker locale must be UTF-8 for French translations
- .po file compilation is fragile; .mo files are pre-compiled and committed
- SafeLocaleMiddleware falls back to English if translations fail
- Seed commands must never silently fail (use get_or_create, not guards)
- Entrypoint must be in railway.json watchPatterns

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
- [ ] Seed failure does not block startup (but warns loudly)
- [ ] Security check blocks startup in production mode
- [ ] Security check warns-only in demo mode
- [ ] Startup does not depend on external services being available

### Database Safety
- [ ] DATABASE_URL required (not optional with fallback)
- [ ] AUDIT_DATABASE_URL required (not optional with fallback)
- [ ] Connection timeouts configured
- [ ] Database router correctly routes audit models
- [ ] No migration creates irreversible data changes without backup warning

### Configuration Hygiene
- [ ] All required env vars use require_env() (fail loudly if missing)
- [ ] Optional env vars have safe defaults
- [ ] No default SECRET_KEY or FIELD_ENCRYPTION_KEY in code
- [ ] DEBUG defaults to False (not True)
- [ ] ALLOWED_HOSTS is not ['*'] in production

### Static Files
- [ ] collectstatic runs at build time (not startup)
- [ ] WhiteNoise configured for compressed static files
- [ ] Build settings (konote.settings.build) work without database

### Recovery
- [ ] Application recovers from temporary database outage
- [ ] Application recovers from temporary audit database outage
- [ ] Seed commands are idempotent (safe to run multiple times)
- [ ] No startup race conditions between migrations and seeds

### Hosting Provider Compatibility
- [ ] railway.json watchPatterns include all deployment-relevant files
- [ ] PORT environment variable respected (not hardcoded)
- [ ] Health check endpoint available (or Gunicorn responds to GET /)
- [ ] Logs go to stdout/stderr (no log files inside container)

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
- Key rotation steps
- Database restore procedure

### Recommendations
Improvements for deployment resilience
```

---

## Part 5: Running a Review — Practical Guide

### For AI Code Review Tools

1. **Open a new conversation** with the AI tool (fresh context, no prior assumptions)
2. **Paste the full prompt** from Part 4
3. **Attach or provide access to the codebase** (GitHub URL, zip file, or file-by-file)
4. **Let the tool work through the checklist** — do not interrupt or guide it
5. **Save the output** to `tasks/reviews/YYYY-MM-DD-dimension.md`
6. **Create tasks in TODO.md** for any Critical or High findings

### For Human Reviewers

1. **Read the prompt** to understand what you are looking for
2. **Use the file list** as your reading order
3. **Work through the checklist** item by item, noting evidence
4. **Fill in the output format** — this is your report
5. **Flag anything not on the checklist** that concerns you in a "Notes" section

### Comparing Results Over Time

Store all review results in `tasks/reviews/` with consistent naming:

```
tasks/reviews/
  2026-02-06-security.md
  2026-02-06-privacy.md
  2026-Q2-accessibility.md
  2026-Q2-deployment.md
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
| Quarterly review | All four prompts, one at a time |
| New agency evaluating KoNote | Prompt A (Security) — they care most about data safety |
| Before a major release | All four prompts + full test suite |
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
| `tasks/UX-REVIEW.md` | Covers UX dimension; this framework does not replace it |
| Test suite (`tests/test_security.py`, etc.) | Regression tests from review findings go here |

---

## Appendix: Prompt Template (Blank)

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
