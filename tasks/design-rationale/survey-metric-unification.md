# Design Rationale: Survey–Metric Unification

**Status:** Decided (2026-03-07)
**Decided by:** GK (subject matter expert, evaluation methodology)
**Reviewed by:** Expert panel (2026-03-07) — Evaluation Systems Architect, Django Data Modeller, Nonprofit Capacity Builder, Standards Compliance Specialist

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

## Scoring Pipeline

`SurveySection.scoring_method` and `MetricDefinition.scoring_bands` are **complementary, not conflicting.** They are two steps in the same pipeline:

1. **Step 1 — Aggregate items:** `scoring_method` (sum/average) computes the subscale score from individual item scores within the section
2. **Step 2 — Interpret the total:** `scoring_bands` maps the aggregated score to severity categories (e.g., PHQ-9 total of 15 → "Moderately severe depression")

This is exactly how validated instruments work. Do not attempt to "resolve" these as competing systems — they are sequential stages.

## CIDS Compliance Interaction

This decision directly supports CIDS compliance and metadata tagging.

### CIDS indicators map to sections, not questions

CIDS indicators (`cids:indicatorForOutcome`) are defined at the outcome level — they map to the *subscale score* (PHQ-9 total), not to individual items (PHQ-9 question 3). In this system:

- The **section** (subscale) is what maps to a CIDS indicator
- The section computes the subscale score via `scoring_method`
- When all questions in a section are linked to the same `MetricDefinition` (via `instrument_name`), the section inherits that metric's CIDS properties
- CIDS export should pull: `SurveySection.source` → citation, `MetricDefinition.cids_indicator_uri` → indicator, computed section score → value

Same pattern applies to IRIS+ codes (`iris_metric_code`) — these map to aggregate measures, not individual items.

### What unification enables

- **MetricDefinition already carries CIDS fields** (`cids_indicator_uri`, `iris_metric_code`, `sdg_goals`, `cids_defined_by`, `cids_unit_description`, `cids_has_baseline`, `cids_theme_override`). When a survey question links to a metric, all CIDS metadata flows through without re-tagging.
- **Survey responses linked to CIDS-aligned metrics can be included in JSON-LD exports.** A PHQ-9 administered as a portal survey produces the same CIDS-compliant data as a PHQ-9 score recorded in a progress note.
- **Avoids duplicate CIDS tagging.** Without unification, someone would need to manually tag survey questions with CIDS URIs separately from metrics — two places to maintain, guaranteed to drift.
- **Supports the Common Approach reporting requirement.** Funders using Common Approach / CIDS expect standardised indicator data regardless of how it was collected (staff observation, client self-report, survey). Unification means one indicator definition, multiple collection surfaces.

See also: `tasks/design-rationale/cids-metadata-assignment.md` for the CIDS metadata workflow on MetricDefinition.

## Implementation Path

### Phase 1 — Lightweight (completed 2026-03-07)
1. Add `source` (CharField, optional) to `Survey` — whole-instrument shorthand
2. Add `source` (CharField, optional) to `SurveySection` — per-section/subscale citation
3. Update CSV import to accept `source` column (first non-blank value per section applies to the section)
4. Update CSV template with source examples (including WHO-5 with citation)
5. No bilingual `source_fr` — citations aren't translated

### Phase 2 — MetricDefinition Link (future session)
1. Add optional FK `metric_definition` to `SurveyQuestion` with `on_delete=SET_NULL` — if a metric is deactivated, the survey question survives but loses its link
2. When linked, display inherited metadata (source, scoring, instrument name) from the metric
3. Survey builder UI: "Link to metric" picker — **hidden by default** behind an "Advanced" or collapsed section. Show a subtle indicator (icon/badge) on sections whose `source` matches a known `instrument_name` but aren't yet linked (nudge, not gate)
4. **Post-import linking review** (replaces CSV metric column): after CSV import, check section `source` fields against `MetricDefinition.instrument_name` with fuzzy matching (case-insensitive, hyphen-insensitive). If matches found, present a review screen: "These sections match instruments in your metric library. Link them?" One click per section, confirmed by the evaluation coordinator. No `metric_code` CSV column — keep the CSV workflow simple.
5. **Aggregation bridge** (required — this is what makes unification real): when a survey response is submitted and the section has linked metrics, compute the section score per `scoring_method` and record it as an outcome data point tagged with:
   - The MetricDefinition (via the FK)
   - The collection context: `survey` (vs. `progress_note` or `portal`)
   - The survey response ID (for traceability)
   - This data point appears in outcome charts alongside progress-note entries

### Phase 3 — Unified Measurement Library (future)
1. Survey sections that correspond to full instruments (all items from PHQ-9) auto-link to MetricDefinition
2. "Create survey from instrument" workflow — select a MetricDefinition with `is_standardized_instrument=True`, auto-generate survey sections and questions
3. Cross-context reporting: "Show all PHQ-9 data for this participant" regardless of whether it came from a progress note or a survey

## MetricDefinition Versioning

When a MetricDefinition changes after a survey has collected responses:

- **Do not snapshot metadata on every answer.** This is clinical-trial thinking — overkill for nonprofit program evaluation.
- **Use the existing `rationale_log`** (append-only changelog) to track why changes were made. The current scoring_bands / definition are always the latest version; the rationale_log preserves the audit trail.
- **For fundamental changes** (metric changes meaning, not just band adjustments): deactivate the old MetricDefinition and create a new one. The FK on old survey questions still points to the old (deactivated) definition with its original interpretation. `on_delete=SET_NULL` means deactivation doesn't cascade-delete survey questions.
- **The UI must handle null gracefully.** If a metric is deactivated and the FK goes null, the survey question still works — question text, options, and scoring live on SurveyQuestion. The link is additive, not structural.

## Cross-App Dependency

The FK from `apps.surveys.SurveyQuestion` to `apps.plans.MetricDefinition` couples these two Django apps. Surveys can no longer be tested or used without the plans app installed. This is acceptable — both apps always coexist in KoNote — but should be documented in test setup and app configuration.

## Anti-Patterns

- **Do not duplicate MetricDefinition fields on SurveyQuestion.** If a question is linked to a metric, read the metadata from the metric. If it's unlinked, it has no instrument metadata — that's fine.
- **Do not require linking.** Many survey questions (demographics, feedback, consent) are not metrics. The FK must be nullable.
- **Do not auto-create MetricDefinitions from survey questions.** Metrics are curated library items. Surveys may have throwaway questions. The link is always intentional.
- **Do not add `source_fr`.** Citations are language-neutral. One field is enough.
- **Do not add a metric linking column to the CSV import.** Use the post-import review screen instead. Keep the CSV workflow simple for program managers.
- **Do not require metric linking to use surveys.** The FK is additive — surveys work exactly as before without it.
- **Do not map CIDS indicators to individual survey questions.** CIDS indicators map to sections/instruments (subscale scores). The section is the CIDS unit, not the question.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Staff confusion from metric linking UI | Medium | Medium | Hidden by default, post-import review only, evaluation coordinator confirms |
| MetricDefinition changes invalidate old survey interpretations | Low | Medium | Append-only rationale_log, deactivate-and-replace for fundamental changes |
| CIDS export pulls from wrong level (question vs. section) | Medium | High | Enforce section-level CIDS mapping in export code, document in anti-patterns |
| Cross-app coupling breaks test isolation | Low | Low | Document dependency, both apps always coexist in KoNote |
| Fuzzy matching on instrument names produces false positives | Low | Low | Review screen requires human confirmation — false matches are caught |
