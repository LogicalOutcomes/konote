# Common Approach Meeting Brief: KoNote Privacy-First Full Tier CIDS

Date: 2026-03-07
Audience: KoNote team preparing for Common Approach meeting
Status: Draft

## Key Message

KoNote achieves CIDS Full Tier compliance within a privacy-first architecture. All Full Tier classes are supported through structured evaluation frameworks that describe program models — not individual participants. Individual-level data is handled through de-identification and optional consent, with evaluator attestation as a quality signal.

## What We Can Show

### Already working

- **Basic Tier JSON-LD export** — aggregate CIDS export with Organization, Outcome, Indicator, IndicatorReport, Theme, and Code classes
- **SHACL validation** — validates against the official Common Approach Basic Tier SHACL shapes
- **Multi-taxonomy support** — IRIS+, SDG, Common Approach code lists imported and mapped
- **Taxonomy review pipeline** — AI-suggested and human-approved taxonomy mappings with provenance tracking

### Ready to demonstrate (wireframe/concept)

- **Evaluation Framework editor** — structured planning tool that maps directly to Full Tier classes
- **CIDS class coverage dashboard** — shows which Full Tier classes have been populated for a program
- **Evaluator attestation workflow** — qualified reviewer confirms accuracy before export

## Three-Layer Compliance Architecture

| Layer | What's in it | Privacy impact | Consent needed? |
|-------|-------------|---------------|----------------|
| **1. Program Model** | ImpactModel, Service, Activity, Output, Stakeholder groups, ImpactRisk, Counterfactual | None — describes programs, not people | No |
| **2. Aggregate Measurement** | IndicatorReport with cohort breakdowns, suppressed to k>=5 | Minimal — existing statistical disclosure controls | No |
| **3. Case Trajectories** (optional) | Pseudonymised individual outcome pathways | Controlled — de-identified or consent-based | Path A: No. Path B: Yes |

**Why this works:** Most Full Tier classes (ImpactModel, Service, Activity, Output, Stakeholder, StakeholderOutcome, ImpactRisk, Counterfactual) describe the program model, not individual participants. `cids:Stakeholder` refers to stakeholder *groups* (e.g., "youth aged 16-24"), not individuals. KoNote's `EvaluationComponent` model maps each component type to a CIDS Full Tier class.

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

## Privacy Architecture (Ontario/PHIPA Context)

KoNote serves Ontario nonprofits subject to PHIPA (Personal Health Information Protection Act). Our architecture ensures:

- **Participant data never leaves the instance** — all PII stays encrypted locally (Fernet/AES)
- **Only approved aggregate exports cross the boundary** — non-PII confirmed before any external processing
- **Layer 3 (optional individual trajectories)** uses either:
  - De-identification (k-anonymity k>=5, dates generalised to quarters, n>=15 minimum) — not PHI under PHIPA
  - Informed consent per PHIPA s.29(1) — participants opt in to pseudonymised outcome journey

This means agencies can choose their comfort level while still achieving Full Tier.

## Questions for Common Approach

1. **Identifiability requirement:** Does Full Tier require individual identifiers, or are pseudonymised structured records sufficient? Our reading is that `cids:Stakeholder` describes groups and `cids:IndicatorReport` can use cohort-level data.

2. **Evaluator attestation:** Would Common Approach endorse an evaluator attestation pattern as a provenance best practice? We'd like to contribute this to the standard.

3. **Full Tier SHACL:** What is the roadmap for Full Tier SHACL validation shapes? Currently only Basic Tier SHACL is published. We'd like to validate our Full Tier exports.

4. **Reference implementations:** Are there other implementations achieving Full Tier that we can learn from or compare against?

5. **Verification pathway:** What does it take to be formally verified at Full Tier? Is there a review process, self-certification, or third-party audit?

## Implementation Timeline

| Phase | Content | Status |
|-------|---------|--------|
| Phase 1 | Evaluation planning (EvaluationFramework, EvaluationComponent, editor UI) | Spec complete, ready to build |
| Phase 2 | Report artifact pipeline (CanonicalReportArtifact, validation, enrichment runs) | Spec complete |
| Phase 3 | AI enrichment and review (metadata items, taxonomy enrichment, snapshots) | Spec complete |
| Phase 4 | Full Tier JSON-LD assembly, de-identification engine, evaluator attestation in export | Designed |

## What We're Not Doing

- **No participant data in external AI** — only approved non-PII artifacts are processed externally
- **No mandatory human review** — quality ladder (AI-generated → checks passed → human confirmed) without gatekeeping
- **No single-tier approach** — agencies choose their compliance level based on their privacy comfort and evaluation capacity
