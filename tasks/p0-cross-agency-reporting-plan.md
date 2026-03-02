# P0 Deliverable: Cross-Agency Reporting Plan

**Requirement ID:** RP4 (cross-agency data rollup and reporting)
**Deliverable type:** Costed implementation plan (not live code by March 31)
**Date:** 2026-03-02
**Source documents:** tasks/design-rationale/reporting-architecture.md (DRR), tasks/design-rationale/multi-tenancy.md, tasks/funder-report-approval.md

---

## Executive Summary

Cross-agency reporting enables a funder to see aggregate outcome data across multiple agencies — without accessing any individual agency's system. KoNote's template-driven reporting architecture is already built and deployed. This plan describes how to extend it to support cross-agency rollup, a reporting API, and an umbrella dashboard.

**Key design principle:** The funder never logs into an agency's KoNote instance. Agencies publish aggregate reports through the existing template-driven pipeline. The funder consumes published reports through a separate API or dashboard.

---

## How It Works

```
Agency A                    Agency B                    Agency C
┌──────────┐               ┌──────────┐               ┌──────────┐
│ KoNote   │               │ KoNote   │               │ KoNote   │
│ instance │               │ instance │               │ instance │
│          │               │          │               │          │
│ Template │               │ Template │               │ Template │
│ Report   │               │ Report   │               │ Report   │
│ ↓        │               │ ↓        │               │ ↓        │
│ Preview  │               │ Preview  │               │ Preview  │
│ ↓        │               │ ↓        │               │ ↓        │
│ Approve  │               │ Approve  │               │ Approve  │
│ ↓        │               │ ↓        │               │ ↓        │
│ Publish  │               │ Publish  │               │ Publish  │
└────┬─────┘               └────┬─────┘               └────┬─────┘
     │                          │                          │
     │    PublishedReport        │    PublishedReport        │
     └──────────┬───────────────┴──────────┬───────────────┘
                │                          │
                ▼                          ▼
     ┌──────────────────────────────────────────┐
     │        Cross-Agency Reporting API         │
     │   (reads PublishedReport from each tenant) │
     └──────────────────┬───────────────────────┘
                        │
                        ▼
     ┌──────────────────────────────────────────┐
     │        Umbrella Dashboard                 │
     │   (funder sees aggregate metrics,         │
     │    report status, instance health)        │
     └──────────────────────────────────────────┘
```

---

## What Already Exists

The reporting architecture (DRR, all 10 implementation steps complete) provides the foundation:

| Component | Status | What it does |
|-----------|--------|-------------|
| `ReportTemplate` | Built | Defines which metrics, aggregation rules, period boundaries, demographic breakdowns per funder |
| `ReportMetric` | Built | Per-metric aggregation (count, average, threshold_percentage, etc.) with display labels |
| `DemographicBreakdown` | Built | Age bins, custom field groupings with small-cell suppression |
| `Partner` model | Built | Funder/network relationship — links to programs |
| `SecureExportLink` | Built | Time-limited download with audit trail |
| Template-driven form | Built | `/reports/generate/` — executive-friendly, template-driven report generation |
| Export pipeline | Built | `generate_template_report()` in `export_engine.py` — CSV/PDF with suppression |
| Approval workflow | In progress | RPT-APPROVE1 — preview, annotation, explicit approve step |

**What's missing:** The "Publish" step that saves aggregate report data for cross-agency consumption, the API that exposes published reports, and the dashboard that displays them.

---

## Implementation Plan

### Phase 1: PublishedReport Model and Publish Step

**What:** After an agency approves a funder report, they can optionally "publish" it — saving the aggregate data for the funder to consume.

**Work:**
- Create `PublishedReport` model in the `consortia` app (tenant-scoped):
  - `report_template` FK — which template was used
  - `consortium` FK — which funder/consortium this is published to
  - `period_start`, `period_end` — reporting period
  - `data_json` — the aggregate report data (metrics, demographics, service stats)
  - `published_by` FK — who approved and published
  - `published_at` — timestamp
  - `agency_notes` — carried from the approval step
  - `status` — draft, published, superseded
- Add "Publish to [Funder Name]" button on the approval confirmation page
- Data stored in `data_json` is the same aggregate output that goes into the CSV — no individual records

**Depends on:** Multi-tenancy (MT-CORE1) — `PublishedReport` is a tenant-scoped model
**Effort:** 2–3 days

### Phase 2: Cross-Agency Reporting API

**What:** A REST API endpoint that the funder can call to retrieve published reports from across agencies.

**Design:**
- **Endpoint:** `GET /api/v1/consortium/{consortium_id}/reports/`
- **Authentication:** API key per consortium (stored in Consortium model, shared schema)
- **Query parameters:** `period_start`, `period_end`, `program_type`, `format` (json/csv)
- **Response:** Array of published reports with agency name, program name, period, and aggregate metrics
- **Rate limiting:** 100 requests/hour per API key
- **Audit logging:** Every API call logged with API key, IP, timestamp, query parameters

**Privacy safeguards (from reporting-architecture DRR):**
- Only aggregate data — never individual participant records
- Small-cell suppression applied (n < 5 shown as "< 5")
- Only data from programs where `consent_to_aggregate_reporting` is true
- Only reports with status = "published"

**Work:**
- Create API views (Django REST Framework or plain Django JSON views)
- API key model in shared schema (ConsortiumAPIKey)
- Rate limiting middleware
- API documentation (OpenAPI/Swagger)

**Depends on:** Phase 1, multi-tenancy (API needs to query across tenant schemas)
**Effort:** 3–5 days

### Phase 3: Umbrella Dashboard

**What:** A web dashboard where the funder can see aggregate metrics, report status, and instance health across all agencies.

**Design:**
- **Access:** Separate login (not an agency KoNote login) — funder user type in shared schema
- **URL:** `console.konote.ca` or similar (separate from agency subdomains)
- **Dashboard shows:**
  - Agency list with last report date, health status (up/down via UptimeRobot API)
  - Report timeline — which agencies have submitted reports for the current period
  - Aggregate metrics across agencies (sum/average of published report data)
  - Missing reports — which agencies haven't published for the current period
  - Download: combined CSV/PDF across all agencies for the current period
- **Does NOT show:** Individual participant data, per-client records, detailed agency configuration

**Work:**
- Create `FunderUser` model in shared schema
- Dashboard views + templates (server-rendered, consistent with KoNote design)
- Report aggregation logic (combine `PublishedReport.data_json` across tenants)
- Instance health integration (UptimeRobot API or similar)
- Combined report download (merge agency reports into single document)

**Depends on:** Phase 2
**Effort:** 5–8 days

---

## Configurable Metrics

A key concern was "which metrics to aggregate." The answer: **metrics are configured per report template, not hardcoded.** The `ReportTemplate` + `ReportMetric` system already handles this:

1. Admin creates a report template for the funder (e.g., "Quarterly Outcome Report")
2. Template defines exactly which metrics to include, with aggregation rules and display labels
3. All agencies using that template report the same metrics in the same format
4. When the funder needs different metrics, update the template — not the code

This means **no specific funder requirements are needed before building.** The system is inherently configurable. The funder specifies what they want during onboarding, and it's configured through the admin UI.

---

## Effort Summary

Estimates assume AI-assisted development (Claude Code with Opus 4.6).

| Phase | Description | Effort | Dependencies |
|-------|-------------|--------|-------------|
| 1 | PublishedReport model + publish step | 2–3 hours | Multi-tenancy (MT-CORE1), approval workflow (RPT-APPROVE1) |
| 2 | Cross-agency reporting API | 3–5 hours | Phase 1 |
| 3 | Umbrella dashboard | 4–6 hours | Phase 2 |
| **Total** | | **~1.5–2 developer days** | |

**Calendar time:** 1 week, accounting for review cycles.

---

## Cost Model

### Development Cost

With AI-assisted development (Claude Code):
- **~1.5–2 days of session time**
- **Claude Code API cost: ~$30–60 CAD** (estimated token usage)
- **Human review time: ~2–4 hours** (GK reviewing data model, PB reviewing PRs)

### Ongoing Cost

- API hosting: included in existing infrastructure (no separate server needed)
- Dashboard hosting: included in existing infrastructure
- UptimeRobot integration: free tier (50 monitors)
- **Incremental cost: ~$0/month** (runs on existing multi-tenant infrastructure)

---

## Sequencing

```
1. RPT-APPROVE1 (approval workflow)     ← in progress now
           |
           v
2. MT-CORE1 (multi-tenancy)            ← after first agency live
           |
           v
3. Phase 1 (PublishedReport + publish)
           |
           v
4. Phase 2 (reporting API)
           |
           v
5. Phase 3 (umbrella dashboard)
```

Phases 1–3 can begin as soon as multi-tenancy is live. The approval workflow (RPT-APPROVE1) can be built now, independently.

---

## What This Plan Demonstrates (for P0)

- **RP4 (cross-agency rollup):** Configurable metric system (already built) + PublishedReport model + aggregation API. Metrics are defined per funder through templates — no hardcoded requirements.
- **Architecture is proven:** The template-driven reporting pipeline is already in production. Cross-agency extends it, doesn't replace it.
- **Privacy by design:** Small-cell suppression, consent checking, and aggregate-only output are already enforced. Cross-agency reporting inherits all safeguards.
- **Credible timeline:** ~1.5–2 days of AI-assisted development after multi-tenancy is live. Can be demonstrated within 1–2 weeks of multi-tenancy completion.
