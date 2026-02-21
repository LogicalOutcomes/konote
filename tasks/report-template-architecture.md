# Report Template Architecture — Expert Panel Summary

**Date:** 2026-02-21
**Status:** Expert panel complete, awaiting data model design
**Related TODO IDs:** RPT-SCHEMA1, SCALE-ROLLUP1

## Problem Statement

Agencies have multiple funders per program, each with different reporting requirements (metrics, demographics, time periods, aggregation rules). Currently, report generation requires manual metric selection each time. Report templates should be **complete definitions** that encode all funder requirements once.

Additionally, surveys/assessments tied to funder requirements need versioning and should link to report metrics.

## Expert Panel Participants

- **Nonprofit Program Management Specialist** — funder cycles, multi-funder operations
- **Software Architect** — data modelling, Django patterns
- **Survey & Assessment Design Specialist** — instrument versioning, psychometric integrity
- **AI Application Designer** — LLM-assisted configuration, human-in-the-loop patterns

## Key Decisions

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Report template granularity | Complete definition (metrics + aggregation + demographics + sections + schedule) | Eliminates per-report metric selection; admin configures once |
| Multi-funder overlap | FundingSource M2M with Programs; same metric in multiple templates with different aggregation | Reflects reality; avoids data duplication |
| Survey versioning | Automatic version creation with question lineage tracking; invisible to admin | Protects data integrity without adding cognitive load |
| AI-assisted setup | Claude Code skill (Phase 1); structured JSON output with confidence indicators; admin reviews draft | Low implementation cost; high value; human always in the loop |
| Report generation | Regenerate on demand from template + time period; don't store report blobs | Ensures reports reflect latest data corrections |
| Scheduling | Lead-time alerts, not just due dates; recurrence rules tied to template | Matches nonprofit workflow (drafting starts weeks before deadline) |

## Recommended Data Model

### Core Entities

```
FundingSource (the grant/funder relationship)
  - name, contact, grant_number
  - grant_period_start, grant_period_end
  - programs (M2M -> Program)
  - notes

ReportTemplate (complete report definition)
  - name
  - funding_source (FK -> FundingSource)
  - period_type (quarterly | semi_annual | annual | custom)
  - period_alignment (calendar | fiscal | grant_start)
  - fiscal_year_start_month (1-12)
  - output_format (tabular | narrative | mixed)
  - language (en | fr | both)
  - is_active
  - created_from_document (FileField, nullable)
  - notes

ReportTemplateSection
  - report_template (FK)
  - title
  - section_type (metrics_table | demographic_summary | narrative | chart)
  - instructions (guidance for narrative sections)
  - sort_order

ReportTemplateMetric (through table)
  - report_template (FK)
  - metric (FK -> Metric)
  - aggregation (count | average | percentage | threshold_count)
  - threshold_value (nullable)
  - display_label (override for funder terminology)
  - section (FK -> ReportTemplateSection)
  - sort_order

ReportTemplateDemographic (through table)
  - report_template (FK)
  - demographic_field (FK -> CustomField or enum)
  - grouping (breakdown | filter | both)
  - display_label
  - sort_order

ReportSchedule
  - report_template (FK)
  - due_date (or recurrence rule)
  - lead_time_days
  - assignee (FK -> User)
  - status (upcoming | in_progress | submitted | overdue)
  - submitted_date (nullable)
```

### Survey Entities

```
Survey
  - name
  - funding_source (FK, nullable)
  - survey_type (intake | progress | exit | custom)
  - audience (staff | participant)
  - is_active
  - current_version (FK -> SurveyVersion)

SurveyVersion
  - survey (FK)
  - version_number
  - effective_date
  - change_notes
  - is_locked (once responses exist)
  - created_from_document (nullable)

SurveyQuestion
  - survey_version (FK)
  - question_text (bilingual JSON)
  - question_type (likert | multiple_choice | free_text | numeric | date)
  - required
  - options (JSONField)
  - sort_order
  - scoring_weight (nullable)
  - show_if (conditional logic, nullable)
  - previous_version_question (FK -> self, nullable)
  - section_label

SurveyResponse
  - survey_version (FK)
  - participant (FK)
  - completed_by (FK -> User)
  - completed_date
  - is_complete

SurveyAnswer
  - response (FK)
  - question (FK -> SurveyQuestion)
  - value (TextField)
```

### Bridge Entity

```
MetricSource
  - metric (FK -> Metric)
  - source_type (manual | survey_score | calculated)
  - survey_question (FK, nullable)
  - calculation_rule (nullable)
```

## Implementation Layers

1. **Layer 1:** FundingSource + ReportTemplate + ReportSchedule — enables funder-aware reporting
2. **Layer 2:** Survey + SurveyVersion + SurveyQuestion — enables structured data collection
3. **Layer 3:** MetricSource bridge + AI-assisted configuration skill — connects everything

Each layer is independently useful. Design all three now; build in sequence.

## AI-Assisted Configuration Skill

### Phase 1: Claude Code Skill
- Admin uploads/pastes funder requirements document
- Claude analyzes and outputs structured JSON matching template/survey schema
- Includes `mapping_confidence` for metric matching (high/low)
- Flags gaps: "Document doesn't specify exact metrics — you'll need to define..."
- Admin reviews draft, confirms mappings, approves

### Phase 2: In-App Feature (future)
- "Import from document" button in admin UI
- Calls Claude API directly
- Requires API key management and cost tracking

## Risks

1. **Template sprawl** — provide "duplicate and modify" flow
2. **Metric mapping drift** — AI skill should re-validate periodically
3. **Privacy** — AI processes template definitions only, never participant data
4. **Bilingual complexity** — every label/question needs EN/FR; budget in data model
