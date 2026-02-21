# CIDS JSON-LD Export — Implementation Plan

**Task ID:** CIDS-EXPORT1
**Created:** 2026-02-21
**Status:** Waiting on approval from [PM] and/or [funder contact] before building
**Strategic value:** Full CIDS compliance would make KoNote one of the first participant management systems in Canada to deliver standardised impact data exports — a significant differentiator for funder adoption across the nonprofit sector.

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
| `cids:BeneficialStakeholder` | `ClientFile` | Participants — add role tagging |
| `cids:Theme` | `MetricDefinition.category` | Map internal categories to CIDS themes |
| `cids:Code` | New: code list references | External taxonomy links (IRIS+, SDG, ICNPO) |
| `cids:Input` | Not modelled | Funding/resources — out of scope for now |
| `cids:Output` | Session counts, service stats | Already computed in funder reports |

### CIDS Tiers

CIDS defines compliance tiers. KoNote should target **EssentialTier** first, then **FullTier**:

| Tier | What It Covers | KoNote Status |
|---|---|---|
| **BasicTier** | Organisation name, legal status, address | Easy — add org metadata model |
| **EssentialTier** | Programs, outcomes, indicators, stakeholders, impact dimensions | Core work — metadata fields + exports |
| **FullTier** | Counterfactuals, impact risk categories, detailed characteristics | Future — computed from longitudinal data |
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
| `operating_name` | CharField | `sch:name` | Display name |
| `description` | TextField | `sch:description` | Mission statement |
| `legal_status` | CharField | `org:hasLegalStatus` | Charity, nonprofit, etc. |
| `sector_codes` | JSONField | `cids:hasCode` | From ICNPOsector code list |
| `province` | CharField | `cids:addressRegion` | From ProvinceTerritory code list |
| `city` | CharField | `cids:addressLocality` | |
| `postal_code` | CharField | `cids:postalCode` | |
| `website` | URLField | `sch:url` | |

**Where it lives:** `apps/settings/models.py` (alongside existing AgencySettings)

#### 1b. New fields on `MetricDefinition`

| Field | Type | CIDS Property | Notes |
|---|---|---|---|
| `cids_indicator_uri` | CharField(blank=True) | `@id` | CIDS identifier (CharField not URLField — URIs may use urn: schemes) |
| `iris_metric_code` | CharField(blank=True) | `cids:hasCode` | From IrisMetric53 code list |
| `sdg_goals` | JSONField(default=list) | `cids:hasCode` | List of SDG numbers (1-17) |
| `unit_of_measure_code` | CharField(blank=True) | `i72:unit_of_measure` | From UnitsOfMeasureList |
| `cids_theme` | CharField(blank=True) | `cids:Theme` | From IRISImpactTheme code list |

#### 1c. New fields on `Program`

| Field | Type | CIDS Property | Notes |
|---|---|---|---|
| `cids_sector_code` | CharField(blank=True) | `cids:hasCode` | From ICNPOsector or ESDCSector |
| `population_served_codes` | JSONField(default=list) | `cids:hasCode` | From PopulationServed code list |
| `funder_program_code` | CharField(blank=True) | — | Funder-assigned ID for cross-referencing |

#### 1d. New fields on `PlanTarget`

| Field | Type | CIDS Property | Notes |
|---|---|---|---|
| `cids_outcome_uri` | CharField(blank=True) | `@id` | CIDS outcome identifier (CharField not URLField) |
| `cids_impact_theme` | CharField(blank=True) | `cids:Theme` | From IRISImpactTheme |

### Phase 2: CIDS Code List Integration

Import the 17 CIDS code lists so admins can pick from dropdowns rather than typing URIs manually.

#### 2a. New model: `CidsCodeList`

| Field | Type | Notes |
|---|---|---|
| `list_name` | CharField | e.g., "ICNPOsector", "SDGImpacts", "PopulationServed" |
| `code` | CharField | The code value |
| `label` | CharField | Display label |
| `label_fr` | CharField | French label (where available) |
| `description` | TextField | Longer description |
| `source_url` | URLField | Link to Common Approach code list |
| `version_date` | DateField | When this code list version was published (for staleness warnings) |

**Population:** Management command `import_cids_codelists` that fetches from `codelist.commonapproach.org` and populates the table. Run once during setup, re-run to update. Warn admins when local copy is stale.

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
> This report uses the Common Impact Data Standard (CIDS) v2.0
> - Sector: Social Services (ICNPO-4)
> - SDG Alignment: SDG 1 (No Poverty), SDG 11 (Sustainable Cities)
> - Outcome indicators mapped to IRIS+ metrics
> - Demographic categories from Statistics Canada classifications

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
  "@context": {
    "cids": "http://ontology.commonapproach.org/cids#",
    "org": "http://www.w3.org/ns/org#",
    "i72": "http://ontology.eil.utoronto.ca/ISO21972/iso21972#",
    "sch": "https://schema.org/",
    "sdg": "http://metadata.un.org/sdg/",
    "prov": "http://www.w3.org/ns/prov#",
    "time": "http://www.w3.org/2006/time#"
  },
  "@type": "cids:ImpactModel",
  "@id": "https://example-agency.konote.ca/cids/impact-model/fy2025-26",
  "cids:forOrganization": {
    "@type": "cids:Organization",
    "@id": "https://example-agency.konote.ca/cids/org",
    "org:hasLegalName": "Community Services Agency",
    "cids:addressRegion": "ON",
    "cids:hasCode": [
      {
        "@type": "cids:Code",
        "sch:codeValue": "ICNPO-4",
        "cids:definedBy": "ICNPOsector",
        "sch:name": "Social Services"
      }
    ]
  },
  "cids:hasProgram": [
    {
      "@type": "cids:Program",
      "@id": "https://example-agency.konote.ca/cids/program/1",
      "sch:name": "Housing First Initiative",
      "cids:hasCode": [
        {
          "@type": "cids:Code",
          "sch:codeValue": "ESDC-Housing",
          "cids:definedBy": "ESDCSector"
        }
      ],
      "cids:hasOutcome": [
        {
          "@type": "cids:Outcome",
          "@id": "https://example-agency.konote.ca/cids/outcome/housing-stability",
          "sch:name": "Improved housing stability",
          "cids:hasIndicator": [
            {
              "@type": "cids:Indicator",
              "@id": "https://example-agency.konote.ca/cids/indicator/housing-stability-score",
              "sch:name": "Housing Stability Score",
              "cids:unitDescription": "score",
              "cids:hasCode": [
                {
                  "@type": "cids:Code",
                  "sch:codeValue": "PI2061",
                  "cids:definedBy": "IrisMetric53",
                  "sch:name": "Client Housing Situation Improved"
                }
              ],
              "cids:hasIndicatorReport": [
                {
                  "@type": "cids:IndicatorReport",
                  "cids:hasBaseline": {
                    "i72:numerical_value": 3.2,
                    "i72:unit_of_measure": "score"
                  },
                  "cids:hasValue": {
                    "i72:numerical_value": 7.8,
                    "i72:unit_of_measure": "score"
                  },
                  "prov:startedAtTime": "2025-04-01",
                  "prov:endedAtTime": "2026-03-31"
                }
              ]
            }
          ],
          "cids:hasImpactReport": {
            "@type": "cids:ImpactReport",
            "cids:hasImpactScale": {
              "@type": "cids:ImpactScale",
              "cids:hasActualAmount": 141,
              "cids:hasPlannedAmount": 156
            },
            "cids:hasImpactDepth": {
              "@type": "cids:ImpactDepth",
              "cids:hasDescription": "90% achievement rate"
            },
            "cids:hasImpactDuration": {
              "@type": "cids:ImpactDuration",
              "prov:startedAtTime": "2025-04-01",
              "prov:endedAtTime": "2026-03-31"
            }
          },
          "cids:forStakeholder": {
            "@type": "cids:BeneficialStakeholder",
            "cids:hasCode": [
              {
                "sch:codeValue": "SDG-11",
                "cids:definedBy": "SDGImpacts",
                "sch:name": "Sustainable Cities and Communities"
              }
            ]
          }
        }
      ]
    }
  ]
}
```

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

CIDS requires three "How Much" dimensions for each outcome. These can be **computed from existing KoNote data**:

| CIDS Dimension | KoNote Source | Computation |
|---|---|---|
| **ImpactScale** (how many) | Count of clients with MetricValues for this target | `hasActualAmount` = count with values; `hasPlannedAmount` = count enrolled |
| **ImpactDepth** (degree of change) | Achievement rate from existing `achievements.py` | % of clients meeting target threshold |
| **ImpactDuration** (how long) | Reporting period from FunderReportForm date range | Start/end dates of the export period |

No new data entry required — these are derived from data KoNote already collects.

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
4. **Target tier?** Recommendation: EssentialTier (covers org, programs, outcomes, indicators, impact dimensions)

---

## Related Tasks

- **RPT-SCHEMA1** — Define standardised report schema for [funder partner] (CIDS codes would feed into this)
- **SCALE-ROLLUP1** — Cross-agency data rollup for funders (CIDS-tagged data makes rollup much easier)
- **SCALE-API1** — Cross-agency reporting API (could serve JSON-LD directly)
- **MT-CONSORT1** — Consortium data model (CIDS export + multi-tenancy = portfolio-wide impact reports)
- **DEPLOY-TEMPLATE1** — [funder partner] config template (should include pre-mapped CIDS codes)

---

## References

- [CIDS Ontology (Turtle)](https://raw.githubusercontent.com/commonapproach/CIDS/main/cids.ttl)
- [CIDS GitHub Repository](https://github.com/commonapproach/CIDS)
- [CIDS FAQ for Developers](https://github.com/commonapproach/CIDS/blob/main/faq/README.md)
- [Common Approach Code Lists](https://codelist.commonapproach.org/)
- [Common Approach Website](https://commonapproach.org/)
