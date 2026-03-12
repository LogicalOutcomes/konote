# Data Retention Schedule — Template for Canadian Nonprofits

**Last updated:** March 2026 | **Based on:** PIPEDA, PHIPA (Ontario), and common funder requirements

> **Instructions:** This schedule provides recommended retention periods for a Canadian nonprofit using KoNote. Review each category with your privacy officer and adjust based on your province's legislation, funder agreements, and professional standards. Copy this file, fill in the "Your Policy" column, and keep it alongside your completed privacy policy.

---

## Retention Periods

| # | Data Category | Recommended Minimum | Rationale | Your Policy |
|---|---------------|---------------------|-----------|-------------|
| 1 | **Active client records** (profile, contact info, program enrolments) | Duration of service | Needed for ongoing service delivery | __________ |
| 2 | **Closed client records** (full file: notes, plans, metrics, events) | 7 years after file closure | PHIPA s.13(1) requires 10 years for health records; 7 years satisfies most funder agreements and limitation periods. Use 10 years if you are a health information custodian. | __________ |
| 3 | **Progress notes** | Same as closed client records | Part of the client file; inseparable for outcome reporting | __________ |
| 4 | **Outcome metrics and recordings** | Same as closed client records | Required for longitudinal outcome reporting and funder audits | __________ |
| 5 | **Plan targets and goals** | Same as closed client records | Part of the client file | __________ |
| 6 | **Consent records** (consent forms, dates, scope, withdrawal records) | 7 years after last consent action | PIPEDA Principle 4.3 — must demonstrate valid consent; funder audit trail | __________ |
| 7 | **Audit logs** (access logs, data changes, exports) | 3 years | Sufficient for incident investigation and compliance audits; longer if required by funders | __________ |
| 8 | **User accounts** (staff accounts) | Duration of employment + 6 months | Allows post-departure audit review; 6 months covers typical transition period | __________ |
| 9 | **Participant portal accounts** | Same as associated client record | Portal account is linked to client file; retained and deleted together | __________ |
| 10 | **Exported reports** (secure export links) | 30 days after generation | Secure links auto-expire; exports should be downloaded and stored in the agency's document management system | __________ |
| 11 | **Survey responses** (public and portal surveys) | Same as closed client records if linked to a participant; 2 years if anonymous | Anonymous surveys may be retained shorter; linked responses are part of the client file | __________ |
| 12 | **Encrypted backups** | 90 days (rolling) | Standard backup rotation; oldest backup deleted when new one is created | __________ |
| 13 | **Session data** (browser sessions) | 30 minutes of inactivity (auto-expire) | KoNote default; configurable in settings | __________ |
| 14 | **Error logs** (application logs) | 30 days | Sufficient for troubleshooting; no PII in error logs by design | __________ |
| 15 | **AI-generated drafts** (outcome insights, suggestions) | Not retained after staff review | AI output is transient — staff copy what they need into notes/reports. No AI output is stored permanently. | __________ |
| 16 | **Erasure request records** (audit trail of data deletion) | Permanent | PIPEDA requires evidence that erasure requests were processed. The audit log records the request and approval but retains no PII about the erased client. | __________ |

---

## When Retention Expires

When a retention period expires for a client record:

1. **Identify records due for deletion** — Review closed client files with closure dates older than your retention period.
2. **Verify no active legal holds** — Confirm no ongoing litigation, complaints, or investigations that require the records.
3. **Process deletion in KoNote** — Use the formal data erasure workflow (Admin > Client > Request Erasure). This requires multi-manager approval and produces an audit trail.
4. **Delete associated external files** — Remove any SharePoint folders or Google Drive folders linked to the client. KoNote does not delete external files automatically.
5. **Rotate encrypted backups** — Ensure backups older than your backup retention period are deleted. Old backups may contain data you have erased from the live system.
6. **Document the deletion** — The audit log records it automatically. Note the batch deletion in your annual privacy review.

---

## Provincial Considerations

| Province | Key Legislation | Notable Requirements |
|----------|----------------|---------------------|
| **Ontario** | PHIPA | 10-year minimum for health information custodians |
| **Alberta** | HIA, PIPA | 10-year minimum for health custodians; PIPA for non-health |
| **British Columbia** | PIPA, E-Health Act | Reasonable retention; specific rules for e-health records |
| **Quebec** | Law 25, Act respecting health services | 5-year minimum for health records; new data privacy obligations under Law 25 |
| **All provinces** | PIPEDA | Federal baseline; applies unless province has substantially similar legislation |

> **Consult your privacy officer** to determine which provincial legislation applies to your agency and whether you qualify as a health information custodian.

---

## Funder-Specific Retention

Many funders require agencies to retain records for the duration of the funding agreement plus a specified period. Common patterns:

| Funder Type | Typical Requirement | Notes |
|-------------|---------------------|-------|
| **Federal government** (e.g., ESDC programs) | Duration of agreement + 6 years | Covers audit and evaluation periods |
| **Provincial ministries** | Varies; commonly 7 years | Check your specific transfer payment agreement |
| **United Way** | Duration of agreement + 3 years | Verify with your local United Way |
| **Community foundations** | Varies | Typically follows provincial legislation |

> **When in doubt:** Use 7 years after file closure as a safe default for most Canadian nonprofits. Increase to 10 years if you provide health services in Ontario or Alberta.

---

## Annual Review

Review this retention schedule annually as part of your privacy practices review. Check for:

- [ ] Changes in provincial legislation
- [ ] New funder agreements with different retention requirements
- [ ] Records now past their retention period that should be deleted
- [ ] Staff awareness — does your team know the retention periods?

---

*This template is provided as part of KoNote documentation. Each organisation is responsible for setting retention periods that comply with their specific regulatory requirements.*
