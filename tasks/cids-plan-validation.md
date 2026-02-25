# CIDS Implementation Plan Validation — CIDS-APPROVE1

**Validated against:** CIDS Ontology v3.2.0 (July 28, 2025)
**Source:** https://ontology.commonapproach.org/cids-en.html
**Plan document:** tasks/cids-json-ld-export.md
**Date:** 2026-02-24
**Status:** Ready for project lead review

---

## Executive Summary

The implementation plan in `tasks/cids-json-ld-export.md` is **architecturally sound** and its phasing is well-designed. However, validation against the actual CIDS 3.2.0 ontology, SHACL shapes, and JSON-LD context files revealed **5 corrections required before building** and **6 items to address before Phase 3 (JSON-LD export)**. None of these require changing the fundamental approach.

**Recommendation: GO with corrections.**

---

## What the Plan Gets Right

These aspects of the plan are confirmed correct against the CIDS 3.2.0 spec:

1. **CharField (not URLField) for CIDS URIs** — Correct. URIs may use `urn:` schemes that Django's URLValidator rejects.
2. **All new fields optional (blank=True)** — Correct. No disruption to existing workflows.
3. **Aggregate-only export (no PII)** — Correct. CIDS exports organisation/program/outcome data, never individual client records.
4. **Phase sequence** (metadata -> code lists -> enriched reports -> JSON-LD -> impact dimensions -> validation) — Good progression, each phase builds on the last.
5. **Config template integration** — Excellent approach. Pre-mapping CIDS codes via deployment templates means zero per-agency burden.
6. **OrganizationProfile as singleton model** — Correct for CIDS BasicTier org metadata.
7. **Management command for code list import** — Correct approach, 17 code lists confirmed at codelist.commonapproach.org (all updated Dec 1, 2025).
8. **SHACL validation before export** — Confirmed. CIDS publishes tiered SHACL files: `cids.basictier.shacl.ttl`, `cids.essentialtier.shacl.ttl`, `cids.fulltier.shacl.ttl`.
9. **JSONField for multi-value fields** (sdg_goals, population_served_codes, sector_codes) — Correct, follows existing KoNote patterns.
10. **No changes to ProgressNote or MetricValue models** — Correct. These are data sources, not metadata carriers.
11. **PHIPA consent filtering applies to CIDS export** — Correct per the phipa-consent-enforcement DRR.

---

## Corrections Required Before Implementation

### C1. Namespace URIs Are Wrong in JSON-LD Example (Critical)

**Plan line 209:** `"org": "http://www.w3.org/ns/org#"`
**Actual CIDS context:** `"org": "http://ontology.eil.utoronto.ca/tove/organization#"`

**Plan line 211:** `"sch": "https://schema.org/"`
**Actual CIDS context:** `"sch": "http://schema.org/"` (HTTP, not HTTPS)

**Fix:** The JSON-LD example in the plan should use the official context URL instead of inline namespaces:
```json
"@context": "https://ontology.commonapproach.org/contexts/cidsContext.jsonld"
```
This avoids all namespace errors and ensures forward compatibility when Common Approach updates the ontology.

### C2. Version Reference Is Outdated

**Plan says:** "CIDS v2.0" (line 183, Standards Alignment appendix example)
**Current version:** 3.2.0 (released July 28, 2025). No evidence of a 3.2.1 patch.

**Fix:** Update version references throughout the plan. The Standards Alignment appendix should read "Common Impact Data Standard (CIDS) v3.2".

### C3. Property Name `i72:unit_of_measure` Is Wrong for Indicator

**Plan (line 127):** `unit_of_measure_code` mapped to CIDS property `i72:unit_of_measure`
**CIDS SHACL:** The Indicator class uses `cids:unitDescription` (xsd:string, exactly 1 at BasicTier) for the human-readable unit label.

`i72:unit_of_measure` is used on `IndicatorReport` and `HowMuchImpact` — it's a measurement-level property, not an indicator-level property.

**Fix:** Rename the planned field or update the CIDS property mapping:
- Database field: `cids_unit_description` (CharField) mapped to `cids:unitDescription`
- Or keep `unit_of_measure_code` but document it maps to `cids:unitDescription` in export

### C4. Entity Names Use `org:hasName`, Not `sch:name`

**Plan JSON-LD example (line 238):** `"sch:name": "Housing First Initiative"`
**CIDS SHACL:** All non-Organization entities use `org:hasName` for their name property. Only `Organization` uses `org:hasLegalName`.

**In the JSON-LD context**, `hasName` maps to `cids:hasName` (which is equivalent to `org:hasName` through owl reasoning). So the correct JSON-LD key is `"hasName"`, not `"sch:name"`.

Similarly, `"sch:description"` should be `"hasDescription"` (maps to `cids:hasDescription`).

**Fix:** Update JSON-LD example to use context-defined terms: `hasName`, `hasDescription`, `hasLegalName`.

### C5. Program Is FullTier, Not EssentialTier

**Plan (line 85):** Lists EssentialTier as covering "Programs, outcomes, indicators, stakeholders, impact dimensions"
**CIDS spec:** Program is a **FullTier** class. It does not appear at BasicTier or EssentialTier.

**Tier definitions (from CIDS 3.2.0):**
- **BasicTier:** Organization, Outcome, Indicator, IndicatorReport, Theme (5 classes)
- **EssentialTier:** + Stakeholder, StakeholderOutcome, ImpactReport, Target, Code, Characteristic, CharacteristicReport, StakeholderReport, HowMuchImpact (ImpactScale, ImpactDepth)
- **FullTier:** + Program, ImpactModel, ImpactPathway, OutcomeChain, Activity, Service, Input, Output, ImpactDuration, Counterfactual, ImpactRisk (9 subtypes)

**Impact:** This doesn't change the implementation (KoNote naturally includes programs), but the tier targeting description in the plan should be corrected. BasicTier exports are Organization-centric — outcomes link directly to the organisation, not through programs.

**Fix:** Update the tier table (plan lines 85-92) with correct class assignments.

---

## Items to Address Before Phase 3 (JSON-LD Export)

These don't block Phase 1 (metadata fields) but must be resolved before building the JSON-LD export.

### A1. Code Objects Are Complex Structures

**Plan assumes:** Simple CharField values stored in database (correct for storage)
**CIDS SHACL Essential Tier Code shape requires 6 fields:**

| Required Field | Type | Example |
|---|---|---|
| `org:hasName` | xsd:string | "Client Housing Situation Improved" |
| `cids:hasDescription` | xsd:string | "IRIS+ indicator for housing stability" |
| `sch:codeValue` | xsd:string | "PI2061" |
| `cids:definedBy` | cids:Organization | Reference to GIIN (for IRIS+) or UN (for SDGs) |
| `cids:hasSpecification` | xsd:anyURI | URI of the code list specification |
| `i72:value` | i72:Measure | Measurement value |

**Implication:** The planned CidsCodeList model (Phase 2) must store all these fields, not just `code`, `label`, `description`. The export layer must construct full Code objects from CidsCodeList rows.

**Recommended CidsCodeList fields:**
```
list_name, code, label, label_fr, description, source_url, version_date  (already planned)
+ specification_uri  (for cids:hasSpecification)
+ defined_by_name    (for cids:definedBy — org name like "GIIN", "United Nations")
+ defined_by_uri     (for the @id of the defining organisation)
```

### A2. Essential Tier Indicator Requires `cids:hasBaseline` and `cids:definedBy`

**SHACL EssentialTier adds to Indicator:**
- `cids:hasBaseline` (class: i72:Measure, exactly 1) — Required at EssentialTier
- `cids:definedBy` (class: cids:Organization, exactly 1) — Required at EssentialTier

**For baselines:** The plan correctly notes baselines are computed from existing data (earliest recorded values per client). No new model field needed — computed at export time.

**For `definedBy`:** This references the organisation that defined the indicator standard. For IRIS+ metrics, this would be GIIN. For agency-defined indicators, this would be the agency itself.

**Recommended:** Add an optional `cids_defined_by` field to MetricDefinition (CharField, stores the URI of the defining organisation), or derive it at export time from `iris_metric_code` presence (if IRIS+ code set -> definedBy = GIIN).

### A3. StakeholderOutcome Is Required at EssentialTier

**CIDS has a class the plan doesn't model:** `cids:StakeholderOutcome` — the junction between Stakeholder (who) and Outcome (what).

Required properties: `forStakeholder`, `forOutcome`, `isUnderserved`, `hasImportance`, `hasImpactReport`.

**Implication:** For EssentialTier export, KoNote needs to construct StakeholderOutcome objects that link participant groups (derived from program enrollment demographics) to outcomes (PlanTarget goals).

**Recommendation:** No new database model needed. StakeholderOutcome can be constructed at export time from existing data:
- Stakeholder = program's participant cohort description
- Outcome = PlanTarget outcome
- isUnderserved = derived from demographic data or manually set

Document this construction logic before Phase 3.

### A4. BeneficialStakeholder Is a Group, Not Individual

**Plan (line 77):** `cids:BeneficialStakeholder` maps to `ClientFile`
**CIDS spec:** BeneficialStakeholder represents a **cohort/group** (e.g., "youth aged 16-24 experiencing homelessness"), not an individual person. Individual data flows through `StakeholderReport` with aggregate `CharacteristicReport` counts.

**Fix:** Update the concept mapping table. `ClientFile` does NOT map to BeneficialStakeholder. Instead:
- BeneficialStakeholder = program's target population description (derived from program metadata + enrollment demographics)
- ClientFile data contributes to aggregate counts in StakeholderReport/CharacteristicReport

### A5. Measurement Values Are Nested Objects in JSON-LD

**Plan JSON-LD example (lines 267-270):**
```json
"cids:hasBaseline": {
    "i72:numerical_value": 3.2,
    "i72:unit_of_measure": "score"
}
```

**CIDS SHACL:** `i72:value` requires an `i72:Measure` object with `i72:hasNumericalValue`. The correct structure is:
```json
"i72:value": {
    "@type": "i72:Measure",
    "i72:hasNumericalValue": "3.2"
}
```

Note: `i72:hasNumericalValue` takes xsd:string (not a number literal), and the Measure object uses `@type`.

**Fix:** Update JSON-LD example. This is an export-layer concern, not a model concern.

### A6. ImpactDuration Is FullTier, Not EssentialTier

**Plan groups ImpactScale + ImpactDepth + ImpactDuration together in Phase 4.**
**CIDS spec:** ImpactScale and ImpactDepth are EssentialTier. ImpactDuration is **FullTier**.

**Implication:** For EssentialTier-only exports, ImpactDuration should be omitted. The ImpactReport SHACL at EssentialTier requires `hasImpactScale` and `hasImpactDepth` (both exactly 1) but ImpactDuration is only required at FullTier.

**Fix:** Phase 4 implementation should flag ImpactDuration as FullTier-only.

---

## Confirmed CIDS Tier Requirements (from SHACL Shapes)

### BasicTier SHACL — Required Fields

| Class | Required Properties |
|---|---|
| **Organization** | `org:hasLegalName` (string, exactly 1) |
| **Outcome** | `org:hasName`, `cids:hasDescription`, `cids:forOrganization` (all exactly 1) |
| **Indicator** | `org:hasName`, `cids:hasDescription`, `cids:unitDescription`, `cids:forOrganization` (all exactly 1) |
| **IndicatorReport** | `org:hasName`, `i72:value` (Measure), `prov:startedAtTime`, `prov:endedAtTime`, `cids:forIndicator`, `cids:forOrganization` (all exactly 1) |
| **Theme** | `org:hasName`, `cids:hasDescription` (both exactly 1) |
| **Address** | `cids:streetAddress`, `cids:postalCode`, `cids:addressRegion`, `cids:addressLocality`, `cids:addressCountry` (all exactly 1) |

### EssentialTier SHACL — Adds These Requirements

| Class | Required Properties (beyond BasicTier) |
|---|---|
| **Indicator** | + `cids:hasBaseline` (Measure, exactly 1), `cids:definedBy` (Organization, exactly 1) |
| **IndicatorReport** | + `cids:forTarget` (Target, exactly 1) |
| **ImpactReport** | `org:hasName`, `prov:startedAtTime`, `prov:endedAtTime`, `cids:hasImpactScale`, `cids:hasImpactDepth`, `cids:hasComment`, `cids:forOutcome`, `cids:forOrganization` (all exactly 1) |
| **Stakeholder** | `org:hasName`, `cids:hasDescription`, `cids:hasCatchmentArea` (enum: local/global/provincial/national/multinational), `cids:forOrganization` |
| **StakeholderOutcome** | `org:hasName`, `cids:hasDescription`, `cids:forStakeholder`, `cids:forOutcome`, `cids:isUnderserved` |
| **Target** | `org:hasName`, `i72:value` (Measure), `prov:startedAtTime`, `prov:endedAtTime`, `cids:hasComment`, `sch:dateCreated` |
| **Code** | `org:hasName`, `cids:hasDescription`, `sch:codeValue`, `cids:definedBy`, `cids:hasSpecification`, `i72:value` |
| **ImpactScale/Depth** | `i72:value` (Measure), `cids:hasDescription` |

---

## Complete Namespace Map (from cidsContext.jsonld)

| Prefix | URI | Plan Correct? |
|---|---|---|
| `cids` | `https://ontology.commonapproach.org/cids#` | Yes |
| `org` | `http://ontology.eil.utoronto.ca/tove/organization#` | **No** — plan says `http://www.w3.org/ns/org#` |
| `sch` | `http://schema.org/` | **No** — plan says `https://schema.org/` |
| `i72` | `http://ontology.eil.utoronto.ca/ISO21972/iso21972#` | Yes |
| `prov` | `http://www.w3.org/ns/prov#` | Yes |
| `time` | `http://www.w3.org/2006/time#` | Yes |
| `act` | `http://ontology.eil.utoronto.ca/tove/activity#` | Not in plan (needed for Activity at FullTier) |
| `ic` | `http://ontology.eil.utoronto.ca/tove/icontact#` | Not in plan (needed for Address) |
| `foaf` | `http://xmlns.com/foaf/0.1/` | Not in plan (needed for Person at FullTier) |
| `dcat` | `http://www.w3.org/ns/dcat#` | Not in plan |
| `dqv` | `http://www.w3.org/ns/dqv#` | Not in plan |

**Recommendation:** Use the official context URL `https://ontology.commonapproach.org/contexts/cidsContext.jsonld` to avoid all namespace issues.

---

## Confirmed Code Lists (17 at codelist.commonapproach.org)

| # | Code List | Relevance to KoNote | Used By |
|---|---|---|---|
| 1 | **SDGImpacts** | High — SDG goal codes for outcomes | MetricDefinition.sdg_goals, Outcome themes |
| 2 | **IRISImpactTheme** | High — theme codes | MetricDefinition.cids_theme |
| 3 | **IrisMetric53** | High — 53 core IRIS+ metric codes | MetricDefinition.iris_metric_code |
| 4 | **UnitsOfMeasureList** | High — standard units | MetricDefinition.unit_of_measure_code |
| 5 | **IRISImpactCategory** | High — impact categories | Theme classification |
| 6 | **ICNPOsector** | Medium — org sector codes | OrganizationProfile.sector_codes |
| 7 | **ESDCSector** | Medium — Canadian sector codes | Program.cids_sector_code |
| 8 | **PopulationServed** | Medium — demographics | Program.population_served_codes |
| 9 | **EquityDeservingGroupsESDC** | Medium — EDG codes | Stakeholder characteristics |
| 10 | **ProvinceTerritory** | Medium — CA provinces | OrganizationProfile.province |
| 11 | **OrgTypeGOC** | Low — SFF-specific | |
| 12 | **CanadianCorporateRegistries** | Low — SFF-specific | |
| 13 | **LocalityStatsCan** | Low — SFF-specific | |
| 14 | **FundingState** | Low — SFF-specific | |
| 15 | **RallyImpactArea** | Low — investor-specific | |
| 16 | **SELI-GLI** | Low — SFF-specific | |
| 17 | **StatsCanSector** | Low — SFF-specific | |

Phase 2 should import all 17 for completeness, but initially only #1-10 are actively used.

---

## Concept Mapping Corrections

| CIDS Class | KoNote Model | Plan Correct? | Notes |
|---|---|---|---|
| `cids:Organization` | OrganizationProfile (new) | Yes | |
| `cids:Program` | `Program` | Yes | But note: FullTier only |
| `cids:Outcome` | `PlanTarget` | Yes | |
| `cids:Indicator` | `MetricDefinition` | Yes | |
| `cids:IndicatorReport` | `MetricValue` (aggregated) | Yes | |
| `cids:ImpactReport` | Computed from data | Yes | |
| `cids:Theme` | `MetricDefinition.category` + codes | Yes | |
| `cids:Code` | `CidsCodeList` (new) | Yes | But model needs more fields (A1) |
| `cids:BeneficialStakeholder` | ~~`ClientFile`~~ **Program cohort** | **No** | Must be group, not individual (A4) |
| `cids:Activity` | `ProgressNote` (aggregated by type) | Yes | |
| `cids:StakeholderOutcome` | Not modelled | **Missing** | Needs export-time construction (A3) |
| `cids:Target` | `PlanTarget` target values | Partially | cids:Target is separate from cids:Outcome |
| `cids:Input` | Not modelled | Correct (out of scope) | |
| `cids:Output` | Session counts, service stats | Yes | |

---

## Open Questions for Project Lead

1. **Target tier:** Plan says EssentialTier. Given that Program is FullTier, should KoNote target BasicTier first (fastest to validate), then FullTier (which naturally includes programs)? Or skip straight to FullTier since KoNote already has all the data?

2. **Partner consumption pathway:** The plan notes a funder expressed interest. Do they want JSON-LD, or would CIDS-tagged CSV/PDF (Phase 2.5) satisfy their requirements? This determines urgency of Phase 3.

3. **Common Approach engagement:** The expert panel recommended engaging Common Approach as a pilot implementer. Should this happen before or after Phase 1 fields are in place? Zero downside to early engagement — they need reference implementations.

4. **Config template pre-mapping:** Should the existing partner config template include pre-mapped CIDS codes for standard metrics? (Recommended: yes, per expert panel.)

5. **CIDS version:** The plan references "v2.0" but the current spec is v3.2.0. No evidence of v3.2.1 exists publicly. Should we pin to v3.2.0?

---

## Validation SHACL Resources

For Phase 3 implementation, these files are available:

| File | URL | Purpose |
|---|---|---|
| BasicTier SHACL | `validation/shacl/cids.basictier.shacl.ttl` | Minimum validation |
| EssentialTier SHACL | `validation/shacl/cids.essentialtier.shacl.ttl` | Mid-tier validation |
| FullTier SHACL | `validation/shacl/cids.fulltier.shacl.ttl` | Complete validation |
| All combined | `validation/shacl/cids.all.shacl.ttl` | All shapes |
| Validation script | `CIDS-validate.sh` | Wrapper with Python summariser |
| JSON-LD context | `contexts/cidsContext.jsonld` | Official context for exports |

Validation command: `shacl validate -s cids.basictier.shacl.ttl -d export.jsonld > report.ttl`

Python option: `pyshacl` library can validate in-process without Apache Jena.

---

## Recommended Implementation Order Updates

No change to the overall phase sequence. Within phases, prioritise corrections:

**Phase 1 (Metadata Fields):**
1. Apply corrections C1-C5 to the plan document first
2. Add fields as planned (all are correct)
3. Consider adding `cids_defined_by` to MetricDefinition (for A2)

**Phase 2 (Code Lists):**
1. Expand CidsCodeList model per A1 (add specification_uri, defined_by_name, defined_by_uri)
2. Import all 17 lists but prioritise #1-10

**Phase 2.5 (Enriched Reports):**
1. Update version reference to "CIDS v3.2" (C2)
2. Proceed as planned

**Phase 3 (JSON-LD Export):**
1. Use official cidsContext.jsonld (C1)
2. Construct Code, StakeholderOutcome, Measure objects correctly (A1, A3, A5)
3. Map BeneficialStakeholder to program cohorts, not individual clients (A4)
4. Validate against BasicTier SHACL first, then EssentialTier

**Phase 4 (Impact Dimensions):**
1. Flag ImpactDuration as FullTier-only (A6)
2. Implement ImpactScale and ImpactDepth for EssentialTier

---

## Conclusion

The CIDS implementation plan is well-designed and the corrections identified are manageable. The core architecture (optional metadata fields, phased delivery, config template integration, aggregate-only export) is sound. With the 5 critical corrections applied to the plan document and the 6 Phase 3 items tracked, KoNote can proceed with confidence.

**GO for implementation with corrections.**
