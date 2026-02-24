# QA-R7-EXEC-COMPLIANCE1 — Privacy Compliance Banner & Annual Summary

**Task ID:** QA-R7-EXEC-COMPLIANCE1
**Date:** 2026-02-24
**Status:** Design approved by GK (expert panel, 2 rounds)
**Parking Lot item:** TODO.md line 141

---

## What

Add event-driven privacy compliance visibility to the executive dashboard and a one-line annual summary to the report system. NOT a permanent dashboard card — a banner that appears only when action is needed.

## Why Not a Dashboard Card

The expert panel (Round 2) recommended against a permanent compliance section on the executive dashboard:

- **Human Factors Specialist:** "Dashboards that show zero are demoralising and get ignored. If the card shows '0 requests' for 11 months, the executive stops looking. Then in month 12 when something appears, they miss it."
- **Operations Director:** "My board wants one line: 'We processed X privacy requests this year, all within the legal deadline.' If the answer is zero, I want it to say 'No privacy requests received this year.'"

Event-driven visibility (show it when it matters, hide it when it doesn't) is proven in healthcare alert systems. Executives notice it because it's novel — it wasn't there yesterday.

## Design Decisions (GK-approved)

### Part 1: Pending Request Banner (Executive Dashboard)

A banner that appears on the executive dashboard **only when there are pending items**:

- **Erasure requests pending approval:** "1 erasure request pending — submitted 12 days ago"
- **Data access requests approaching deadline:** "[Name]'s data access request is due in 8 days" (from QA-R7-PRIVACY1's tracking)
- **Overdue items:** Warning style — "1 data access request is overdue (due 3 days ago)"

When nothing is pending, **nothing is shown.** No empty state, no "all clear" message, no card at all.

### Part 2: Annual Summary (Report System)

A one-line summary available in the report generation system for board reports:

> "Privacy requests processed: 2 (average 8 days, all within statutory deadline)"

Or if none:

> "No privacy requests were received this year."

This is a single aggregate query on `ErasureRequest` + `DataAccessRequest` (once PRIVACY1 is built), formatted as a line that can be included in template-driven reports.

### Metrics (derived, not configured)

The system computes these from existing data — no manual entry:

1. Total privacy requests in period (erasure + data access)
2. Average processing time (days from request to completion)
3. Whether all were completed within 30 days (yes/no — for the board summary)
4. Count currently pending

### Aggregation

Organisation-wide only. No per-program breakdown in v1. Most agencies have 2-5 programs — program-level breakdown adds complexity without insight.

### Access

Executive role + Admin role. PMs don't need compliance metrics — they see their own pending items in the regular admin views.

### Time Period

- Banner: always shows current pending items (no time filter)
- Annual summary: rolling 12 months or fiscal year (matches the report template's period picker)

## Implementation

### Part 1: Banner

**Files:**
- `apps/clients/views.py` (or `dashboard/views.py`) — add a context variable with pending counts to the executive dashboard view
- `templates/dashboard/executive_dashboard.html` — conditional banner block at the top, shown only when counts > 0
- Query: `ErasureRequest.objects.filter(status="pending").count()` + `DataAccessRequest.objects.filter(completed_at__isnull=True).count()` (once PRIVACY1 model exists)

**Effort:** Small (1 hour). Queryset aggregate + conditional template block.

### Part 2: Annual Summary

**Files:**
- `apps/reports/export_engine.py` — add a compliance summary helper function
- The summary line can be added to template-driven PDF reports as a `ReportSection` type, or as a simple text include

**Effort:** Small (1 hour). Single aggregate query formatted as a string.

### Dependencies

- Part 1 (banner for erasure requests) can be built now — `ErasureRequest` model exists
- Part 1 (banner for data access requests) depends on QA-R7-PRIVACY1 being built first (needs `DataAccessRequest` model)
- Part 2 depends on Part 1 + the report template system

**Recommendation:** Build the erasure banner first. Add data access request banner when PRIVACY1 lands.

### Tests

- `tests/test_clients.py` or `tests/test_dashboard.py` — verify banner appears when pending, hidden when not
- Verify executive role sees banner, worker role does not

## Expert Panel Context

Round 1 recommended a 4-metric dashboard card (total requests, avg time, % within 30 days, pending count). Round 2 simplified this to event-driven visibility:

- **Human Factors Specialist:** "Show it when action is needed, hide it when it's not. This matches how compliance actually works: it's event-driven, not monitoring-driven."
- **Regulatory Pragmatist:** "For board reports, add a one-line annual summary to the existing report system. Don't build a separate compliance page — one less page to maintain and discover."
- **Nonprofit Consultant:** "Agree on integrating into the executive dashboard rather than a separate page. The card should handle the empty state gracefully — but even better, just don't show it when empty."

## Related Files

- `tasks/design-rationale/executive-dashboard-redesign.md` — dashboard UX patterns
- `tasks/design-rationale/reporting-architecture.md` — report template system
- `apps/clients/erasure_views.py` — existing erasure request queries
- `apps/clients/models.py` — `ErasureRequest` model
