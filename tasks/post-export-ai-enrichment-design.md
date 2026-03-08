# Post-Export AI Enrichment for Partner Reports

Date: 2026-03-07
Status: Draft
Context: Prosper Canada dashboarding and cross-agency reporting

## Goal

Add an optional AI-assisted stage after a report has already been approved and stripped of participant data.

This workflow should be paired with an earlier evaluation-planning stage that happens before or during KoNote implementation.

This stage should:

1. validate partner-ready reports against reporting requirements
2. assign or improve high-quality metadata for CIDS and dashboarding
3. support complex Full Tier elements such as program models, services, outputs, risks, and counterfactual descriptions
4. allow centralised processing across many KoNote instances that opt in
5. never send participant-level data to an external API

## Core Rule

External AI services must only receive approved exports that have already been stripped of all participant data.

That means the AI layer works on a report artifact that is already suitable to send to a partner or funder.

It must not read:

1. client records
2. note text tied to an individual
3. per-participant metric histories
4. names, IDs, or record-level demographic rows

## Stage 0: Evaluation Planning Before KoNote Setup

For higher-quality Full Tier metadata, the best time to define the hard parts is before the instance is fully implemented.

That means the workflow should start with an evaluation framework builder.

This stage should help an agency describe:

1. programs and service lines
2. intended participants or cohorts
3. interventions and services delivered
4. expected outputs
5. short-, medium-, and longer-term outcomes
6. logic model or theory-of-change relationships
7. known risks and mitigations
8. counterfactual assumptions or comparison claims
9. partner-specific reporting requirements

### Why this belongs before implementation

If these elements are captured early, KoNote can be configured against a clearer evaluation structure instead of trying to infer everything later from reports.

That improves:

1. metric selection
2. template setup
3. program descriptions
4. report consistency
5. Full Tier metadata quality

### Role of AI in Stage 0

AI can assist by:

1. drafting program intervention descriptions
2. proposing logic-model structures
3. suggesting outputs and outcome chains
4. drafting risk statements and mitigations
5. proposing initial CIDS/IRIS+/SDG mappings

For the hardest work, such as risk framing, impact-model synthesis, or counterfactual drafting, the system can escalate to a frontier API.

### Human confirmation in Stage 0

Human confirmation should be recommended for complex elements, but not required.

That means:

1. agencies can accept AI-generated evaluation structures directly if they choose
2. agencies that confirm the hard parts manually should get a higher quality rating and more trusted downstream metadata
3. the system should track whether an element was AI-only, human-confirmed, or fully manual

This gives a practical quality ladder without making review mandatory.

## Where This Fits in the Existing Flow

KoNote already has a report approval and secure export flow.

The complete workflow becomes:

1. pre-implementation evaluation planning
2. KoNote configuration and program/template setup
3. operational data collection in KoNote
4. report generation and approval
5. post-export non-PII validation and enrichment

The new stage should sit after:

1. report generation
2. report preview
3. agency notes
4. approval
5. creation of a `SecureExportLink` with `contains_pii=False`

Then, optionally:

6. send the approved aggregate report artifact to a validation and enrichment pipeline
7. attach the enriched metadata back to the export record
8. use the enriched output for dashboard rollups, partner packages, and Full Tier export assembly

The evaluation-planning stage should also feed into this later stage by seeding trusted program-model metadata before reports ever reach the enrichment pipeline.

## Proposed Pipeline

### Stage 1: Canonical report artifact

Each instance produces a canonical machine-readable report package.

Suggested contents:

1. export metadata
2. partner name and template name
3. period covered
4. aggregate metrics and demographic summaries
5. agency notes
6. taxonomy lens used
7. CIDS JSON-LD export if available
8. explicit `contains_pii=false`
9. schema version
10. source instance ID / tenant ID

This should be treated as the source object for downstream AI operations.

Where available, the report artifact should also include references to the evaluation-planning records for that program or template.

### Stage 2: Deterministic validation

Before calling any model, run non-AI checks.

Examples:

1. required sections present
2. expected metric set for the partner template
3. date range valid
4. suppression rules applied
5. no participant-level rows or identifiers
6. export marked `contains_pii=False`
7. JSON-LD parses successfully
8. Basic Tier SHACL passes when CIDS export is included

If deterministic validation fails, stop and flag the report.

### Stage 3: AI requirement validation

Once the report is confirmed safe, AI can assess whether it is complete and dashboard-ready.

Examples:

1. does the report clearly identify the program model?
2. are outputs and outcomes distinguishable?
3. does the service description match the reported activities?
4. are important gaps obvious, such as missing risk statements or absent counterfactual language?
5. does the metadata fit the partner schema?

This stage should return structured findings, not just prose.

### Stage 4: Metadata assignment and enrichment

This is the main AI assistance layer.

It can populate or improve:

1. taxonomy mappings across CIDS, IRIS+, SDG, Common Approach, and partner schemas
2. Program, Service, Activity, Input, and Output descriptions
3. ImpactModel summaries
4. Stakeholder and stakeholder-outcome framing from aggregate cohort definitions
5. impact dimensions and explanatory text
6. counterfactual statements
7. impact risks, likelihood, consequence, and mitigation descriptions
8. cross-agency dashboard metadata such as comparable program model tags

### Stage 5: Frontier fallback for complex cases

Use a smaller or default model first for simpler classification.

Escalate automatically to a frontier API only when the task is genuinely complex.

Examples:

1. ambiguous program-model inference
2. synthesising a clean impact model from many aggregate sections
3. drafting counterfactual language from structured context
4. generating risk statements and mitigations that are plausible and specific
5. reconciling many code systems at once

### Stage 6: Output modes

Each instance should be able to choose one of three modes.

1. validation only
2. validation plus draft enrichment
3. validation plus auto-applied enrichment

Human review remains possible in every mode, but is not mandatory.

## Multi-Instance Architecture

For agencies that opt in, the best model is a central managed enrichment service.

The same service can also host reusable evaluation-planning profiles for common funders or sectors.

### Local KoNote instance responsibilities

Each KoNote instance should:

1. generate the approved aggregate report artifact locally
2. prove it is non-PII
3. sign or authenticate the job request
4. submit the artifact to the enrichment service
5. receive back structured validation results and enriched metadata

### Managed enrichment service responsibilities

The central service should:

1. store partner schemas and dashboard profiles
2. store code-list packs and taxonomy prompts
3. run deterministic validation first
4. choose the model tier for each task
5. return structured results in a stable schema
6. retain only the minimum needed audit record
7. maintain reusable evaluation-framework templates for common program models
8. support shared partner schemas such as Prosper Canada templates across many instances

### Why centralise this

Centralisation allows:

1. one set of Prosper Canada reporting rules for all agencies
2. one set of prompts and ontology mappings
3. shared improvements across many instances
4. lower cost than every instance calling frontier APIs independently
5. central benchmarking and quality monitoring across opted-in agencies
6. shared evaluation-framework patterns that improve setup quality across many agencies

## Recommended Data Contract

The central service should accept a report package like this:

1. `report_id`
2. `instance_id`
3. `partner_profile`
4. `report_template`
5. `period`
6. `approved_at`
7. `contains_pii`
8. `aggregate_payload`
9. `cids_payload`
10. `agency_notes`
11. `validation_profile`
12. `requested_operations`

The response should include:

1. deterministic validation results
2. AI validation findings
3. enriched metadata objects
4. confidence values
5. model used per task
6. whether frontier escalation occurred
7. a final readiness status

For Stage 0 planning jobs, the service should also support a planning package containing:

1. organisation type
2. program/service descriptions
3. target populations
4. funder requirements
5. existing logic models or proposal text
6. draft metrics and outcome statements

The output of that planning package should be structured evaluation metadata that KoNote can later reference during export enrichment.

## Model Strategy

Use different model classes for different jobs.

### Low-complexity tasks

Use cheaper models for:

1. direct code-list classification
2. known schema checks
3. section matching
4. simple label normalisation

### High-complexity tasks

Use frontier APIs for:

1. impact-model synthesis
2. counterfactual drafting
3. risk and mitigation generation
4. complex service/output/input framing
5. cross-taxonomy reconciliation

## Safety and governance rules

1. External AI receives only approved non-PII report artifacts.
2. No participant-level data leaves the instance.
3. Every enrichment run records model, timestamp, and task type.
4. Agencies can disable auto-apply and require review if they prefer.
5. Narrative fields should remain editable by humans even when auto-applied.
6. Partner-specific validation rules should be versioned.
7. The enrichment layer must be optional per agency and per export.
8. Complex planning elements should carry provenance showing whether they were AI-generated, human-confirmed, or manual.

## How this supports Prosper Canada

For Prosper Canada and similar umbrella funders, this creates a shared pipeline:

1. agencies produce the same approved aggregate report package
2. a common service validates each package against the same schema
3. AI assigns consistent metadata across agencies
4. central dashboarding uses the enriched metadata instead of raw local wording

Before that reporting stage, a shared planning workflow can help partner agencies define comparable intervention models up front.

That means the Prosper workflow can operate at two points:

1. during onboarding and evaluation planning
2. during post-export validation and enrichment

This is the cleanest way to get comparable cross-agency dashboards without sending raw client data to a central system.

## Suggested implementation order

### Phase 1

1. define the canonical non-PII report artifact
2. add deterministic safety and schema validation
3. store enrichment results against `SecureExportLink`
4. define the evaluation-planning record schema for programs and partner templates

### Phase 2

1. add local AI enrichment for straightforward metadata tasks
2. add structured validation findings to report history
3. add opt-in settings per instance and per partner profile
4. add Stage 0 planning UI for intervention, outputs, outcomes, risks, and logic model capture

### Phase 3

1. add managed central enrichment service for multi-instance use
2. add automatic frontier escalation for hard tasks
3. add dashboard rollup consumption of enriched metadata
4. add shared planning profiles for umbrella funders and common program types

### Phase 4

1. extend the exporter from Basic Tier-style output to real Essential/Full Tier output
2. use the enriched metadata to populate Full Tier classes more consistently
3. add conformance reporting per export tier

## Implementation implications for KoNote

Likely new pieces:

1. a canonical report artifact builder
2. a report validation profile model
3. an enrichment-run model linked to `SecureExportLink`
4. a managed service client for opted-in tenants
5. a structured result schema for AI-enriched metadata
6. a UI screen showing validation findings and enriched metadata status

## Important boundary

This should not become a hidden participant-data pipeline.

The boundary is:

1. KoNote instance does participant-level work locally
2. approved aggregate report artifact crosses the boundary
3. external AI helps with metadata, validation, and dashboarding only

That boundary is what makes this defensible for multi-instance use.