# Prompt to paste into Jules

Copy everything below the line into the Jules prompt box.

---

## Task: PIPEDA Privacy Compliance Review — Create Report

**DO NOT modify any application code.** Your only task is to create a single file:
`tasks/reviews/2026-02-06-privacy.md`

This file should contain a privacy compliance review report based on the analysis below.

## Role

You are a Canadian privacy compliance specialist with expertise in PIPEDA
(Personal Information Protection and Electronic Documents Act) and Ontario's
AODA. You understand how privacy law applies to nonprofit social service
agencies handling client records.

## Application Context

KoNote2 is used by Canadian nonprofits to manage participant outcomes —
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

Write the report in markdown with the following structure:

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
