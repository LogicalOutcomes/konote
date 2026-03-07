# Design Rationale: Survey–Metric Unification

**Status:** Decided (2026-03-07)
**Decided by:** GK (subject matter expert, evaluation methodology)

## Decision

Survey questions and outcome metrics are the same underlying construct — a measured item that can appear in different contexts (staff progress notes, participant portal forms, anonymous surveys). The system should treat them as one thing, not two parallel systems.

### Core Change

`SurveyQuestion` gets an **optional FK to `MetricDefinition`**. When linked:
- The question inherits metadata from the metric: source/citation, instrument grouping, scoring rules, directionality, CIDS alignment
- Survey responses for linked questions can feed into the same outcome tracking that progress notes use
- One PHQ-9 item definition, surfaced in a staff note, a portal form, or a survey

When unlinked (FK is null):
- The question works exactly as it does today — standalone, custom, no metric relationship
- Used for demographics, open-ended feedback, consent questions, etc.

### Metadata Fields That Already Exist on MetricDefinition

These are the fields survey questions should inherit (not duplicate) when linked:

| Field | Purpose |
|-------|---------|
| `instrument_name` | Groups items from the same instrument (e.g., "PHQ-9") |
| `is_standardized_instrument` | Flags published validated tools |
| `definition` / `definition_fr` | What the item measures and how to score it |
| `scoring_bands` | Published severity cutoffs (JSON) |
| `higher_is_better` | Directionality |
| `min_value` / `max_value` | Valid range |
| `rationale_log` | Append-only changelog with dates, notes, author |
| `cids_indicator_uri` | CIDS indicator alignment |
| `iris_metric_code` | IRIS+ metric code |
| `sdg_goals` | SDG alignment |
| `cids_defined_by` | Organisation that defined the indicator |

### Metadata That Stays on SurveySection

`SurveySection` already has `scoring_method` (none/sum/average) and `max_score`. These are section-level (subscale-level) concerns and stay where they are — they describe how to aggregate the items in that section.

A section-level `source` field (free text, optional) can be added for cases where someone wants to cite the instrument at the section level without linking every question to a MetricDefinition. This is the lightweight path for agencies that don't use the metric library.

## Why Not Question-Level Source Fields?

Rejected: adding `source` directly to `SurveyQuestion`.

- Questions from the same instrument share the same citation — per-question sourcing creates duplication
- The MetricDefinition already has comprehensive metadata; duplicating it on SurveyQuestion creates two sources of truth
- The natural unit of citation in evaluation is the instrument/subscale (section), not the individual item

## Why Not Survey-Level Only?

Rejected as the sole location: adding `source` only to `Survey`.

- Composite surveys mix questions from multiple instruments — one survey-level field can't capture this
- Survey-level source is still useful as a shorthand ("This is the PHQ-9"), so keep it as a convenience field

## Implementation Path

### Phase 1 — Lightweight (current session scope)
1. Add `source` (TextField, optional) to `Survey` — whole-instrument shorthand
2. Add `source` (TextField, optional) to `SurveySection` — per-section/subscale citation
3. Update CSV import to accept `source` column (first non-blank value per section applies to the section)
4. Update CSV template with source examples
5. No bilingual `source_fr` — citations aren't translated

### Phase 2 — MetricDefinition Link (future session)
1. Add optional FK `metric_definition` to `SurveyQuestion`
2. When linked, display inherited metadata (source, scoring, instrument name) from the metric
3. Survey builder UI: "Link to metric" search/picker when adding questions
4. CSV import: optional `metric_code` column that matches `MetricDefinition` by name or ID
5. Response aggregation: linked question responses can appear in outcome tracking charts

### Phase 3 — Unified Measurement Library (future)
1. Survey sections that correspond to full instruments (all items from PHQ-9) auto-link to MetricDefinition
2. "Create survey from instrument" workflow — select a MetricDefinition with `is_standardized_instrument=True`, auto-generate survey sections and questions
3. Cross-context reporting: "Show all PHQ-9 data for this participant" regardless of whether it came from a progress note or a survey

## CIDS Compliance Interaction

This decision directly supports CIDS compliance and metadata tagging:

- **MetricDefinition already carries CIDS fields** (`cids_indicator_uri`, `iris_metric_code`, `sdg_goals`, `cids_defined_by`, `cids_unit_description`, `cids_has_baseline`, `cids_theme_override`). When a survey question links to a metric, all CIDS metadata flows through without re-tagging.
- **Survey responses linked to CIDS-aligned metrics can be included in JSON-LD exports.** A PHQ-9 administered as a portal survey produces the same CIDS-compliant data as a PHQ-9 score recorded in a progress note.
- **Avoids duplicate CIDS tagging.** Without unification, someone would need to manually tag survey questions with CIDS URIs separately from metrics — two places to maintain, guaranteed to drift.
- **Supports the Common Approach reporting requirement.** Funders using Common Approach / CIDS expect standardised indicator data regardless of how it was collected (staff observation, client self-report, survey). Unification means one indicator definition, multiple collection surfaces.

See also: `tasks/design-rationale/cids-metadata-assignment.md` for the CIDS metadata workflow on MetricDefinition.

## Anti-Patterns

- **Do not duplicate MetricDefinition fields on SurveyQuestion.** If a question is linked to a metric, read the metadata from the metric. If it's unlinked, it has no instrument metadata — that's fine.
- **Do not require linking.** Many survey questions (demographics, feedback, consent) are not metrics. The FK must be nullable.
- **Do not auto-create MetricDefinitions from survey questions.** Metrics are curated library items. Surveys may have throwaway questions. The link is always intentional.
- **Do not add `source_fr`.** Citations are language-neutral. One field is enough.

## Scoring Interaction

Different sections already support different scoring rules via `SurveySection.scoring_method`. When a question is linked to a MetricDefinition:
- The metric's `scoring_bands` provide severity interpretation
- The section's `scoring_method` (sum/average) determines how items are aggregated
- The metric's `higher_is_better` determines directionality for display
- These don't conflict — they describe different levels (item vs. subscale)
