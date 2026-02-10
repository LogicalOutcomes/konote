# SRE1 — Serious Reportable Events

## Summary

Add a predefined list of Serious Reportable Events (SREs) to the events system. When a staff member flags an event as an SRE, it triggers notifications and creates an auditable record.

## Why This Matters

Canadian nonprofits — especially those in housing, mental health, addictions, and youth services — are required to track and report critical incidents. Having a built-in SRE system means agencies don't need a separate incident tracking tool, and leadership gets immediate visibility.

## How It Would Work

1. **Predefined SRE list** — a configurable list of event types relevant to Canadian nonprofits, e.g.:
   - Death of a participant (expected or unexpected)
   - Serious injury requiring emergency medical care
   - Allegation or disclosure of abuse or neglect
   - Use of physical restraint or seclusion
   - Missing person / elopement (e.g., youth leaving care)
   - Suicide attempt or self-harm requiring intervention
   - Medication error with adverse outcome
   - Property damage or fire
   - Threat or assault involving participants or staff
   - Police involvement or criminal incident
   - Communicable disease outbreak
   - Client rights violation

2. **Flagging** — when creating or editing an event, staff can mark it as an SRE and select the category from the predefined list

3. **Notifications** — when an SRE is flagged:
   - Immediate notification to the program manager (email)
   - Immediate notification to the executive director (email)
   - Optional: notification to a designated compliance/safety officer

4. **Audit trail** — SRE flagging is logged in the audit database with:
   - Who flagged it, when, which category
   - Any follow-up actions recorded
   - Cannot be un-flagged without admin approval (immutable once set)

5. **Reporting** — a dedicated SRE report showing:
   - All SREs in a date range, by program, by category
   - Aggregate counts for board reporting
   - Individual detail for internal review (admin-only)

## Regulatory Context

- Ontario: Ministry of Children, Community and Social Services (MCCSS) requires critical incident reporting within 24 hours for funded programs
- PHIPA: serious incidents involving health information breaches must be reported
- Occupational Health and Safety Act: workplace violence/harassment incidents
- Agency accreditation standards (e.g., Imagine Canada, CARF) often require incident tracking

## Design Considerations

- SRE categories should be configurable per agency (the default list covers common cases)
- Consider a "severity" field (e.g., Level 1 = immediate, Level 2 = within 24h, Level 3 = within 7 days)
- The notification system depends on email being configured (OPS3 prerequisite)
- Follow the existing PII access patterns: SRE details are sensitive, admin-only for exports
- French translations needed for all SRE categories and UI strings

## Dependencies

- Email must be configured (OPS3)
- Events system already exists — this extends it
- Notification infrastructure may need to be built (could start with email-only)
