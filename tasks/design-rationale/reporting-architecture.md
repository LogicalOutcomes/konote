# Reporting Architecture — Design Rationale Record

**Date:** 2026-02-21
**Status:** Steps 1-10 implemented. All DRR steps complete.
**Canonical reference:** This is the single source of truth for all reporting design decisions in KoNote. Other documents (dashboard, navigation, etc.) defer to this document for reporting behaviour.
**Dependencies:** Privacy thresholds and consortium data sharing follow `tasks/design-rationale/multi-tenancy.md` (settled). This document does not override that DRR.

## Core Principle

**Report templates ARE the report.** `ReportTemplate` + `ReportMetric` define which metrics, with what aggregation, in what sections, with partner-specific display labels and period boundaries. The generate form is driven by the template — it does not offer manual metric selection, program dropdowns, or raw fiscal year pickers.

## Two Distinct Paths

| Path | URL | Who sees it | Purpose |
|------|-----|-------------|---------|
| **Template-driven** | `/reports/generate/` | Everyone (executives, PMs, admins) | Produce a report matching a partner's specification |
| **Ad-hoc export** | `/reports/export/` | Program managers, executives, and admins | Data extraction with manual control (aggregate-only for executives) |

Executives see both paths in navigation (decided 2026-02-22 per stakeholder request). The ad-hoc export enforces aggregate-only output for executives via `is_aggregate_only_user()` — no individual participant data is exposed. Templates remain the **primary** path for executives; Custom Export is a secondary option for one-off needs.

## Entry Points

| From | Action | Destination |
|------|--------|-------------|
| **Navigation menu** | "Reports" dropdown | Both paths for all report-capable users (Generate Report + Custom Export) |
| **Executive dashboard** | "Generate funder report" button | `/reports/generate/` with template pre-selected if the current program maps to exactly one template |
| **Program detail page** | "Generate report" link (future) | `/reports/generate/` with template pre-selected |

When arriving from a program context (dashboard or program page), the form pre-selects the template whose Partner includes that program. If multiple templates match, the dropdown is shown with those templates filtered to the top. If no template matches, the full dropdown is shown.

## Template-Driven Form (`/reports/generate/`)

### Executive flow

The executive does NOT choose a program. The template already knows its programs (via Partner -> Programs M2M).

**Form fields (in order):**
1. **Which report?** — dropdown of available templates, labelled by partner + report name (e.g., "United Way — Quarterly Outcome Report", "Board of Directors — Annual Report"). Only shows templates linked to programs the user can access.
2. **Which period?** — dropdown populated from template's `period_type` and `period_alignment` (e.g., "Q3 FY2025-26"). Raw date inputs only for `period_type=custom`.
3. **Export format** — CSV/PDF, constrained by `template.output_format` if not "mixed". Hidden if template only supports one format.
4. **Recipient details** — who and why (audit requirement).
5. **Generate Report** button.

**What the user does NOT see:**
- Program dropdown (template defines programs via Partner)
- Metric checkboxes (template defines metrics via `ReportMetric`)
- Grouping dropdown (template defines demographics via `DemographicBreakdown`)
- Achievement rate toggle (template's `ReportMetric.aggregation` handles this)
- Fiscal year dropdown (template's period picker replaces this)

**What the form shows as read-only confirmation:**
- "Programs:" — list from Partner.get_programs()
- "This report includes:" — list of metrics from `ReportMetric`, using `display_label`
- "Demographic breakdowns:" — list from `DemographicBreakdown`
- "Report for:" — Partner name

### No template available

When an executive has no templates available (no active templates linked to their accessible programs):

> "No report templates have been set up yet. Report templates define what metrics and demographic breakdowns to include for recurring partner reports. Contact your administrator to create one."

The page links to Custom Export as an alternative ("In the meantime, you can create a one-off report using Custom Export"). Admins also see a link to template management.

Do NOT show metric checkboxes on this page. Custom Export is a separate page with its own aggregate-only safeguards for executives.

### Period picker logic

The period picker derives from the template, not from a generic fiscal year dropdown:

| `period_type` | `period_alignment` | Picker shows |
|---------------|-------------------|--------------|
| `quarterly` | `fiscal` | "Q1 FY2025-26 (Apr-Jun)", "Q2 FY2025-26 (Jul-Sep)", etc. Uses `fiscal_year_start_month` |
| `quarterly` | `calendar` | "Q1 2026 (Jan-Mar)", "Q2 2026 (Apr-Jun)", etc. |
| `quarterly` | `grant` | Quarters derived from `Partner.grant_period_start` |
| `monthly` | any | Month dropdown |
| `semi_annual` | `fiscal` | "H1 FY2025-26 (Apr-Sep)", "H2 FY2025-26 (Oct-Mar)" |
| `annual` | `fiscal` | "FY2025-26", "FY2024-25", etc. |
| `annual` | `grant` | Grant year derived from partner dates |
| `custom` | any | Raw date_from / date_to inputs |

This prevents the most common funder reporting error: submitting data for wrong period boundaries.

## Ad-Hoc Export Form (`/reports/export/`) — PM only

**Restructured field order:**
1. **Program** — PMs select which program to extract data from
2. **Report template** (optional) — selecting one auto-fills downstream fields
3. **Fiscal year / Date range** — smart: template overrides with period picker when selected
4. **Metrics** — auto-checked from template when selected; consortium-required locked; all shown
5. **Grouping** — disabled when template selected
6. **Additional options** — achievement rate
7. **Export format**
8. **Recipient details**
9. **Generate**

**When template selected:** Metrics auto-check from `ReportMetric`, consortium-required metrics shown as locked checkboxes with explanation, grouping disabled, period picker replaces raw dates.

**When no template:** Full manual control. All metrics pre-selected by default (not blank).

**Consortium warning:** When the selected program is linked to a consortium partner, show: "This program reports to [Consortium Name]. For partner-compliant reports, use the template-driven report instead."

### Consortium-required metrics

When `ReportMetric.is_consortium_required=True`:
- In ad-hoc form: metric appears as a locked checkbox (checked, disabled) with tooltip: "Required by [Consortium Name] reporting standards"
- PM can add additional metrics but cannot remove consortium ones
- In template-driven form: no special UI needed — template includes them automatically

## Export Pipeline

### Template-driven CSV output

```csv
Report: United Way Quarterly Outcome Report
Program: Youth Employment Services
Period: Q3 FY2025-26 (Oct 1 – Dec 31, 2025)
Generated: 2026-02-21
Generated by: Kwame Asante (Executive Director)
Template: United Way Quarterly v2.1

Metric,All Participants,Age 13-17,Age 18-24,Age 25+
Youth Engagement Index (mean),3.8,3.2,4.1,3.9
Youth Engagement Index (n),50,12,28,10
Goal Achievement Rate (%),64%,50%,71%,60%
```

- Rows are metrics (not clients). Columns are demographic groups.
- Uses `ReportMetric.display_label` for column headers (partner terminology)
- Applies `ReportMetric.aggregation` per metric (count, average, threshold_percentage, etc.)
- Metadata header makes the file self-documenting
- Small-cell suppression applied (groups < 10 shown as "< 10")

### Template-driven PDF output

Structured by `ReportSection` (ordered by `sort_order`):
- `service_stats`: Program overview (enrolled, active, new)
- `metrics_table`: Metrics table using display labels + demographic columns
- `narrative`: Placeholder for agency notes ("[To be added during review]")
- `chart`: Trend visualisation over last 4 periods
- `demographic_summary`: Demographic breakdown tables

### Ad-hoc CSV output

Unchanged — flat per-client-per-metric rows. This is a data extract, not a funder report.

### Implementation

New module: `reports/export_engine.py` with two entry points:
- `generate_template_report(template, date_range, user)` — template-driven (program comes from template)
- `generate_adhoc_export(metrics, program, date_range, grouping, user)` — legacy ad-hoc

Separation ensures template pipeline can't accidentally fall back to flat output.

## Aggregation Rules (from ReportMetric)

| `aggregation` | What it produces | Example output |
|---------------|-----------------|----------------|
| `count` | COUNT of values | "Satisfaction Responses (n): 50" |
| `average` | AVG of values | "Mean Satisfaction Score: 3.8" |
| `sum` | SUM of values | "Total Hours: 1,240" |
| `average_change` | AVG of (last - first) per client | "Mean Change: +0.6" |
| `threshold_count` | COUNT where value >= `threshold_value` | "Clients Scoring 4+: 32" |
| `threshold_percentage` | threshold_count / total x 100 | "% Scoring 4+: 64%" |
| `percentage` | (count meeting threshold / total) x 100 | "% Meeting Minimum: 82%" |

## Navigation

| Role | "Reports" menu shows |
|------|---------------------|
| Executive | `/reports/generate/` only |
| Program Manager | `/reports/generate/` + `/reports/export/` |
| Admin | Both + template management |

## Privacy Safeguards (enforced regardless of path)

These apply to both template-driven and ad-hoc exports, and to any other page that displays aggregate outcome data (including the executive dashboard).

**Thresholds are set in `multi-tenancy.md` (settled):**
- Small-cell suppression: cells where n < 5 shown as "< 5" (Canadian health data de-identification standard)
- Programs with < 50 enrolled: no demographic grouping
- Confidential programs: no demographic grouping

**Access controls:**
- PII fields never available for grouping
- Aggregate-only users: no individual records, no record IDs, no author names

**Consent (from multi-tenancy architecture):**
- Aggregate reporting requires `consent_to_aggregate_reporting` on the program/client enrolment
- Data without consent is excluded from all aggregate outputs, including template-driven reports
- Consent is per-program, not per-agency (see `multi-tenancy.md` for sharing granularity)

## Consortium Reporting (future — see multi-tenancy.md)

When multi-tenancy is live, template-driven reports are the mechanism for consortium data sharing:

1. Agency generates a template-driven report (this architecture)
2. If the template's Partner is a consortium member, the report can be **published** as a `PublishedReport` (model in `consortia` app, tenant-scoped)
3. `PublishedReport` stores the aggregate output — never individual records
4. Consortium dashboard (deferred, per multi-tenancy DRR) consumes `PublishedReport` data
5. Sharing granularity is **per-program**, not per-agency — different programs within one agency may share with different funders

**This is why templates are the primary report path for consortium reporting.** Manual metric selection makes cross-agency reports impossible because each agency would choose different metrics. The template guarantees consistency across consortium members. Executives can also use Custom Export for one-off aggregate needs, but only template-driven reports feed the consortium pipeline.

**Implementation note:** Consortium reporting is deferred until "after report data model is validated with real data" (multi-tenancy DRR). The template-driven pipeline built here is a prerequisite.

## Implementation Sequence

| Step | What | Depends on |
|------|------|-----------|
| 1 | Create `TemplateExportForm` class | Nothing |
| 2 | Create `export_template_driven.html` template | Step 1 |
| 3 | Add `/reports/generate/` URL + view | Steps 1-2 |
| 4 | Build `generate_template_report()` in export_engine.py | Step 3 |
| 5 | Add HTMX fragments for template -> period cascade | Steps 1-3 |
| 6 | Wire ReportMetric aggregation into export pipeline | Step 4 |
| 7 | Wire ReportSection into PDF output | Step 4 |
| 8 | Add consortium-required locking to ad-hoc form | Steps 1-2 |
| 9 | ~~Update navigation~~ Done (2026-02-22): all report users see dropdown with Generate Report + Custom Export | Steps 3, 8 |
| 10 | Restructure ad-hoc form field order + template auto-fill via HTMX | Step 8 |

## GK Review Required

- Period picker labels and quarter boundaries (fiscal year start month varies by funder)
- "No template" message wording for executives
- Whether the metadata header fields are complete for Ontario nonprofit reporting
- Aggregation rule definitions (do they match evaluation methodology?)
- Entry point labels (dashboard button wording, nav menu labels)

## Anti-Patterns (rejected)

- **Removing aggregate-only enforcement on ad-hoc for executives** — executives may use Custom Export but MUST only receive aggregate output (enforced by `is_aggregate_only_user()`). Never expose individual participant data to executives via any path
- **Manual metric selection when template exists** — the template defines the report, not the user
- **Program dropdown for executives** — template already knows its programs via Partner
- **Generic fiscal year dropdown when template has period_type** — causes date boundary errors across agencies
- **Single form for both paths** — different actions (report generation vs. data extraction) need different forms
- **CSV download button on dashboard** — unaudited export path that bypasses template architecture, period logic, and privacy safeguards. The dashboard links to the report form; it does not produce files itself
- **Inventing suppression thresholds per feature** — n < 5 is set in the multi-tenancy DRR as the Canadian standard. All features use that threshold, not their own
- **Bypassing consent checks in aggregate reports** — `consent_to_aggregate_reporting` must be checked. Data without consent is excluded, not suppressed

## Relationship to Other Documents

- **Executive dashboard** (`executive-dashboard-redesign.md`): Monitoring page at `/clients/executive/`. Links to `/reports/generate/` via action bar button. The dashboard does not produce exportable files — all data output goes through this reporting architecture. Privacy safeguards (suppression, consent) apply to dashboard displays too.
- **Multi-tenancy architecture** (`multi-tenancy.md`): Authoritative source for privacy thresholds (n < 5), consortium data model (`PublishedReport`, `ConsortiumMembership`, `ProgramSharing`), consent requirements, and sharing granularity. This reporting doc does not override those decisions.
- **Program detail pages**: May link to `/reports/generate/` with template pre-selected (future).
- **Template management** (admin): Where templates, metrics, sections, and partners are configured. Not covered in this document.
