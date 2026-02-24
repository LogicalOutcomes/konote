# QA-R7-PRIVACY1 — PIPEDA Data Access Request (Guided Manual Process)

**Task ID:** QA-R7-PRIVACY1
**Date:** 2026-02-24
**Status:** Design approved by GK (expert panel, 2 rounds)
**Parking Lot item:** TODO.md line 139

---

## What

Build a guided manual process for PIPEDA Section 8 data access requests. NOT an automated export — a checklist page that tells staff what to gather, tracks the request, and logs completion to the audit trail.

## Why Not Automated Export

The expert panel (Round 2) strongly recommended against building an automated PDF export:

1. **Brittleness:** Every model change requires updating the export. New features (surveys, communications) silently make the export incomplete. A legally incomplete export is worse than no export — the agency believes they're compliant when they're not.
2. **Frequency:** Most small nonprofits handle fewer than one data access request per year. Building automated infrastructure for a once-a-year event is over-engineering.
3. **Staff capability:** A guided checklist matches the existing paper-based workflow. Staff already know how to print a page and put papers in an envelope.
4. **Maintenance cost:** The Tech Debt Analyst scored an automated export at 4/5 maintenance burden. The checklist scores 1/5.

## Design Decisions (GK-approved)

### The Checklist

A page accessible from the client profile (Actions dropdown > "Respond to Data Access Request") that shows:

**Step 1: Log the request**
- Date request received (defaults to today)
- How received (verbal, written, email)
- 30-day deadline auto-calculated and displayed: "Response due by [date]"

**Step 2: Gather this person's information**

Checklist of what to collect (staff checks off as they go):

- [ ] Client profile (print the profile page)
- [ ] Program enrolments and status
- [ ] Progress notes (use the notes list — filter by this participant, print or export)
- [ ] Plan goals and metric history (print the plan page)
- [ ] Communication log entries
- [ ] Survey responses (if your agency uses surveys)
- [ ] **Alerts and flags — review before including. You may withhold safety-related notes under PIPEDA s.9(1) if disclosure could threaten the safety of others.**

The checklist items are a **static universal list**. If a module doesn't apply (e.g., the agency doesn't use surveys), staff skip it. The checklist should note: "Not all items may apply to your agency. Include what you have."

**Step 3: Deliver and log completion**
- How delivered (in person, mail, email)
- Date delivered
- "Mark as Complete" button — logs to audit DB

### 30-Day Tracking

- When a request is logged (Step 1), the system records the date and calculates the 30-day PIPEDA deadline
- The admin dashboard shows a banner when a request is pending: "[Name]'s data access request is due in X days"
- After 30 days, the banner turns to a warning style
- When marked complete, the banner disappears and the audit trail records fulfilment

### Access Control

- **Who can start a request:** PM or Admin (not frontline workers — this is an administrative/legal process)
- **Who sees the pending banner:** PM and Admin roles on the admin dashboard
- **Portal self-service:** Deferred. Build staff-only path first. Add portal trigger only if agencies request it.

### Audit Trail

Every action logged to the audit database:
- Request logged (who, when, for which client)
- Request completed (who, when, delivery method)
- Request overdue (automated flag if 30 days pass without completion)

## Implementation

### New Model (lightweight)

```python
class DataAccessRequest(models.Model):
    client_file = models.ForeignKey("clients.ClientFile", on_delete=models.CASCADE)
    requested_at = models.DateField()
    request_method = models.CharField(max_length=20, choices=[
        ("verbal", _("Verbal")),
        ("written", _("Written")),
        ("email", _("Email")),
    ])
    deadline = models.DateField()  # auto-set to requested_at + 30 days
    completed_at = models.DateField(null=True, blank=True)
    delivery_method = models.CharField(max_length=20, blank=True, choices=[
        ("in_person", _("In person")),
        ("mail", _("Mail")),
        ("email", _("Email")),
    ])
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
```

### Files

- `apps/clients/models.py` — add `DataAccessRequest` model
- `apps/clients/views.py` or new `apps/clients/data_access_views.py` — log request, checklist page, mark complete
- `templates/clients/data_access_request.html` — the checklist page
- `templates/clients/data_access_log.html` — form to log a new request
- Dashboard template — pending request banner
- Migration file
- `tests/test_clients.py` — permission checks, deadline calculation, audit logging

### Effort

Medium (3-4 hours). Most of the work is the checklist template and the request tracking model.

## Expert Panel Context

Round 1 panel recommended an automated PDF export. Round 2 panel (focused on brittleness and maintenance) overturned this:

- **Operations Director:** "My staff already know how to print a page and put papers in an envelope. They need to know what to include."
- **Tech Debt Analyst:** "A comprehensive data export means the export code must know about every model that holds personal information. When you add a feature, someone must update the export. If they forget, the export is legally incomplete — which is worse than not having the feature."
- **Regulatory Pragmatist:** "The Privacy Commissioner's guidance says organisations must respond to requests — it doesn't say they need a button in their software to do it."

## Related Files

- `tasks/design-rationale/phipa-consent-enforcement.md` — consent model and enforcement scope
- `tasks/erasure-hardening.md` — erasure system (separate from data access)
- `apps/clients/erasure_views.py` — pattern reference for admin-only privacy features
