# Unified Reporting Architecture — Partner-Centric Model

**Date:** 2026-02-21
**Status:** Architecture validated by two expert panels; ready for implementation planning
**Related TODO IDs:** RPT-SCHEMA1, SCALE-ROLLUP1, MT-CONSORT1, SCALE-API1

## Problem Statement

Nonprofits report to many different entities — funders, networks, boards, regulators, collaborations — each with different requirements. A single program may have 3-4 reporting relationships, each requiring different metrics, demographics, time periods, and aggregation rules.

The current reporting system requires manual metric selection each time a report is generated. Report templates should be **complete definitions** that encode all requirements once. And this architecture must work for the entire sector, not just one deployment.

## Why "Partner" (Not "Stakeholder" or "Funder")

- **"Funder"** is too narrow — boards, networks, and collaborations also require reports
- **"Stakeholder"** is increasingly problematic in Canada, particularly regarding Indigenous nations
- **"Partner"** is inclusive, accurate, and reflects the collaborative nature of nonprofit work: funders, donors, networks, accreditation bodies, and boards are all partners in the mission

The model name is `Partner`. KoNote's terminology system can let agencies customise the UI label if needed.

## Architecture Overview

Two expert panels examined this problem (a report template panel and a unified architecture panel). Key conclusions:

1. **Partner is a separate entity**, not a field on ReportTemplate. One partner (e.g., IRCC) may require 3 different reports (monthly, quarterly, annual). Normalisation demands a separate entity.
2. **Partner → Program is many-to-many**, and optional. A provincial grant funds two programs; the board oversees all programs (empty M2M = "all programs").
3. **Reports and surveys both connect to Partner.** A funder may require specific assessment tools alongside specific reports.
4. **ConsortiumReportSchema is the "template of templates."** When a network like Prosper Canada defines a standard schema, each agency instantiates it as their own Partner + ReportTemplate.
5. **Scheduling has three phases**: data cutoff → draft deadline → submission deadline. Supports calendar-aligned, grant-aligned, and fixed-date recurrence.

## Entity Relationship Diagram

```
[SHARED SCHEMA — visible across tenants]

Consortium
  ├── name, slug, description, is_active
  │
  └──► ConsortiumReportSchema
         ├── version, name, schema_definition (JSON)
         ├── effective_date, is_current
         └── (defines standard metrics + demographics for the network)

─────────────────────────────────────────────────────────

[TENANT SCHEMA — per agency]

Program ◄──── M2M ────► Partner
                          ├── name, partner_type
                          ├── consortium (FK → Consortium, nullable)
                          ├── contact_name, contact_email
                          ├── grant_number (nullable)
                          ├── grant_period_start/end (nullable)
                          ├── is_active
                          ├── created_from_document (FileField)
                          │
                          ├──► ReportTemplate (FK: partner)
                          │      ├── name, description
                          │      ├── consortium_schema (FK → ConsortiumReportSchema, nullable)
                          │      ├── consortium_schema_version (nullable)
                          │      ├── period_type, period_alignment
                          │      ├── fiscal_year_start_month
                          │      ├── output_format, language, is_active
                          │      │
                          │      ├──► ReportSection
                          │      │      └── title, section_type, instructions, sort_order
                          │      │
                          │      ├──► ReportMetric
                          │      │      ├── FK → MetricDefinition
                          │      │      ├── aggregation, threshold_value
                          │      │      ├── display_label, sort_order
                          │      │      └── is_consortium_required
                          │      │
                          │      ├──► DemographicBreakdown [EXISTING]
                          │      │
                          │      └──► ReportSchedule
                          │             ├── recurrence_type
                          │             ├── data_cutoff / draft_deadline / submission_deadline
                          │             ├── assignee, reviewers
                          │             └── is_active
                          │
                          └──► Survey (optional FK: partner)
                                 └── "required by this partner"

MetricDefinition
  ├── superseded_by (FK → self, nullable)
  └── (referenced by ReportMetric AND SurveyQuestion scoring)

ConsortiumMembership, ProgramSharing, PublishedReport
  └── (from multi-tenancy plan — unchanged)
```

## Data Model — Django Models

### Partner (New)

```python
class Partner(models.Model):
    PARTNER_TYPES = [
        ("funder", "Funder"),
        ("network", "Network / Collaboration"),
        ("board", "Board of Directors"),
        ("regulator", "Government / Regulator"),
        ("accreditation", "Accreditation Body"),
        ("donor", "Donor"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=255)
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPES)
    consortium = models.ForeignKey(
        "tenants.Consortium", on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Link to cross-agency network, if applicable."
    )
    programs = models.ManyToManyField(
        "programs.Program", blank=True,
        help_text="Programs this partner funds or oversees. "
                  "Leave empty for organisation-wide partners (e.g., board)."
    )
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    grant_number = models.CharField(max_length=100, blank=True)
    grant_period_start = models.DateField(null=True, blank=True)
    grant_period_end = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_from_document = models.FileField(
        upload_to="partner_docs/", null=True, blank=True,
        help_text="Original requirements document."
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "reports"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_programs(self):
        """Linked programs, or all active programs if none specified."""
        programs = self.programs.all()
        if programs.exists():
            return programs
        from apps.programs.models import Program
        return Program.objects.filter(is_active=True)
```

### ReportTemplate (Existing, Enhanced)

```python
class ReportTemplate(models.Model):
    PERIOD_TYPES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("semi_annual", "Semi-annual"),
        ("annual", "Annual"),
        ("custom", "Custom"),
    ]
    PERIOD_ALIGNMENTS = [
        ("calendar", "Calendar year (Jan-Dec)"),
        ("fiscal", "Fiscal year (custom start month)"),
        ("grant", "Grant period"),
    ]
    OUTPUT_FORMATS = [
        ("tabular", "Tables and charts"),
        ("narrative", "Narrative with data"),
        ("mixed", "Mixed — narrative and tables"),
    ]

    partner = models.ForeignKey(
        Partner, on_delete=models.CASCADE, related_name="report_templates"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Consortium schema tracking
    consortium_schema = models.ForeignKey(
        "tenants.ConsortiumReportSchema",
        on_delete=models.SET_NULL, null=True, blank=True,
    )
    consortium_schema_version = models.PositiveIntegerField(null=True, blank=True)

    # Reporting period
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPES)
    period_alignment = models.CharField(max_length=20, choices=PERIOD_ALIGNMENTS)
    fiscal_year_start_month = models.PositiveSmallIntegerField(
        default=1, help_text="1=Jan, 4=Apr (Ontario govt), 7=Jul, etc."
    )

    output_format = models.CharField(max_length=20, choices=OUTPUT_FORMATS, default="mixed")
    language = models.CharField(
        max_length=5, default="en",
        choices=[("en", "English"), ("fr", "French"), ("both", "Bilingual")],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "reports"

    def __str__(self):
        return f"{self.name} ({self.partner.name})"
```

### ReportSection, ReportMetric, ReportSchedule (New)

```python
class ReportSection(models.Model):
    SECTION_TYPES = [
        ("metrics_table", "Metrics Table"),
        ("demographic_summary", "Demographic Summary"),
        ("narrative", "Narrative / Written Section"),
        ("chart", "Chart / Visualisation"),
        ("service_stats", "Service Statistics"),
    ]

    report_template = models.ForeignKey(
        ReportTemplate, on_delete=models.CASCADE, related_name="sections"
    )
    title = models.CharField(max_length=255)
    title_fr = models.CharField(max_length=255, blank=True)
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES)
    instructions = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "reports"
        ordering = ["sort_order"]


class ReportMetric(models.Model):
    AGGREGATION_TYPES = [
        ("count", "Count of participants"),
        ("average", "Average value"),
        ("average_change", "Average change (intake to latest)"),
        ("percentage", "Percentage of participants"),
        ("threshold_count", "Count meeting threshold"),
        ("threshold_percentage", "Percentage meeting threshold"),
        ("sum", "Sum total"),
    ]

    report_template = models.ForeignKey(
        ReportTemplate, on_delete=models.CASCADE, related_name="metrics"
    )
    metric_definition = models.ForeignKey(
        "plans.MetricDefinition", on_delete=models.CASCADE
    )
    section = models.ForeignKey(
        ReportSection, on_delete=models.SET_NULL, null=True, blank=True
    )
    aggregation = models.CharField(max_length=25, choices=AGGREGATION_TYPES)
    threshold_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    display_label = models.CharField(max_length=255, blank=True)
    display_label_fr = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_consortium_required = models.BooleanField(default=False)

    class Meta:
        app_label = "reports"
        ordering = ["sort_order"]


class ReportSchedule(models.Model):
    RECURRENCE_TYPES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("semi_annual", "Semi-annual"),
        ("annual", "Annual"),
        ("grant_period", "Relative to grant period"),
        ("fixed_dates", "Specific dates"),
    ]

    report_template = models.ForeignKey(
        ReportTemplate, on_delete=models.CASCADE, related_name="schedules"
    )
    recurrence_type = models.CharField(max_length=20, choices=RECURRENCE_TYPES)
    fixed_dates = models.JSONField(null=True, blank=True)
    data_cutoff_offset_days = models.PositiveIntegerField(default=5)
    draft_deadline_offset_days = models.PositiveIntegerField(default=15)
    submission_deadline_offset_days = models.PositiveIntegerField(default=30)
    assignee = models.ForeignKey(
        "auth_app.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_reports",
    )
    reviewers = models.ManyToManyField(
        "auth_app.User", blank=True, related_name="report_reviews",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "reports"
```

### ConsortiumReportSchema (Shared Schema — Add to Tenants App)

```python
class ConsortiumReportSchema(models.Model):
    consortium = models.ForeignKey(
        Consortium, on_delete=models.CASCADE, related_name="report_schemas"
    )
    version = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=255)
    schema_definition = models.JSONField(
        help_text="Standard metrics, demographics, and report structure."
    )
    effective_date = models.DateField()
    is_current = models.BooleanField(default=True)
    change_notes = models.TextField(blank=True)

    class Meta:
        app_label = "tenants"
        unique_together = [("consortium", "version")]
        ordering = ["-version"]
```

### Survey Enhancement (Existing Model, Add FK)

```python
# In apps/surveys/models.py — add to existing Survey model:
partner = models.ForeignKey(
    "reports.Partner", on_delete=models.SET_NULL,
    null=True, blank=True, related_name="required_surveys",
    help_text="Partner that requires this assessment, if any."
)
```

### MetricDefinition Enhancement (Existing Model, Add Lineage)

```python
# In apps/plans/models.py — add to existing MetricDefinition:
superseded_by = models.ForeignKey(
    "self", null=True, blank=True, on_delete=models.SET_NULL,
    help_text="If this metric was replaced by a newer version."
)
superseded_date = models.DateField(null=True, blank=True)
```

## How It All Connects

### Single-Agency Reporting (No Consortium)

```
Partner: "United Way of Greater Toronto"
  type: funder
  programs: [Employment Readiness]
  grant: UW-2026-1234

  ReportTemplate: "United Way Quarterly"
    period: quarterly, calendar-aligned
    sections:
      - Demographics (age, gender breakdown)
      - Outcomes (3 metrics: employment rate, income change, housing stability)
      - Narrative (program highlights)
    schedule: due 30 days after quarter-end, draft at 15 days, data cutoff at 5 days
```

### Cross-Agency Network (With Consortium)

```
Consortium: "Prosper Canada Network" (shared schema)
  ConsortiumReportSchema v1: standard 10 metrics + 4 demographic breakdowns

Agency A (tenant):
  Partner: "Prosper Canada"
    type: network
    consortium: → Prosper Canada Network
    programs: [Financial Coaching]

    ReportTemplate: "PC Quarterly Report"
      consortium_schema_version: 1
      metrics: 10 standard + 2 agency-specific
      schedule: quarterly

Agency B (tenant):
  Partner: "Prosper Canada"
    type: network
    consortium: → Prosper Canada Network

    ReportTemplate: "PC Quarterly Report"
      consortium_schema_version: 1
      metrics: 10 standard (same as Agency A's standard set)
      schedule: quarterly
```

When the consortium updates to schema v2, agencies are notified: "Your template uses schema v1; v2 is available."

### Board Report (No Grant, All Programs)

```
Partner: "Board of Directors"
  type: board
  programs: [] (empty = all programs)
  grant_number: (blank)

  ReportTemplate: "Board Quarterly Overview"
    period: quarterly
    sections:
      - Service stats across all programs
      - Key outcomes summary
      - Narrative highlights
    schedule: fixed dates (one week before board meetings)
```

## Migration Path from Existing Models

1. Create `Partner` model (no existing data affected)
2. Add `partner` FK to `ReportTemplate` as **nullable**
3. Data migration: for each existing ReportTemplate, auto-create a Partner (`name = template.name`, `type = "funder"`) and link
4. Add new fields to ReportTemplate (sections, metrics, schedule) — all nullable or with defaults
5. Make `partner` FK non-nullable
6. Existing `DemographicBreakdown` FK to ReportTemplate is unchanged — continues working

## Implementation Layers

| Layer | What | Independently Useful? |
|-------|------|----------------------|
| **1** | Partner + enhanced ReportTemplate + ReportSection + ReportMetric | Yes — complete report definitions with partner context |
| **2** | ReportSchedule + three-phase alerts | Yes — reminders without full report generation |
| **3** | Survey.partner FK + MetricDefinition.superseded_by | Yes — connects surveys to partner context |
| **4** | ConsortiumReportSchema + version tracking | Only needed for multi-agency deployments |
| **5** | AI-assisted configuration skill | Accelerates setup; not required for manual configuration |

## AI-Assisted Configuration Skill

### How It Works
1. Admin uploads/pastes a funder agreement, MOU, assessment tool, or board policy
2. Claude analyzes and outputs structured JSON matching the data model
3. JSON includes `mapping_confidence` per metric (high/low) and explicit warnings
4. Admin reviews draft in a "Partner Setup" UI, confirms mappings, approves
5. Partner + ReportTemplate + Schedule created from approved draft

### What It Generates By Document Type
- **Funder agreement** → Partner (type=funder) + ReportTemplate with metrics, demographics, schedule
- **Collaboration MOU** → Partner (type=network) + ReportTemplate, optionally linked to Consortium
- **Assessment tool** → Survey definition with questions, scoring rules, metric mappings
- **Board reporting policy** → Partner (type=board) + ReportTemplate with schedule

### Phase 1: Claude Code Skill (No API Key Needed)
- Runs during onboarding or setup sessions
- KoNote team or admin works with Claude to configure

### Phase 2: In-App Feature (Future)
- "Import from document" button in admin UI
- Requires Claude API key management and cost tracking

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Template sprawl | "Duplicate and modify" flow; Partner grouping in UI |
| Metric mapping drift | AI skill re-validates periodically; `superseded_by` tracks changes |
| Privacy in AI pipeline | AI processes template definitions only, never participant data |
| Bilingual complexity | `title_fr` and `display_label_fr` on all display fields |
| Consortium schema divergence | `consortium_schema_version` tracking with update notifications |
| Staff turnover | Original documents stored with Partner; template = institutional memory |

## Connection to Multi-Tenancy Plan

This architecture is designed to integrate with the [multi-tenancy implementation plan](prosper-canada/multi-tenancy-implementation-plan.md):

- **Partner** lives in tenant schema → each agency manages their own partners
- **Partner.consortium** FK points to shared-schema Consortium → enables cross-agency linkage
- **ConsortiumReportSchema** lives in shared schema → networks define standards centrally
- **ConsortiumMembership, ProgramSharing, PublishedReport** (from multi-tenancy plan) remain unchanged
- **Cross-agency API** (SCALE-API1) serves PublishedReport data that was generated from Partner-linked ReportTemplates

The two architectures complement each other: this one handles "what to report and when," the multi-tenancy plan handles "how to share it across agencies."
