# CIDS JSON-LD Export — Implementation Plan

**Task ID:** CIDS-EXPORT1
**Created:** 2026-02-21
**Status:** Validated against CIDS 3.2.0 — GO with corrections (see tasks/cids-plan-validation.md)
**Validated:** 2026-02-24 — 5 critical corrections applied inline, 6 Phase 3 items documented
**Strategic value:** Full CIDS compliance would make KoNote one of the first participant management systems in Canada to deliver standardised impact data exports — a significant differentiator for funder adoption across the nonprofit sector.

---

## Validation Notes (2026-02-24)

> Full validation report: `tasks/cids-plan-validation.md`

**Critical corrections (all applied inline — look for ⚠️ markers):**

1. ~~Namespace URIs wrong~~ → JSON-LD example now uses official context URL
2. ~~Version was v2.0~~ → Corrected to v3.2 throughout
3. ~~Indicator unit was `i72:unit_of_measure`~~ → Corrected to `cids:unitDescription`
4. ~~Entity names used `sch:name`/`sch:description`~~ → Corrected to `org:hasName`/`cids:hasDescription`
5. ~~Program was EssentialTier~~ → Corrected to FullTier in tier table

**Phase 3 implementation notes (from validation):**

- Code objects need 6 required SHACL fields — CidsCodeList model expanded to match (see Phase 2a)
- EssentialTier Indicator requires `cids:hasBaseline` and `cids:definedBy` — both fields added to MetricDefinition (see Phase 1b)
- StakeholderOutcome class — construct at export time from Program cohort + PlanTarget
- BeneficialStakeholder = group/cohort, NOT individual — concept mapping corrected
- `i72:value` wraps in `i72:Measure` objects — JSON-LD example corrected
- ImpactDuration is FullTier only — Impact Dimensions table annotated with tiers

---

## Background

The [Common Impact Data Standard (CIDS)](https://ontology.commonapproach.org/) is maintained by [Common Approach](https://commonapproach.org/) and backed by a consortium of Canadian funders. It defines a shared vocabulary for how social-purpose organisations report outcomes to funders using linked data (RDF/JSON-LD).

**Why this matters for KoNote:**
- Funders increasingly want to compare outcomes across their portfolios without requiring identical metrics from every agency
- CIDS enables "report once, share many ways" — agencies export standardised files that any CIDS-aware funder can consume
- Few or no current client management systems deliver full CIDS compliance
- Early adoption positions KoNote as the reference implementation for Canadian nonprofits

---

## Expert Panel Recommendations (2026-02-21)

An expert panel (Nonprofit Technology Strategist, Data Interoperability Specialist, Product Strategist, Funder Relations Expert) reviewed this plan and reached consensus on five key recommendations:

### 1. Engage Common Approach early — before writing code

Position KoNote as a pilot implementer. Common Approach needs reference implementations to make CIDS credible; KoNote needs validation and co-marketing. Join their technical working group or developer office hours. Zero downside.

### 2. Build CIDS tagging into the onboarding config template system

When a config template (e.g., [funder partner]) already includes IRIS+ codes for standard metrics, every agency deployed with that template is automatically CIDS-tagged. Zero per-agency effort. Make CIDS metadata tagging free for all agencies to maximise the network effect — funders want *all* their agencies using standardised codes, not just the ones who can afford it.

### 3. Ship CIDS-enriched CSV/PDF first (new Phase 2.5)

Most Canadian funders cannot consume JSON-LD today. A "Standards Alignment" appendix page on existing PDF/CSV reports delivers 80% of the value with 20% of the effort. This is the quick win that proves value to the funder who expressed interest.

### 4. Use CharField (not URLField) for CIDS URIs, add @id to all entities

In linked data, URIs are identifiers, not necessarily clickable URLs — some use `urn:` schemes. Every JSON-LD entity should have an `@id` for real graph interoperability across agencies.

### 5. Include basic SHACL validation in Phase 3 (not deferred)

A simple pass/fail SHACL check before export catches structural errors early. Defer the fancy conformance badge and detailed reporting to Phase 5.

### Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| CIDS doesn't gain traction beyond SFF | Medium | Low | Metadata fields (SDG, IRIS+) have standalone value regardless |
| Funder can't consume JSON-LD | High (today) | Medium | Phase 2.5 delivers value via CSV/PDF; JSON-LD is future-ready |
| Common Approach changes the ontology | Low | Medium | Code list versioning + SHACL validation catch breaking changes |
| Agencies resist filling in CIDS fields | Medium | Medium | Pre-populate via config templates; zero frontline staff burden |
| Competitor builds CIDS support faster | Low (18-month window) | High | Engage Common Approach early for reference implementation status |

### Pricing Model

- **All tiers:** CIDS metadata tagging (configured during onboarding, zero marginal cost)
- **Premium / managed service:** JSON-LD export, SHACL validation badge, API endpoint for funder portals
- **Buyer:** The funder consortium pays (e.g., [funder partner]'s managed service includes CIDS reporting for all member agencies)

---

## How CIDS Maps to KoNote

### Concept Mapping

| CIDS Class | KoNote Model | Notes |
|---|---|---|
| `cids:Organization` | Implicit (single-tenant) | Need lightweight org metadata |
| `cids:Program` | `Program` | Add sector + population codes |
| `cids:Activity` | `ProgressNote` (aggregated by interaction_type) | "This program delivered 847 sessions of type X" — not individual notes |
| `cids:Outcome` | `PlanTarget` | Client goals/outcomes — add CIDS URI |
| `cids:Indicator` | `MetricDefinition` | Measurement tools — add IRIS+ code, SDG |
| `cids:IndicatorReport` | `MetricValue` | Already captures value + timestamp |
| `cids:ImpactReport` | New: computed from data | Scale/depth/duration dimensions |
| `cids:BeneficialStakeholder` | Program cohort (aggregate) | **NOT ClientFile** — represents a group/cohort, not individual. ⚠️ Corrected 2026-02-24 |
| `cids:Theme` | `MetricDefinition.category` | Map internal categories to CIDS themes |
| `cids:Code` | New: code list references | External taxonomy links (IRIS+, SDG, ICNPO) |
| `cids:StakeholderOutcome` | Constructed at export time | ⚠️ Added 2026-02-24 — junction of Stakeholder (who) and Outcome (what), required at EssentialTier |
| `cids:Target` | `PlanTarget` target values | Distinct from cids:Outcome — represents measurement targets for indicators |
| `cids:Input` | Not modelled | Funding/resources — out of scope for now |
| `cids:Output` | Session counts, service stats | Already computed in funder reports |

### CIDS Tiers

CIDS defines compliance tiers. ⚠️ **Corrected 2026-02-24** — Program is FullTier, not EssentialTier. KoNote should target **BasicTier** first (fast win), then **EssentialTier** (impact dimensions), then **FullTier** (programs, activities):

| Tier | What It Covers | KoNote Status |
|---|---|---|
| **BasicTier** | Organisation, Outcome, Indicator, IndicatorReport, Theme (5 classes) | Quick win — org metadata + outcome/indicator export |
| **EssentialTier** | + Stakeholder, StakeholderOutcome, ImpactReport, Target, Code, Characteristic, HowMuchImpact (Scale, Depth) | Core work — metadata fields + impact dimensions |
| **FullTier** | + Program, ImpactModel, Activity, Service, Input, Output, ImpactDuration, Counterfactual, ImpactRisk (9 subtypes) | Future — KoNote naturally includes programs, so FullTier is achievable |
| **SFFTier** | Social Finance Fund specific codes + characteristics | Only if SFF funding is involved |

---

## Implementation Phases (revised per expert panel)

### Phase 1: Metadata Fields (schema changes, no UI disruption)

Add optional fields to existing models so agencies can tag their data with CIDS codes. None of these are required — agencies only fill them in when a funder asks for CIDS-compliant exports.

#### 1a. New model: `OrganizationProfile` (one per tenant)

Stores CIDS BasicTier org metadata. Single row per agency instance.

| Field | Type | CIDS Property | Notes |
|---|---|---|---|
| `legal_name` | CharField | `org:hasLegalName` | Required for BasicTier |
| `operating_name` | CharField | `org:hasName` | Display name (⚠️ corrected from `sch:name`) |
| `description` | TextField | `cids:hasDescription` | Mission statement (⚠️ corrected from `sch:description`) |
| `legal_status` | CharField | `org:hasLegalStatus` | Charity, nonprofit, etc. |
| `sector_codes` | JSONField | `cids:hasCode` | From ICNPOsector code list |
| `street_address` | CharField | `cids:streetAddress` | Street address — required for CIDS Address |
| `city` | CharField | `cids:addressLocality` | Required for CIDS Address |
| `province` | CharField | `cids:addressRegion` | From ProvinceTerritory code list; required for CIDS Address |
| `postal_code` | CharField | `cids:postalCode` | Required for CIDS Address |
| `country` | CharField | `cids:addressCountry` | Default "CA"; required for CIDS Address |
| `website` | URLField | `sch:url` | |

**Where it lives:** `apps/admin_settings/models.py` (alongside existing TerminologyOverride / FeatureToggle / InstanceSetting)

#### 1b. New fields on `MetricDefinition`

| Field | Type | CIDS Property | Notes |
|---|---|---|---|
| `cids_indicator_uri` | CharField(blank=True) | `@id` | CIDS identifier (CharField not URLField — URIs may use urn: schemes) |
| `iris_metric_code` | CharField(blank=True) | `cids:hasCode` | From IrisMetric53 code list |
| `sdg_goals` | JSONField(default=list) | `cids:hasCode` | List of SDG numbers (1-17) |
| `cids_unit_description` | CharField(blank=True) | `cids:unitDescription` | Human-readable unit label from UnitsOfMeasureList (⚠️ corrected from `i72:unit_of_measure` — that property is on IndicatorReport/Measure, not Indicator) |
| `cids_theme` | CharField(blank=True) | `cids:forTheme` | From IRISImpactTheme code list (⚠️ corrected: maps to Theme via `forTheme` on Outcome) |
| `cids_defined_by` | CharField(blank=True) | `cids:definedBy` | URI of defining organisation (e.g., GIIN for IRIS+ metrics, agency for custom). Required at EssentialTier. Can auto-derive from iris_metric_code presence. |
| `cids_has_baseline` | CharField(blank=True) | `cids:hasBaseline` | Baseline value description. Required at EssentialTier. Human-readable (e.g., "Average score 3.2 at intake"). |

#### 1c. New fields on `Program`

| Field | Type | CIDS Property | Notes |
|---|---|---|---|
| `cids_sector_code` | CharField(blank=True) | `cids:hasCode` | From ICNPOsector or ESDCSector |
| `population_served_codes` | JSONField(default=list) | `cids:hasCode` | From PopulationServed code list |
| `description_fr` | TextField(blank=True) | — | French description — currently missing from Program model. Needed for bilingual CIDS exports. |
| `funder_program_code` | CharField(blank=True) | — | Funder-assigned ID for cross-referencing |

#### 1d. New fields on `PlanTarget`

| Field | Type | CIDS Property | Notes |
|---|---|---|---|
| `cids_outcome_uri` | CharField(blank=True) | `@id` | CIDS outcome identifier (CharField not URLField) |
| `cids_impact_theme` | CharField(blank=True) | `cids:Theme` | From IRISImpactTheme |

### Phase 2: CIDS Code List Integration

Import the 17 CIDS code lists so admins can pick from dropdowns rather than typing URIs manually.

#### 2a. New model: `CidsCodeList`

| Field | Type | CIDS Property | Notes |
|---|---|---|---|
| `list_name` | CharField(max_length=100) | — | e.g., "ICNPOsector", "SDGImpacts", "PopulationServed" |
| `code` | CharField(max_length=100) | `sch:codeValue` | The code value (e.g., "ICNPO-4", "SDG-11", "PI2061") |
| `label` | CharField(max_length=255) | `org:hasName` | Display label (English) |
| `label_fr` | CharField(max_length=255, blank=True) | — | French label (where available) |
| `description` | TextField(blank=True) | `cids:hasDescription` | Longer description |
| `specification_uri` | CharField(max_length=500, blank=True) | `cids:hasSpecification` | URI of code list spec (e.g., `https://codelist.commonapproach.org/codeLists/ICNPOsector`) |
| `defined_by_name` | CharField(max_length=255, blank=True) | `cids:definedBy` → `org:hasLegalName` | Organisation name (e.g., "GIIN", "United Nations") |
| `defined_by_uri` | CharField(max_length=500, blank=True) | `cids:definedBy` → `@id` | URI of defining organisation |
| `source_url` | URLField(blank=True) | — | Link to Common Approach code list page |
| `version_date` | DateField(blank=True, null=True) | — | When this code list version was published (for staleness warnings) |

**Indexes:** `unique_together = [("list_name", "code")]`

**Why the extra fields?** CIDS SHACL EssentialTier requires Code objects with `hasName`, `hasDescription`, `codeValue`, `definedBy` (an Organisation reference), and `hasSpecification` (a URI). Storing these on CidsCodeList means the JSON-LD export can construct full Code objects without hardcoding standards body references.

**Population:** Management command `import_cids_codelists` that fetches from `codelist.commonapproach.org` and populates the table. Run once during setup, re-run to update. Warn admins when local copy is stale. Formats available: JSON-LD, CSV, Turtle, RDF/XML.

#### 2b. Admin UI for CIDS tagging

- Add CIDS fields to the existing Program admin form (collapsible "Funder Reporting" section)
- Add CIDS fields to MetricDefinition admin form
- Use select2-style dropdowns populated from `CidsCodeList`
- PlanTarget CIDS fields can be set via the plan template (so they auto-apply to client targets)
- Integrate into config template system — e.g., [funder partner] template pre-maps CIDS codes for standard metrics

### Phase 2.5: CIDS-Enriched CSV/PDF Reports (quick win)

**This is the immediate value delivery.** Before building JSON-LD, add CIDS codes to the existing funder report format that program officers already know how to read.

#### What changes in existing reports

- Add IRIS+ metric codes next to indicator names in CSV/PDF exports (e.g., "Housing Stability (IRIS+ PI2061)")
- Add SDG goal references to outcome sections
- Add a **"Standards Alignment" appendix page** to PDF funder reports:

> **Standards Alignment**
> This report uses the Common Impact Data Standard (CIDS) v3.2
> - Organisation: [Legal Name] — [Province]
> - Sector: Social Services (ICNPO-4)
> - SDG Alignment: SDG 1 (No Poverty), SDG 11 (Sustainable Cities)
> - Outcome indicators mapped to IRIS+ metrics
> - Demographic categories from Statistics Canada classifications
> - Code lists sourced from codelist.commonapproach.org (version: [date])

This one page transforms a regular funder report into a standards-compliant one in the eyes of a program officer who reads PDFs.

#### Implementation

- Modify `generate_funder_report_csv_rows()` to include CIDS codes when available
- Modify funder report PDF template to add Standards Alignment appendix
- No new export format — just enrich existing CSV/PDF
- Graceful degradation: if no CIDS codes are configured, reports look exactly the same as today

### Phase 3: JSON-LD Export (with basic SHACL validation)

New export format alongside existing CSV and PDF. Produces a valid JSON-LD document conforming to the CIDS ontology. Includes basic SHACL pass/fail validation before export.

#### 3a. Export structure

The JSON-LD output follows the CIDS class hierarchy. Every entity includes an `@id` for graph interoperability:

```json
{
  "@context": "https://ontology.commonapproach.org/contexts/cidsContext.jsonld",
  "@type": "cids:Organization",
  "@id": "https://example-agency.konote.ca/cids/org",
  "org:hasLegalName": "Community Services Agency",
  "hasName": "Community Services Agency",
  "cids:hasAddress": {
    "@type": "cids:Address",
    "cids:streetAddress": "123 Main St",
    "cids:addressLocality": "Ottawa",
    "cids:addressRegion": "ON",
    "cids:postalCode": "K1A 0B1",
    "cids:addressCountry": "CA"
  },
  "cids:hasCode": [
    {
      "@type": "cids:Code",
      "@id": "https://example-agency.konote.ca/cids/code/icnpo-4",
      "hasName": "Social Services",
      "hasDescription": "ICNPO sector classification for social services",
      "sch:codeValue": "ICNPO-4",
      "cids:definedBy": {
        "@type": "cids:StandardsOrganization",
        "@id": "https://unstats.un.org/",
        "org:hasLegalName": "United Nations Statistics Division"
      },
      "cids:hasSpecification": "https://codelist.commonapproach.org/codeLists/ICNPOsector"
    }
  ],
  "cids:hasOutcome": [
    {
      "@type": "cids:Outcome",
      "@id": "https://example-agency.konote.ca/cids/outcome/housing-stability",
      "hasName": "Improved housing stability",
      "hasDescription": "Participants achieve and maintain stable housing",
      "cids:forOrganization": {"@id": "https://example-agency.konote.ca/cids/org"},
      "cids:forTheme": {
        "@type": "cids:Theme",
        "@id": "https://example-agency.konote.ca/cids/theme/sdg-11",
        "hasName": "Sustainable Cities and Communities",
        "hasDescription": "UN SDG Goal 11",
        "cids:hasCode": {
          "@type": "cids:Code",
          "sch:codeValue": "SDG-11",
          "hasName": "Sustainable Cities and Communities",
          "cids:definedBy": {
            "@type": "cids:StandardsOrganization",
            "@id": "https://unstats.un.org/sdgs/",
            "org:hasLegalName": "United Nations"
          },
          "cids:hasSpecification": "https://codelist.commonapproach.org/codeLists/SDGImpacts"
        }
      },
      "cids:hasIndicator": [
        {
          "@type": "cids:Indicator",
          "@id": "https://example-agency.konote.ca/cids/indicator/housing-stability-score",
          "hasName": "Housing Stability Score",
          "hasDescription": "Self-reported housing stability on a 1-10 scale",
          "cids:unitDescription": "score",
          "cids:forOrganization": {"@id": "https://example-agency.konote.ca/cids/org"},
          "cids:hasCode": [
            {
              "@type": "cids:Code",
              "sch:codeValue": "PI2061",
              "hasName": "Client Housing Situation Improved",
              "hasDescription": "IRIS+ metric for housing outcome tracking",
              "cids:definedBy": {
                "@type": "cids:StandardsOrganization",
                "@id": "https://iris.thegiin.org/",
                "org:hasLegalName": "Global Impact Investing Network (GIIN)"
              },
              "cids:hasSpecification": "https://codelist.commonapproach.org/codeLists/IrisMetric53"
            }
          ],
          "cids:hasIndicatorReport": [
            {
              "@type": "cids:IndicatorReport",
              "@id": "https://example-agency.konote.ca/cids/report/housing-stability-fy2025",
              "hasName": "Housing Stability Score — FY2025-26",
              "i72:value": {
                "@type": "i72:Measure",
                "i72:hasNumericalValue": "7.8"
              },
              "cids:forIndicator": {"@id": "https://example-agency.konote.ca/cids/indicator/housing-stability-score"},
              "cids:forOrganization": {"@id": "https://example-agency.konote.ca/cids/org"},
              "prov:startedAtTime": "2025-04-01T00:00:00-04:00",
              "prov:endedAtTime": "2026-03-31T23:59:59-04:00"
            }
          ]
        }
      ]
    }
  ]
}
```

> **Note:** This example targets **BasicTier** — Organisation + Outcome + Indicator + IndicatorReport + Theme. For EssentialTier, add Stakeholder, StakeholderOutcome, ImpactReport, Target, and Code objects. For FullTier, wrap in an ImpactModel and add Program, Activity, and Service objects. See `tasks/cids-plan-validation.md` for complete tier requirements.

#### 3b. What gets exported (no PII)

The JSON-LD export is **aggregate only** — no individual client data:

- Organisation metadata (name, sector, province)
- Program metadata (name, sector codes, populations served)
- Outcomes (from PlanTargets — aggregated across clients)
- Indicators (from MetricDefinitions — with CIDS codes)
- IndicatorReports (aggregate: baseline average, current average, date range)
- ImpactReport dimensions (scale = count, depth = achievement rate, duration = period)
- SDG and IRIS+ code references
- Demographic breakdowns (from existing ReportTemplate/DemographicBreakdown)

**Not exported:** client names, record IDs, individual metric values, note text, or any encrypted fields.

#### 3c. Implementation approach

- New file: `apps/reports/cids_export.py` — builds the JSON-LD structure from existing data
- New format option in `FunderReportForm`: `("jsonld", _("JSON-LD (CIDS standard)"))`
- Reuse existing `generate_funder_report_data()` as the data source
- Add CIDS metadata from the new model fields
- **Basic SHACL validation** using `pyshacl` — pass/fail check before export, warn user if non-compliant
- Secure export link works the same as CSV/PDF — no new security model needed

### Phase 4: Impact Dimensions (computed, no new data entry)

CIDS defines "How Much" impact dimensions via `cids:HowMuchImpact` subclasses. These can be **computed from existing KoNote data** — no new data entry required:

| CIDS Dimension | Tier | KoNote Source | Computation |
|---|---|---|---|
| **ImpactScale** (how many) | EssentialTier | Count of clients with MetricValues for this target | `i72:value` = count with values (actual); compare to count enrolled (planned) |
| **ImpactDepth** (degree of change) | EssentialTier | Achievement rate from existing `achievements.py` | `i72:value` = % of clients meeting target threshold |
| **ImpactDuration** (how long) | **FullTier** | Reporting period from FunderReportForm date range | `prov:startedAtTime` / `prov:endedAtTime` of the export period |

⚠️ **ImpactDuration is FullTier** — omit from EssentialTier-only exports. ImpactScale and ImpactDepth are required at EssentialTier (each needs `i72:value` as `i72:Measure` object + `cids:hasDescription`).

Each HowMuchImpact dimension requires:
- `i72:value` → nested `i72:Measure` with `i72:hasNumericalValue` (string, not number)
- `cids:hasDescription` (human-readable explanation)
- `cids:forIndicator` (link to the Indicator being measured)

### Phase 5: Conformance Badge and Detailed Validation (future)

- Detailed SHACL error reporting (not just pass/fail)
- Display a "CIDS Conformance" badge on exports that pass validation
- Optionally submit to Common Approach's validator (if one exists)
- Conformance level indicator: BasicTier / EssentialTier / FullTier

---

## What This Does NOT Require

- **No new data entry for frontline staff.** CIDS metadata is set up once by admins (org profile, program codes, metric codes). Coaches and workers never see it.
- **No changes to existing CSV/PDF exports** (Phase 2.5 enriches them but degrades gracefully if no CIDS codes are set).
- **No breaking changes to existing models.** All new fields are optional (blank=True).
- **No external dependencies for Phases 1-2.5.** JSON-LD is just JSON with a `@context` — Python's built-in `json` module handles it. Phase 3 adds `pyshacl` for validation.
- **No API keys or external services.** Code lists are imported once via management command.

---

## Revised Phase Sequence

| Phase | Deliverable | Value | Depends On |
|---|---|---|---|
| **1** | Metadata fields on existing models + OrganizationProfile | Foundation — no user-facing change | Nothing |
| **2** | Code list import + admin dropdowns + config template integration | Admins can tag programs and metrics with CIDS codes | Phase 1 |
| **2.5** | CIDS-enriched CSV/PDF reports + "Standards Alignment" appendix | **Immediate funder value** — existing reports get standardised codes | Phase 2 |
| **3** | JSON-LD export with basic SHACL validation | Full CIDS compliance — the differentiator | Phases 1-2 |
| **4** | Computed impact dimensions (scale, depth, duration) | Richer CIDS output, no new data entry | Phase 3 |
| **5** | Conformance badge + detailed validation reporting | Polish and marketing | Phase 3 |

Phases 1 through 2.5 are the minimum viable deliverable. Phases 3-5 complete full JSON-LD compliance.

---

## Codebase Integration Notes

Findings from codebase review (2026-02-24) — existing patterns to reuse and gaps to address:

### Existing code to leverage

- **`apps/reports/aggregations.py`** — `metric_stats()` returns count, avg, min, max, sum for MetricValues. Directly reusable for computing ImpactScale (count) and ImpactDepth (achievement rate) in Phase 4.
- **`apps/reports/funder_report.py`** — `generate_funder_report_data()` is the main report entry point. Phase 2.5 enriches its output; Phase 3 uses it as the data source for JSON-LD.
- **`apps/reports/export_engine.py`** — `generate_template_csv_rows()` handles template-driven CSV output. Phase 2.5 modifies this to include CIDS codes alongside indicator names.
- **`apps/reports/models.py`** — `ReportMetric` already has 7 aggregation types; `DemographicBreakdown` supports demographic segmentation; `SecureExportLink` with 24-hour expiry handles secure downloads.
- **Admin form patterns** — `MetricDefinitionForm` (18 fields) and `ProgramForm` (with confidential keyword detection) in `apps/plans/forms.py` and `apps/programs/forms.py`. Phase 2b CIDS fields should follow these patterns (collapsible sections, consistent validation).

### Known gaps to address

- **`Program.description_fr` is missing.** Program has `description` (TextField) but no French translation field. Needed for bilingual CIDS exports. Add alongside CIDS fields in Phase 1c or as a separate migration.
- **No singleton pattern for settings.** `InstanceSetting` uses class methods, not a singleton. `OrganizationProfile` should follow the same pattern (class method to get-or-create the single row).
- **PlanTargetForm is a plain Form** (not ModelForm) due to encrypted fields. Adding `cids_outcome_uri` and `cids_impact_theme` to PlanTarget will need corresponding fields in the form — these are not encrypted, so they can use standard ModelForm field patterns.

---

## Go-to-Market Strategy

### Immediate (before code is written)
- Engage Common Approach — offer KoNote as a pilot implementer
- Announce "CIDS-ready" positioning on website and in funder conversations
- Discuss requirements with the funder who expressed interest

### After Phase 2.5 (CIDS-enriched reports)
- Produce a real CIDS-tagged funder report from actual program data
- Use as a case study for other funder conversations

### After Phase 3 (JSON-LD export)
- Present at sector conferences (ONN, Imagine Canada)
- Publish: "How KoNote Became Canada's First CIDS-Compliant Outcome Management System"
- Approach Common Approach for co-marketing
- Message: *"KoNote is the first Canadian participant management system built for standardised impact reporting"* — not just "we support CIDS"

---

## Open Questions (for [PM] / [funder contact])

1. **Which funder expressed interest?** We need to confirm their actual consumption pathway — do they want JSON-LD, or would CIDS-tagged CSV/PDF satisfy their requirements?
2. **Should we engage Common Approach now?** Recommendation: yes, position as a partnership/pilot implementation
3. **Should CIDS metadata be part of the [funder partner] config template?** Recommendation: yes, pre-map their standard metrics to IRIS+ codes
4. **Target tier?** ⚠️ Updated per validation: Program is FullTier, not EssentialTier. **Recommendation:** Target FullTier directly — KoNote already has programs, outcomes, indicators, and metric values, so FullTier is naturally achievable. BasicTier validation can be a quick first milestone (5 classes: Organisation, Outcome, Indicator, IndicatorReport, Theme).
5. **CIDS version pinning?** Current spec is v3.2.0 (July 2025). Pin to v3.2.0?

---

## Related Tasks

- **RPT-SCHEMA1** — Define standardised report schema for [funder partner] (CIDS codes would feed into this)
- **SCALE-ROLLUP1** — Cross-agency data rollup for funders (CIDS-tagged data makes rollup much easier)
- **SCALE-API1** — Cross-agency reporting API (could serve JSON-LD directly)
- **MT-CONSORT1** — Consortium data model (CIDS export + multi-tenancy = portfolio-wide impact reports)
- **DEPLOY-TEMPLATE1** — [funder partner] config template (should include pre-mapped CIDS codes)

---

## References

### Ontology and Specification
- [CIDS Ontology HTML (v3.2.0)](https://ontology.commonapproach.org/cids-en.html) — human-readable class/property reference
- [CIDS Ontology (Turtle)](https://raw.githubusercontent.com/commonapproach/CIDS/main/cids.ttl) — machine-readable OWL source
- [CIDS GitHub Repository](https://github.com/commonapproach/CIDS)
- [CIDS Developer Page](https://www.commonapproach.org/developers/data-standard/)
- [CIDS FAQ for Developers](https://github.com/commonapproach/CIDS/blob/main/faq/README.md) — 12 files covering RDF, OWL, SHACL, SPARQL, JSON-LD context files

### JSON-LD and Validation
- [Official JSON-LD Context](https://ontology.commonapproach.org/contexts/cidsContext.jsonld) — **use this as `@context` in exports**
- [SFF JSON-LD Context](https://ontology.commonapproach.org/contexts/sffContext.jsonld)
- [BasicTier SHACL](https://github.com/commonapproach/CIDS/blob/main/validation/shacl/cids.basictier.shacl.ttl)
- [EssentialTier SHACL](https://github.com/commonapproach/CIDS/blob/main/validation/shacl/cids.essentialtier.shacl.ttl)
- [FullTier SHACL](https://github.com/commonapproach/CIDS/blob/main/validation/shacl/cids.fulltier.shacl.ttl)
- [Validation README](https://github.com/commonapproach/CIDS/blob/main/validation/validationReadMe.md) — how to run SHACL validation

### Code Lists
- [Common Approach Code Lists](https://codelist.commonapproach.org/) — all 17 lists, available in JSON-LD, CSV, Turtle, RDF/XML
- Last updated: Dec 1, 2025

### Organisation
- [Common Approach Website](https://commonapproach.org/)
- [CIDS v3.2 Announcement](https://www.commonapproach.org/common-impact-data-standard-version-3-2/)

### KoNote Validation
- [Plan Validation Report](tasks/cids-plan-validation.md) — corrections and tier requirements verified against SHACL shapes
