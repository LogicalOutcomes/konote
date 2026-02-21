# Funder Report Approval Workflow

Task ID: RPT-APPROVE1
Related: DQ2 (pre-report data quality checks), RPT-SCHEMA1 (standardised report schema)

## The Problem

When agencies share outcome data with funders, there is no quality gate or approval step. Data flows straight from the database to a CSV export. Agencies need to:

1. Review data for errors before sharing (e.g. misplaced decimal points in financial metrics)
2. Add context or explanatory notes to the report
3. Explicitly approve what gets shared — funders should only see data the agency has released

## Design Principles (from expert panel review)

- **Enhanced push model, not pull.** The agency exports and sends data. Don't build a funder login or portal.
- **Report-level annotations, not per-value.** Agencies write a cover note for the report, not annotations on every metric value.
- **Extend the existing export flow.** This is not a new module — it's an enhancement to the current funder report export.
- **The approval is implicit in the act of publishing.** The agency reviews, annotates, and clicks "Publish." That's the approval.

## Current Export Flow

1. Staff navigates to Reports > Funder Report
2. Selects report template, date range, programs
3. Clicks "Generate"
4. Data is assembled (apps/reports/funder_report.py)
5. CSV is produced and a secure download link is created (24-hour expiry)
6. Email notification sent to configured recipients

**What's missing:** Steps 3.5 (quality review) and 3.7 (annotation + approval).

## Proposed Flow

1. Staff navigates to Reports > Funder Report
2. Selects report template, date range, programs
3. Clicks "Generate Preview"
4. **NEW — Data Quality Review screen:**
   - Summary of potential issues (see DQ2 design in data-validation-design.md):
     - Outlier values flagged with severity
     - Missing data gaps
     - Stale records
   - Each warning can be: fixed (link to the record), acknowledged, or dismissed
   - Staff can click through to fix underlying data without losing their place
5. **NEW — Report Preview + Annotation:**
   - On-screen preview of what the report will contain (key metrics, totals, demographic breakdowns)
   - "Agency Notes" text field — free-text cover note that accompanies the export
   - Example: "Q1 debt figures include a $50K outlier for one participant who received a large legal settlement. This is accurate, not a data entry error."
6. Staff clicks "Approve and Export"
7. CSV is produced (with agency notes as a header row or cover sheet)
8. Secure download link created
9. Email notification sent
10. **NEW — Audit log entry:** "Report approved by [staff name] at [timestamp] with [N] acknowledged warnings"

## What "Publish" Means

For now, "publish" = "approve the export." The export file includes the agency notes. There is no separate funder-facing system.

In the future, if [funder partner] needs a cross-agency dashboard, each agency's "published" reports could feed a reporting API. But that's a Tier 3 item — don't build it now.

## Report-Level Annotations

The annotation is a single text field attached to the report export. It is:

- Optional — agencies can leave it blank
- Stored with the export record (for audit purposes)
- Included in the CSV as a metadata header or as a separate cover sheet
- Visible in the export history ("View past reports" should show the annotation text)

**Not per-value.** If an agency needs to explain a specific value, they write it in the cover note: "Client #247's debt figure of $52,000 is correct — includes legal settlement."

## Standardised Report Schema (RPT-SCHEMA1)

For umbrella funders like [funder partner], define a standard set of metrics and demographic breakdowns that all partner agencies report on. This enables:

- Consistent reports across agencies (Prosper can combine CSVs)
- The "Publish" action knows exactly what to include
- Reduces per-agency configuration for report templates

**Standard schema for [funder partner] (to be confirmed with [funder contact]):**
- Key outcome metrics (10-15 TBD)
- Demographic breakdowns (age bins, gender, income bracket — TBD)
- Contact outcomes (sessions completed, contact types)
- Program enrolment counts

This schema is defined once at the umbrella level and baked into the [funder partner] configuration template (DEPLOY-TEMPLATE1).

## Key Files

- `apps/reports/views.py` — export views (add quality review + annotation steps)
- `apps/reports/funder_report.py` — `generate_funder_report_data()`
- `apps/reports/aggregations.py` — data assembly
- `apps/reports/models.py` — need to add annotation field to export record model
- New: `apps/reports/data_quality.py` — quality check logic (see DQ2 design)
- Templates: new intermediate screens (quality review, preview + annotation)

## Open Questions

1. Should the quality review screen block the export (can't proceed with unacknowledged warnings) or just warn?
2. Should acknowledged warnings be listed in the export itself (so funders know what was flagged)?
3. What format should agency notes take in the CSV — header rows, separate file, or embedded metadata?
4. Should there be a "draft" state where a report is previewed but not yet approved? (Useful if PM needs to check with a coach before approving.)
5. Should past approved reports be viewable in a "Report History" screen with their annotations?

## Implementation Estimate

- Quality review screen (DQ2): 2-3 weeks
- Annotation field + approval step: 1 week
- Report preview screen: 1-2 weeks
- Standardised schema configuration: 1 week
- **Total: 5-7 weeks** (can be phased — annotation + approval first, quality checks second)

## Dependencies

- DQ1 (entry-time plausibility) reduces the number of errors that reach the report stage — nice to have but not blocking
- DQ2 (pre-report quality checks) is the core of the quality review screen — design is in data-validation-design.md
- RPT-SCHEMA1 (standardised schema) should be defined with [funder partner] before building the report template
