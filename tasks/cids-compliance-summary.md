# KoNote CIDS Compliance Summary

**Author:** Gillian Kerr, LogicalOutcomes
**Standard:** Common Impact Data Standard (CIDS) v3.2.0 (July 28, 2025)
**Publisher:** Common Approach (commonapproach.org)
**Date:** 2026-03-06
**Status:** Full specification implemented; SHACL conformance validation deferred

---

## Compliance Level

KoNote targets **FullTier** compliance — the highest tier defined in CIDS 3.2.0. All three tiers (BasicTier, EssentialTier, FullTier) are covered by the implementation.

## What's Implemented

### Data Model (Phase 1 — complete)

| CIDS Class | KoNote Model | Tier |
|---|---|---|
| Organization | OrganizationProfile (singleton) | BasicTier |
| Program | Program (with CIDS sector, population served) | FullTier |
| Outcome | PlanTarget | BasicTier |
| Indicator | MetricDefinition (with IRIS+ codes, SDG goals, baseline, unit) | BasicTier |
| IndicatorReport | MetricValue (aggregated) | BasicTier |
| Theme | CidsCodeList (IRISImpactTheme entries) | BasicTier |
| BeneficialStakeholder | Program cohort (aggregate, not individual) | EssentialTier |
| StakeholderOutcome | Constructed at export from stakeholder + outcome | EssentialTier |
| Activity | ProgressNote (aggregated session counts) | FullTier |
| ImpactReport | Computed from ServiceEpisode + PlanTarget data | EssentialTier |
| ImpactScale / ImpactDepth / ImpactDuration | Computed (all three dimensions) | EssentialTier |
| Code | CidsCodeList (17 official code lists imported) | EssentialTier |
| Target | PlanTarget target values | EssentialTier |

### Code Lists (Phase 2 — complete)

All 17 official code lists from codelist.commonapproach.org are supported via the `import_cids_codelists` management command. The 10 most relevant lists are actively used:

- SDGImpacts, IRISImpactTheme, IrisMetric53, UnitsOfMeasureList, IRISImpactCategory
- ICNPOsector, ESDCSector, PopulationServed, EquityDeservingGroupsESDC, ProvinceTerritory

The CidsCodeList model stores all six SHACL-required fields for Code objects (name, description, codeValue, definedBy, hasSpecification, value).

### Enriched Reports (Phase 2.5 — complete)

- Standards Alignment appendix page in funder outcome reports
- CIDS theme derivation (IRIS+ lookup with admin override)
- SDG goal mapping summary
- Metric-level CIDS coverage statistics

### JSON-LD Export (Phase 3 — complete)

- Management command: `python manage.py export_cids_jsonld`
- Uses official CIDS JSON-LD context: `https://ontology.commonapproach.org/contexts/cidsContext.jsonld`
- All exported data is aggregate — no individual PII
- Correct property names per CIDS 3.2.0 (hasName, hasDescription, hasLegalName)
- i72:Measure objects correctly structured with hasNumericalValue
- Can export all programs or a single program (`--program-id`)

### Auto-Population

CIDS fields are auto-populated when staff create targets and metrics. Staff never see or fill in CIDS fields directly — the system maps their normal work to CIDS behind the scenes using config template pre-mappings and code list lookups.

## What's Not Yet Implemented

| Item | Status | Task ID |
|---|---|---|
| SHACL conformance validation (pyshacl) | Deferred — build when a funder requests conformance certification | CIDS-VALIDATE1 |

## Privacy Safeguards

- CIDS exports contain **organisation, program, and outcome data only** — never individual client records
- BeneficialStakeholder represents cohort groups, not individuals
- PHIPA consent filtering applies to any data feeding CIDS exports
- Consistent with `tasks/design-rationale/no-live-api-individual-data.md`

## Validation History

- **2026-02-24:** Implementation plan validated against CIDS 3.2.0 ontology and SHACL shapes (see `tasks/cids-plan-validation.md`). Five critical corrections applied; six Phase 3 items addressed.
- **2026-02-25:** Reviewed and approved — target FullTier directly, pin to v3.2.0.
- **2026-02-27:** Full implementation merged (PR #131) — metadata fields, code lists, admin UI, enriched reports, JSON-LD export, impact dimensions.
- **1,540-line test suite** covering CIDS models, export, enrichment, and edge cases.

## Notes for Common Approach

### About KoNote

KoNote is a participant outcome management system for Canadian nonprofits. Agencies use it to define desired outcomes with clients, record progress notes with metrics, and visualise progress over time. Each agency runs their own instance.

### Implementation Approach

- We implemented against CIDS v3.2.0 (July 28, 2025), targeting FullTier compliance.
- Our existing data model already tracked programs, outcomes, indicators, and activities, so the CIDS mapping was a natural fit rather than a new layer.
- CIDS metadata is auto-populated when staff create outcomes and metrics — frontline workers don't interact with CIDS fields directly.
- Exports are aggregate only — no individual participant data. This keeps the export compatible with Ontario privacy legislation (PHIPA).
- We validated our implementation against the CIDS 3.2.0 ontology, SHACL shape files, and JSON-LD context, and corrected five issues during that process (namespace URIs, property names, tier classifications).

### Areas Where We'd Welcome Guidance

- **Conformance verification** — we haven't yet run SHACL validation (pyshacl) against our JSON-LD output. We'd appreciate any guidance on how Common Approach recommends implementers verify conformance.
- **Spec updates** — we're pinned to v3.2.0. If there are upcoming changes or a mailing list for implementers, we'd like to stay current.
- **Review of our export** — we'd be happy to share a sample JSON-LD export if Common Approach would like to review it.

### Implementation Feedback We Can Share

During implementation, we noticed a few areas where the spec was ambiguous or where we had to make interpretive decisions. We're happy to share that experience if it's useful for documentation or for other implementers:

- How we mapped `BeneficialStakeholder` to program cohorts rather than individual participants
- Constructing `StakeholderOutcome` junction objects at export time from existing relational data
- Deriving impact dimensions (scale, depth, duration) from service episode and achievement data

## References

- CIDS Ontology: https://ontology.commonapproach.org/cids-en.html
- Code Lists: https://codelist.commonapproach.org
- JSON-LD Context: https://ontology.commonapproach.org/contexts/cidsContext.jsonld
- KoNote implementation plan: `tasks/cids-json-ld-export.md`
- KoNote validation report: `tasks/cids-plan-validation.md`
