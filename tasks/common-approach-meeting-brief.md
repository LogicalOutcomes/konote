# Common Approach Meeting Brief: KoNote Privacy-First Full Tier CIDS

Date: 2026-03-07
Audience: KoNote team preparing for Common Approach meeting
Status: Updated with honest implementation status

## Key Message

KoNote is building toward CIDS Full Tier compliance within a privacy-first architecture. All Full Tier classes are supported through structured evaluation frameworks that describe program models — not individual participants. The standard's Stakeholder class refers to stakeholder *groups* (e.g., "youth aged 16-24"), not individuals, which aligns perfectly with our privacy architecture.

## Honest Implementation Status

### Deployed and working on the production instance
- Program model with CIDS fields (`cids_sector_code`, `population_served_codes`)
- MetricDefinition and PlanTarget with CIDS fields
- CidsCodeList model with ICNPOsector, PopulationServed, SDG, IRIS+ code lists imported
- TaxonomyMapping model (base fields — `taxonomy_system`, `taxonomy_code`, `taxonomy_label`)
- SecureExportLink with approval flow, PII tracking, elevated export delays
- AI module with OpenRouter integration and PII safety controls
- PII scrubbing and k-anonymity suppression (k>=5) in reports
- OrganizationProfile for agency-level CIDS metadata

### Written but not yet deployed (code exists, needs commit + migration)
- Basic Tier JSON-LD export builder (`cids_jsonld.py`, 347 lines)
- SHACL validation against official Common Approach Basic Tier shapes
- Taxonomy review pipeline with AI-suggested and human-approved mappings
- TaxonomyMapping enhancements (mapping_status, confidence_score, provenance fields)
- CIDS enrichment (theme derivation, standards alignment)

### Designed, ready to build (spec complete with agent prompts)
- Evaluation Framework editor — structured planning tool mapping to Full Tier classes
- Full Tier JSON-LD serialiser with 3-layer compliance architecture
- CIDS class coverage dashboard
- Evaluator attestation workflow

## What We Can Demonstrate at the Meeting

1. **Live Basic Tier export** (once Phase 0 deploys) — valid JSON-LD with Organization, Outcome, Indicator, IndicatorReport, Theme, Code classes, validated against SHACL shapes
2. **Quick Full Tier stubs** (once Phase 0.5 deploys) — ImpactModel, Stakeholder, StakeholderOutcome, Output derived from existing program data without new models
3. **Evaluation Framework concept** — the component type → CIDS class mapping, and how it fills the remaining 4 classes (Service, Activity, ImpactRisk, Counterfactual)
4. **Privacy-First architecture diagram** — 3-layer model showing what data is in each layer and why it's safe

## Three-Layer Compliance Architecture

| Layer | What's in it | Privacy impact | Consent needed? |
|-------|-------------|---------------|----------------|
| **1. Program Model** | ImpactModel, Service, Activity, Output, Stakeholder groups, ImpactRisk, Counterfactual | None — describes programs, not people | No |
| **2. Aggregate Measurement** | IndicatorReport with cohort breakdowns, suppressed to k>=5 | Minimal — existing statistical disclosure controls | No |
| **3. Case Trajectories** (optional) | De-identified outcome pathways per cohort | Controlled — k-anonymity (k>=5), dates generalised to quarters, minimum n>=15 | No (de-identified data is not PHI under PHIPA) |

**Why this works:** CIDS Full Tier classes describe the *program model*, not individual participants. `cids:Stakeholder` refers to stakeholder groups. `cids:StakeholderOutcome` describes aggregate outcomes for a group. `cids:ImpactModel` is the theory of change. None of these require individual identifiers.

## CIDS Class Coverage Roadmap

| Phase | Classes added | Cumulative | Coverage |
|-------|-------------|------------|----------|
| Phase 0 (commit existing code) | Organization, Outcome, Indicator, IndicatorReport, Theme, Code, Address | 7/14 | 50% |
| Phase 0.5 (quick stubs from existing data) | ImpactModel, Stakeholder, StakeholderOutcome, Output | 11/14 | 79% |
| Phase 1 (evaluation planning) | Service, Activity, ImpactRisk, Counterfactual | 14/14 | 100% |
| Phase 4 (Full Tier assembly) | All classes in a single Full Tier JSON-LD document | 14/14 | Full Tier |

## How EvaluationComponent Maps to CIDS

| KoNote component | CIDS Full Tier Class |
|---|---|
| Participant group | `cids:Stakeholder` |
| Service | `cids:Service` |
| Activity | `cids:Activity` |
| Output | `cids:Output` |
| Outcome | `cids:StakeholderOutcome` |
| Risk | `cids:ImpactRisk` |
| Counterfactual | `cids:Counterfactual` |
| Input | `cids:Input` |
| Impact dimension | `cids:ImpactDimension` |

## Evaluator Attestation: A Proposed Best Practice

KoNote introduces an **evaluator attestation** workflow:

1. The system generates a structured Full Tier package locally
2. An evaluator (staff, consultant, or evaluation lead) reviews it within the instance
3. The evaluator confirms the impact model, outcome measurement, and risk assessment
4. The attestation is recorded as provenance metadata in the export

**We propose this to Common Approach as a best practice** — a provenance signal that adds trust to impact claims. It's more rigorous than automated export because a qualified human has confirmed the evaluation framework's accuracy.

## Privacy Architecture (Canadian Context)

KoNote serves Canadian nonprofits. Agencies in Ontario are subject to PHIPA (Personal Health Information Protection Act); other provinces have comparable health privacy legislation. Our architecture ensures:

- **Participant data never leaves the instance** — all PII stays encrypted locally (Fernet/AES)
- **Only approved aggregate exports cross the boundary** — non-PII confirmed before any external processing
- **Layer 3 (optional de-identified trajectories)** uses k-anonymity (k>=5), date generalisation (quarters), and minimum cohort size (n>=15) — de-identified data is not PHI under PHIPA, so no consent is needed for aggregate trajectories

This means agencies achieve Full Tier using only program-level and aggregate data. No individual identifiers are required, no consent barriers, and no privacy risks.

## Questions for Common Approach

1. **Evaluator attestation:** Would Common Approach endorse an evaluator attestation pattern as a provenance best practice? We'd like to contribute this to the standard.

2. **Full Tier SHACL shapes:** What is the roadmap for Full Tier SHACL validation shapes? Currently only Basic Tier SHACL is published. We'd like to validate our Full Tier exports against official shapes.

3. **Reference implementations:** Are there other implementations achieving Full Tier that we can learn from or compare against?

4. **Verification pathway:** What does it take to be formally verified at Full Tier? Is there a review process, self-certification, or third-party audit?

## Implementation Timeline

| Phase | Content | Status |
|-------|---------|--------|
| Phase 0 | Commit existing CIDS code, apply migrations, deploy | Code exists, needs commit |
| Phase 0.5 | Quick Full Tier stubs (ImpactModel, Stakeholder, StakeholderOutcome, Output) | Prompt ready |
| Phase 1 | Evaluation planning (EvaluationFramework, EvaluationComponent, editor UI) | Prompt ready |
| Phase 4 | Full Tier JSON-LD assembly, evaluator attestation in export | Prompt ready |

Phases 2-3 (report artifact pipeline, AI enrichment) improve metadata quality but are not compliance blockers — they can follow after Full Tier is achieved.

## What We're Not Doing

- **No individual identifiers in exports** — CIDS Full Tier describes program models and aggregate outcomes, not individual participants
- **No participant data in external AI** — only approved non-PII artifacts are processed externally
- **No mandatory human review** — quality ladder (AI-generated → checks passed → human confirmed) without gatekeeping
- **No single-tier approach** — agencies choose their compliance level based on their evaluation capacity
