# Evaluation Planning and Privacy-First Full Tier CIDS Implementation Spec

Date: 2026-03-07
Revised: 2026-03-07
Status: Draft implementation spec (revised after expert panel review)
Depends on:
- tasks/post-export-ai-enrichment-design.md
- tasks/evaluation-planning-and-enrichment-workflow.md

## Purpose

Turn the two March 7 design notes into a buildable KoNote plan that defines:

1. local data models
2. machine-readable payloads
3. staff-facing screens
4. service boundaries
5. a phased implementation path

This spec achieves CIDS Full Tier compliance within KoNote's privacy-first architecture.

## Key finding: Full Tier is achievable without compromising privacy

Most CIDS Full Tier classes describe the *program model*, not individual participants:

- `cids:ImpactModel` — theory of change (program-level)
- `cids:Service` / `cids:Activity` — what the organisation delivers (program-level)
- `cids:Output` — direct products of services (program-level)
- `cids:Stakeholder` — stakeholder *groups*, not individuals (e.g., "youth aged 16-24")
- `cids:StakeholderOutcome` — intended outcome *for that group* (program-level)
- `cids:ImpactRisk` — risks to achieving impact (program-level)
- `cids:Counterfactual` — what would have happened without intervention (program-level)

None of these require individual identifiers. The `EvaluationFramework` and `EvaluationComponent` models in this spec map directly to these Full Tier classes.

## Three-layer compliance architecture

| Layer | Content | CIDS Classes | Privacy | Source |
|-------|---------|-------------|---------|--------|
| **1. Program Model Metadata** | Impact model, services, activities, outputs, stakeholder groups, risks, counterfactuals | ImpactModel, Service, Activity, Output, Stakeholder, StakeholderOutcome, ImpactRisk, Counterfactual | No privacy concern — describes programs, not people | `EvaluationFramework` + `EvaluationComponent` |
| **2. Aggregate Measurement** | Indicator reports with cohort breakdowns | IndicatorReport, Indicator, Outcome | Existing suppression controls (k>=5) | Existing metric aggregation + `CanonicalReportArtifact` |
| **3. Exemplar Case Trajectories** (optional) | Pseudonymised individual outcome pathways | Extended IndicatorReport | De-identified (Path A) or consented (Path B) | `MetricValue` + `PlanTarget` + de-identification |

### Privacy paths for Layer 3

**Path A: De-identification (no consent needed)**
- Strip direct identifiers; apply k-anonymity (k>=5)
- Generalise dates to quarters, ages to ranges
- Only for programs with n>=15 (matching existing AI threshold)
- Result is NOT PHI under PHIPA — exportable freely

**Path B: Consent-based (richer detail)**
- Participants opt in to pseudonymised outcome journey in evaluation exports
- PHIPA s.29(1) authorises disclosure with consent
- Allows richer trajectory data than Path A

**Path C: Evaluator-in-the-loop (data stays local)**
- Full Tier export generated within instance
- Evaluator with authorised access reviews before export leaves
- Safest path — baseline always available

## Core boundaries

1. participant-level data stays inside each KoNote instance
2. only approved non-PII report artifacts may cross into any external AI service
3. human review is supported but not mandatory
4. planning metadata is non-PII if it describes programs, not individuals

## Scope

This spec covers four connected parts:

1. Stage 0 evaluation planning before or during implementation
2. canonical non-PII report artifact generation after report approval
3. deterministic validation plus optional AI enrichment on approved exports
4. Full Tier CIDS export assembly using evaluation frameworks and enriched metadata

## Design principles

1. Reuse existing seams before adding new ones
2. Store structured metadata, not just AI prose
3. Keep report enrichment anchored to approved exports
4. Keep planning separate from day-to-day staff note entry
5. Make provenance visible on every AI-assisted field
6. Default to local deterministic checks before any model call
7. Map evaluation components explicitly to CIDS Full Tier classes

## Existing seams to reuse

### Reports

- `SecureExportLink` already records approved exports, recipient context, agency notes, file path, and `contains_pii`
- `ReportTemplate` already defines partner-facing reporting expectations
- report approval and secure export flow already exists

### Evaluation and metadata

- `OrganizationProfile` already holds instance-level metadata
- `Program` already holds program descriptors including `description`, `cids_sector_code`, and `population_served_codes`
- `MetricDefinition`, `PlanTargetMetric`, and `MetricValue` already hold outcome and indicator structures
- `TaxonomyMapping` and `CidsCodeList` already support taxonomy mapping review

### Taxonomy pipeline

- `apps/admin_settings/taxonomy_review.py` already provides `generate_subject_suggestions()`, `create_draft_suggestions()`, `_score_candidate()`, and batch suggestion jobs
- Taxonomy-related enrichment must route through this existing pipeline, not build a parallel path

### Architectural decision

Phase 1 should extend `apps/programs` for evaluation-planning setup. Phase 2 should extend `apps/reports` for export-linked validation and enrichment.

## Proposed models

## Part A: Evaluation-planning models

These records define the trusted planning package that maps to CIDS Full Tier classes and later feeds report enrichment.

### `EvaluationFramework`

Recommended app: `apps/programs`

Purpose:

1. one framework per program
2. stores the agency's intervention model and evaluation logic
3. maps to `cids:ImpactModel` in Full Tier exports

Fields:

1. `name`
2. `program` required foreign key to `Program`
3. `report_template` nullable foreign key to `ReportTemplate`
4. `status` with values `draft`, `active`, `archived`
5. `planning_quality_state` with values `ai_generated`, `checks_passed`, `human_confirmed`, `manual`
6. `summary`
7. `output_summary`
8. `outcome_chain_summary`
9. `risk_summary`
10. `counterfactual_summary`
11. `partner_requirements_summary`
12. `source_documents_json` JSONField — schema: `[{"title": str, "source_type": str, "excerpt": str, "contains_pii": bool}]`
13. `evaluator_attestation_by` nullable foreign key to User
14. `evaluator_attestation_at` nullable DateTimeField
15. `evaluator_attestation_scope` JSONField nullable — schema: `["impact_model", "outcome_measurement", "risk_assessment"]`
16. `evaluator_attestation_text` TextField blank
17. `created_by`
18. `updated_by`
19. `created_at`
20. `updated_at`

Design decisions:

1. `program` is required, not nullable — one framework per program. Revisit if multi-program frameworks prove necessary in practice.
2. Does NOT duplicate fields already on `Program` (description, population_served_codes, cids_sector_code). The framework editor displays Program fields read-only and adds only what Program lacks.
3. Includes evaluator attestation fields — proposed as a best practice contribution to Common Approach.

### `EvaluationComponent`

Purpose:

1. structured child records under an evaluation framework
2. each component type maps to a CIDS Full Tier class
3. avoids storing everything as one long narrative blob

CIDS class mapping:

| component_type | CIDS Full Tier Class |
|---|---|
| `participant_group` | `cids:Stakeholder` |
| `service` | `cids:Service` |
| `activity` | `cids:Activity` |
| `output` | `cids:Output` |
| `outcome` | `cids:StakeholderOutcome` |
| `risk` | `cids:ImpactRisk` |
| `mitigation` | (part of `cids:ImpactRisk`) |
| `counterfactual` | `cids:Counterfactual` |
| `assumption` | (metadata on `cids:ImpactModel`) |
| `taxonomy_mapping` | `cids:Code` references |
| `dashboard_tag` | Custom metadata for cross-agency dashboards |
| `input` | `cids:Input` |
| `impact_dimension` | `cids:ImpactDimension` |

Fields:

1. `framework` foreign key to `EvaluationFramework`
2. `component_type` with values from CIDS class mapping above
3. `cids_class` CharField blank — explicit CIDS class URI for export (auto-populated from component_type)
4. `name`
5. `description`
6. `sequence_order`
7. `parent` self foreign key nullable for logic chains
8. `structured_payload` JSONField — per-type schema validated in `clean()`
9. `quality_state`
10. `provenance_source` with values `manual`, `ai_local`, `ai_external`, `imported`
11. `provenance_model` blank allowed
12. `confidence_score` nullable decimal
13. `is_active`
14. `created_at`
15. `updated_at`

Structured payload schemas by component type:

Risk: `{"likelihood": str, "consequence": str, "mitigation": str}`
Output: `{"quantity_description": str, "measurement_method": str}`
Outcome: `{"timeframe": str, "direction": str, "indicator_ids": [int]}`
Participant group: `{"size_estimate": int, "characteristics": str}`
Service/Activity: `{"delivery_mode": str, "frequency": str, "duration": str}`
Counterfactual: `{"type": str, "justification": str}`

Use cases:

1. an output can link to the service that produces it via `parent`
2. a risk can link to one or more outcomes or activities through `parent` or `structured_payload`
3. a dashboard tag can store cross-agency comparability labels

### `EvaluationEvidenceLink`

Purpose:

1. track what source material supported the framework
2. keep provenance for future trust scoring

Fields:

1. `framework`
2. `title`
3. `source_type` with values `proposal`, `logic_model`, `funder_requirement`, `website`, `manual_note`, `report_template`
4. `storage_path` or `external_reference`
5. `excerpt_text`
6. `contains_pii` boolean default `False`
7. `used_for_ai` boolean default `False`
8. `created_at`

Rule:

Only non-PII planning evidence may be sent to an external model. Evidence with `contains_pii=True` is blocked from AI processing.

## Part B: Report artifact and enrichment models

These records attach to approved exports.

### `ReportValidationProfile`

Recommended app: `apps/reports`

Purpose:

1. define rule sets for a partner, template, or service profile
2. version validation requirements independently from the export itself

Fields:

1. `name`
2. `partner` nullable foreign key to `Partner`
3. `report_template` nullable foreign key to `ReportTemplate`
4. `version`
5. `is_active`
6. `required_sections` JSONField — schema: `[{"section_type": str, "required": bool}]`
7. `required_metrics` JSONField — schema: `[{"metric_id": int, "aggregation": str}]`
8. `required_taxonomy_systems` JSONField — schema: `[{"system": str, "min_coverage": float}]`
9. `requires_cids_payload` boolean
10. `requires_full_tier_classes` boolean — requires EvaluationFramework with mapped CIDS components
11. `suppressions_required` boolean
12. `allow_external_ai` boolean
13. `default_enrichment_mode` with values `validation_only`, `draft`, `auto_apply`
14. `external_service_profile` blank allowed
15. `created_at`
16. `updated_at`

### `CanonicalReportArtifact`

Purpose:

1. store the machine-readable non-PII package derived from an approved export
2. provide a stable object for deterministic validation and AI enrichment
3. container for Full Tier export (Layers 1-3)

Fields:

1. `secure_export_link` one-to-one to `SecureExportLink`
2. `schema_version`
3. `instance_identifier`
4. `partner_profile`
5. `report_template_name`
6. `program_ids` JSONField — schema: `[int]`
7. `period_start`
8. `period_end`
9. `artifact_payload` JSONField — schema: `{"sections": [...], "metrics": [...], "demographics": [...], "agency_notes": str}`
10. `cids_payload` JSONField nullable — Full Tier JSON-LD when available
11. `contains_pii` boolean
12. `validation_profile` nullable foreign key to `ReportValidationProfile`
13. `evaluation_framework_ids` JSONField — schema: `[int]`
14. `includes_layer3_trajectories` boolean default False
15. `generated_at`
16. `generated_by`

Rule:

The save path must refuse creation if `contains_pii=True`.

### `EnrichmentRun`

Purpose:

1. store each validation or enrichment attempt
2. keep an audit trail of what was checked, what model was used, and what changed

Fields:

1. `artifact` foreign key to `CanonicalReportArtifact`
2. `run_type` with values `deterministic_validation`, `ai_validation`, `ai_enrichment`, `manual_review`
3. `status` with values `queued`, `running`, `completed`, `failed`, `cancelled`
4. `requested_operations` JSONField — schema: `[str]`
5. `used_external_ai` boolean
6. `frontier_escalation` boolean
7. `model_name` blank allowed
8. `provider_name` blank allowed
9. `input_checksum`
10. `result_summary`
11. `result_payload` JSONField — schema: `{"checks": [...], "findings": [...], "items": [...]}`
12. `started_at`
13. `completed_at`
14. `created_by`
15. `error_message`

### `EnrichedMetadataItem`

Purpose:

1. persist structured outputs at the field or object level for non-taxonomy enrichment
2. allow selective review and selective auto-apply

Important: taxonomy suggestions must NOT go through this model. They route through the existing `TaxonomyMapping` model via `apps/admin_settings/taxonomy_review.py` with `mapping_source='ai_suggested'`.

Fields:

1. `run` foreign key to `EnrichmentRun`
2. `artifact` foreign key to `CanonicalReportArtifact`
3. `framework` nullable foreign key to `EvaluationFramework`
4. `item_type` with values `program_model`, `service`, `activity`, `output`, `outcome`, `risk`, `mitigation`, `counterfactual`, `dashboard_tag`, `narrative`
5. `target_key`
6. `title`
7. `structured_value` JSONField — schema varies by item_type, matching EvaluationComponent schemas
8. `narrative_value` TextField blank allowed
9. `confidence_score` nullable decimal
10. `quality_state`
11. `provenance_source`
12. `provenance_model` blank allowed
13. `review_status` with values `pending`, `accepted`, `rejected`, `auto_applied`
14. `reviewed_by` nullable foreign key to user
15. `reviewed_at` nullable datetime
16. `created_at`

Note: `taxonomy_mapping` is deliberately excluded from `item_type`. Taxonomy suggestions are created as `TaxonomyMapping` records with `mapping_source='ai_suggested'` via the existing `taxonomy_review.py` pipeline.

### `ExportMetadataSnapshot`

Purpose:

1. capture the accepted metadata package attached back to an export
2. avoid mutating old runs when the accepted set changes later

Fields:

1. `secure_export_link` foreign key to `SecureExportLink`
2. `source_run` foreign key to `EnrichmentRun`
3. `snapshot_payload` JSONField — schema: `{"accepted_items": [...], "taxonomy_mappings": [...], "evaluation_framework_id": int}`
4. `snapshot_version`
5. `applied_mode` with values `manual_accept`, `auto_apply`
6. `created_at`
7. `created_by`

## Recommended status and provenance enums

Reuse these enums across planning and enrichment where possible.

### `quality_state`

1. `ai_generated`
2. `checks_passed`
3. `human_confirmed`
4. `manual`

### `provenance_source`

1. `manual`
2. `ai_local`
3. `ai_external`
4. `imported`

### `review_status`

1. `pending`
2. `accepted`
3. `rejected`
4. `auto_applied`

## API and payload contracts

Keep the first implementation internal to KoNote views plus JSON endpoints. A future central service can use the same JSON contracts.

## 1. Planning package payload

Used for Stage 0 AI-assisted evaluation planning.

```json
{
  "schema_version": "1.0",
  "instance_id": "tenant-slug-or-uuid",
  "framework": {
    "name": "Financial resilience coaching",
    "program_id": 12,
    "program_description": "Loaded from Program.description, not duplicated",
    "population_served_codes": "Loaded from Program.population_served_codes",
    "report_template_id": 4,
    "partner_requirements_summary": "Prosper Canada quarterly reporting"
  },
  "source_material": [
    {
      "source_type": "proposal",
      "title": "2026 grant application",
      "excerpt_text": "The program provides one-to-one coaching...",
      "contains_pii": false
    }
  ],
  "requested_operations": [
    "draft_logic_model",
    "suggest_risks",
    "suggest_taxonomy_mappings"
  ]
}
```

## 2. Canonical report artifact payload

Created locally after approval.

```json
{
  "schema_version": "1.0",
  "report_id": "export-482",
  "instance_id": "tenant-slug-or-uuid",
  "partner_profile": "prosper_canada_v1",
  "report_template": "Quarterly partner summary",
  "approved_at": "2026-03-07T18:40:00Z",
  "contains_pii": false,
  "period": {
    "start": "2026-01-01",
    "end": "2026-03-31"
  },
  "program_ids": [12, 15],
  "aggregate_payload": {
    "sections": [],
    "metrics": [],
    "demographics": [],
    "agency_notes": ""
  },
  "cids_payload": {},
  "validation_profile": "prosper_quarterly_v1",
  "evaluation_framework_ids": [8],
  "requested_operations": [
    "deterministic_validation",
    "ai_validation",
    "ai_enrichment"
  ]
}
```

## 3. Deterministic validation response

```json
{
  "status": "completed",
  "ready_for_ai": true,
  "checks": [
    {
      "code": "contains_pii_false",
      "status": "pass",
      "severity": "error",
      "message": "Artifact confirmed as non-PII."
    },
    {
      "code": "full_tier_classes_present",
      "status": "pass",
      "severity": "warning",
      "message": "EvaluationFramework covers required CIDS Full Tier classes."
    },
    {
      "code": "basic_tier_shacl",
      "status": "pass",
      "severity": "warning",
      "message": "Basic Tier SHACL validation passed."
    }
  ]
}
```

## 4. AI enrichment response

```json
{
  "status": "completed",
  "frontier_escalation": true,
  "items": [
    {
      "item_type": "risk",
      "target_key": "framework:8:risk:financial-instability",
      "title": "Income volatility can interrupt coaching attendance",
      "structured_value": {
        "likelihood": "medium",
        "consequence": "medium",
        "mitigation": "Offer flexible session timing and remote follow-up"
      },
      "confidence_score": 0.84,
      "quality_state": "ai_generated",
      "provenance_source": "ai_external",
      "provenance_model": "frontier-model-name"
    }
  ],
  "taxonomy_suggestions": [
    {
      "note": "Routed through taxonomy_review.py, stored as TaxonomyMapping"
    }
  ],
  "findings": [
    {
      "code": "missing_counterfactual",
      "severity": "warning",
      "message": "No counterfactual statement was found in the planning package."
    }
  ]
}
```

## Endpoints and server actions

Keep these as Django views and forms first. Introduce DRF only if the service surface becomes large.

## Evaluation-planning screens

### `GET /programs/evaluation-frameworks/`

Purpose:

1. list frameworks by program
2. show quality state, CIDS class coverage, and last update

### `GET|POST /programs/evaluation-frameworks/new/`

Purpose:

1. create a framework manually
2. optionally start from a planning assistant
3. "draft from existing data" option assembles a starting framework from Program descriptions, MetricDefinitions, and TaxonomyMappings already in the system

Form:

1. `EvaluationFrameworkForm`
2. `EvaluationEvidenceUploadForm`

### `GET|POST /programs/evaluation-frameworks/<id>/edit/`

Purpose:

1. edit framework summaries (Program fields displayed read-only at top)
2. manage child components with CIDS class badges
3. per-section AI drafting actions

Formsets:

1. `EvaluationComponentFormSet`
2. separate tabs for services/activities, outputs/outcomes, risks/mitigations, assumptions/counterfactuals, taxonomy/dashboard tags

### `POST /programs/evaluation-frameworks/<id>/draft-with-ai/`

Purpose:

1. run AI planning assistance on non-PII planning material
2. create or update `EvaluationComponent` rows
3. route taxonomy suggestions through `taxonomy_review.py`

Response:

1. HTMX partial with draft findings and suggested components

### `POST /programs/evaluation-frameworks/<id>/attest/`

Purpose:

1. evaluator confirms accuracy of impact model and measurement methodology
2. records attestation on the framework

## Report enrichment screens

### `GET /reports/exports/<id>/metadata/`

Purpose:

1. show the export's artifact status
2. show CIDS class coverage checklist (Layer 1/2/3 status)
3. show deterministic validation status
4. show latest enrichment run and accepted metadata snapshot
5. show evaluator attestation panel

### `POST /reports/exports/<id>/metadata/build-artifact/`

Purpose:

1. create `CanonicalReportArtifact` from an approved export
2. block if `contains_pii=True`

### `POST /reports/exports/<id>/metadata/validate/`

Purpose:

1. run deterministic validation only
2. persist an `EnrichmentRun` with `run_type=deterministic_validation`
3. check Full Tier class coverage from linked EvaluationFramework

### `POST /reports/exports/<id>/metadata/enrich/`

Purpose:

1. run validation plus optional AI enrichment according to profile and user choice
2. return findings and metadata items
3. route taxonomy suggestions through `taxonomy_review.generate_subject_suggestions()`

Form:

1. `EnrichmentRequestForm`
2. fields: operation mode, allow external AI, auto-apply, use frontier fallback

### `POST /reports/exports/<id>/metadata/items/<item_id>/review/`

Purpose:

1. accept or reject one metadata item
2. support optional human review without making it mandatory

### `POST /reports/exports/<id>/metadata/apply/`

Purpose:

1. create `ExportMetadataSnapshot`
2. mark accepted items as applied to the export package

### `GET /reports/validation-profiles/`

Purpose:

1. admin screen for partner-specific rule sets

## Screen inventory

Build these screens in this order.

### Screen 1: Evaluation frameworks list

Audience:

1. admin
2. program manager

Columns:

1. framework name
2. linked program
3. quality state
4. CIDS class coverage (e.g., "8/13 classes mapped")
5. evaluator attestation status
6. last updated
7. actions

Actions:

1. edit
2. draft with AI
3. archive

### Screen 2: Evaluation framework editor

Sections:

1. program overview (read-only from Program: description, population_served_codes, cids_sector_code)
2. framework summary and partner requirements
3. participant groups (maps to cids:Stakeholder)
4. services and activities (maps to cids:Service, cids:Activity)
5. outputs and outcomes (maps to cids:Output, cids:StakeholderOutcome)
6. risks and mitigations (maps to cids:ImpactRisk)
7. assumptions and counterfactuals (maps to cids:Counterfactual)
8. taxonomy and dashboard tags
9. provenance and quality summary
10. evaluator attestation panel

Behaviour:

1. plain-language labels with CIDS class badges on each section
2. inline explanation of quality states
3. AI drafting actions on each section, not one giant black-box button
4. Program fields shown read-only — edit via Program settings

### Screen 3: Export metadata status page

Anchor:

1. linked from approved export history

Sections:

1. artifact readiness
2. CIDS class coverage checklist
3. deterministic checks
4. AI findings
5. enriched metadata items (non-taxonomy)
6. taxonomy mapping status (links to existing taxonomy review UI)
7. evaluator attestation status
8. accepted snapshot history

Actions:

1. build artifact
2. run validation
3. run enrichment
4. apply accepted metadata
5. generate Full Tier JSON-LD export

### Screen 4: Validation profile admin screen

Audience:

1. admin only

Sections:

1. partner/template selector
2. required sections
3. metric requirements
4. taxonomy requirements
5. Full Tier class requirements
6. AI policy
7. external service policy

### Screen 5: Multi-instance service status screen

Phase 4 only.

Purpose:

1. show remote job status
2. show what left the instance
3. show provider, model, and timestamps

## Permissions

### Evaluation planning

1. admin can create, edit, activate, and archive frameworks
2. program managers can edit frameworks for their programs
3. evaluators (admin or program manager) can submit attestations
4. regular staff can view only if explicitly allowed later

### Enrichment and export metadata

1. only users who can approve partner-ready exports can trigger artifact build or enrichment
2. if external AI is disabled by profile or instance settings, the UI must hide that option
3. downloads and sharing rules remain governed by existing secure export permissions

## Forms

Add dedicated forms instead of raw POST handling.

### `EvaluationFrameworkForm`

Core fields:

1. name
2. program (required)
3. report_template (optional)
4. summary fields (outcome_chain, risk, counterfactual, output, partner_requirements)
5. planning quality state

### `EvaluationComponentForm`

Core fields:

1. component type (with CIDS class auto-populated)
2. name
3. description
4. parent
5. structured payload (validated per component_type schema)
6. quality state

### `EvaluatorAttestationForm`

Core fields:

1. attestation scope (checkboxes: impact_model, outcome_measurement, risk_assessment)
2. attestation text

### `EnrichmentRequestForm`

Core fields:

1. requested operations
2. allow external AI
3. use frontier fallback
4. auto-apply non-narrative items

Validation rules:

1. forbid external AI if artifact `contains_pii=True`
2. forbid auto-apply when deterministic validation failed at error severity

### `MetadataReviewForm`

Core fields:

1. review status
2. reviewer note optional

## Services

Keep business logic out of views.

### `build_canonical_report_artifact(link)`

Responsibilities:

1. confirm export approval metadata exists
2. confirm `contains_pii=False`
3. gather aggregate payload and related evaluation framework references
4. save `CanonicalReportArtifact`

### `run_deterministic_validation(artifact, profile)`

Responsibilities:

1. required fields present
2. non-PII safety checks
3. section and metric requirements
4. CIDS parsing
5. SHACL validation where configured (reuse `validate_cids_jsonld.py`)
6. Full Tier class coverage check against linked EvaluationFramework

### `run_enrichment(artifact, request_options)`

Responsibilities:

1. choose local or external model path
2. create `EnrichmentRun`
3. persist `EnrichedMetadataItem` records for non-taxonomy items
4. route taxonomy suggestions through `taxonomy_review.generate_subject_suggestions()` and `create_draft_suggestions()` — stored as `TaxonomyMapping` with `mapping_source='ai_suggested'`
5. never auto-apply narrative items

### `apply_metadata_snapshot(link, selected_items)`

Responsibilities:

1. gather accepted items
2. build one immutable snapshot payload
3. attach snapshot to export history

### `build_full_tier_jsonld(artifact, framework)`

Responsibilities:

1. assemble Layer 1: map EvaluationComponents to CIDS Full Tier JSON-LD classes
2. assemble Layer 2: include aggregate IndicatorReport data with suppression
3. optionally assemble Layer 3: pseudonymised case trajectories with de-identification
4. include evaluator attestation as provenance record
5. return complete Full Tier JSON-LD document

## Templates

Recommended template paths:

1. `templates/programs/evaluation_framework_list.html`
2. `templates/programs/evaluation_framework_form.html`
3. `templates/programs/partials/evaluation_component_table.html`
4. `templates/programs/partials/evaluator_attestation.html`
5. `templates/reports/export_metadata_status.html`
6. `templates/reports/partials/validation_results.html`
7. `templates/reports/partials/enriched_metadata_items.html`
8. `templates/reports/partials/cids_class_coverage.html`
9. `templates/reports/validation_profile_list.html`

## Management commands

Useful for implementation and testing.

### `python manage.py build_report_artifact --export-link <id>`

1. builds the canonical artifact for an approved export

### `python manage.py validate_report_artifact --artifact <id>`

1. runs deterministic checks only

### `python manage.py enrich_report_artifact --artifact <id> --mode draft`

1. runs enrichment for local testing without UI clicks

### `python manage.py export_full_tier_jsonld --framework <id> --artifact <id>`

1. generates Full Tier JSON-LD from evaluation framework + artifact data

## Migration strategy

### Phase 1 migrations

1. add `EvaluationFramework`
2. add `EvaluationComponent`
3. add `EvaluationEvidenceLink`

### Phase 2 migrations

1. add `ReportValidationProfile`
2. add `CanonicalReportArtifact`
3. add `EnrichmentRun`

### Phase 3 migrations

1. add `EnrichedMetadataItem`
2. add `ExportMetadataSnapshot`

Reason for this order:

Evaluation planning ships first so agencies define their framework before reporting. The artifact pipeline ships second. Enrichment items and snapshots ship when review workflow is needed.

## Testing plan

### Model tests

1. artifact creation blocked when `contains_pii=True`
2. validation profile defaults behave correctly
3. metadata snapshot is immutable after creation
4. EvaluationComponent validates structured_payload per component_type
5. EvaluationFramework requires program FK

### Service tests

1. deterministic validation fails on missing required sections
2. deterministic validation checks Full Tier class coverage
3. deterministic validation stops AI when safety checks fail
4. enrichment persists provenance and confidence
5. enrichment routes taxonomy suggestions through taxonomy_review.py
6. auto-apply skips narrative items
7. Full Tier JSON-LD serialiser correctly maps component types to CIDS classes

### View tests

1. only permitted users can trigger enrichment
2. review endpoint updates item state correctly
3. export metadata status page renders accepted snapshot and latest findings
4. framework editor shows Program fields read-only
5. evaluator attestation records reviewer and scope

### Suggested test files

1. `tests/test_reports.py`
2. `tests/test_admin.py` if profile admin UI lands there
3. `tests/test_programs.py` for evaluation frameworks

## Phase plan

### Phase 1: Evaluation planning foundation

Build:

1. `EvaluationFramework`, `EvaluationComponent`, `EvaluationEvidenceLink`
2. framework list and editor screens with CIDS class badges
3. "draft from existing data" view
4. evaluator attestation workflow

Outcome:

Agencies can define their evaluation framework with explicit CIDS Full Tier class mapping before reporting.

### Phase 2: Report artifact and validation

Build:

1. `ReportValidationProfile`
2. `CanonicalReportArtifact`
3. `EnrichmentRun`
4. deterministic validation service with Full Tier class coverage checks
5. export metadata status page

Outcome:

Approved exports gain a non-PII metadata workflow with Full Tier readiness checking.

### Phase 3: AI enrichment and review

Build:

1. `EnrichedMetadataItem` (non-taxonomy items)
2. `ExportMetadataSnapshot`
3. AI-assisted planning draft actions (via existing `konote/ai.py`)
4. taxonomy enrichment (via existing `taxonomy_review.py`)
5. item-by-item review controls

Outcome:

Agencies can improve metadata quality with AI assistance before reporting.

### Phase 4: Full Tier export assembly and multi-instance service

Build:

1. `build_full_tier_jsonld()` service — maps EvaluationComponents to CIDS Full Tier JSON-LD classes
2. Layer 3 de-identification engine for optional pseudonymised case trajectories
3. optional consent-based export path (PHIPA s.29(1))
4. evaluator attestation as provenance in Full Tier JSON-LD
5. Full Tier SHACL validation (when Common Approach publishes Full Tier shapes)
6. metadata completeness reporting
7. external service client for multi-instance use
8. shared partner profiles for opted-in agencies

Outcome:

KoNote produces Privacy-First Full Tier CIDS exports with ImpactModel, Service, Activity, Output, Stakeholder, StakeholderOutcome, ImpactRisk, and Counterfactual classes, all within the privacy boundary.

## Simplest first cut

If this needs to be smaller, start with:

1. `EvaluationFramework` with required FK to Program
2. `EvaluationComponent` with CIDS class mapping
3. framework list and editor screens
4. one "draft from existing data" view
5. one management command to generate Full Tier JSON-LD from framework data

That is the minimum useful slice because it creates the CIDS Full Tier metadata foundation and can be demonstrated to Common Approach immediately.
