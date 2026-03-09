# Funder Reporting Profiles

**Status:** Parking lot — depends on Common Approach standardising the template format
**TODO ID:** CIDS-FUNDER-PROFILE1
**GK reviews:** Yes (data modelling, funder workflow)

## Problem

CIDS allows each agency to define metrics in their own way and tag them with shared taxonomy codes (IRIS+, SDG, ICNPO, PopulationServed). This is good for agencies — they measure what matters to their program. But funders need to aggregate across a funding stream.

The missing piece: there's no standardised way for a funder to say "here's what I need you to report on" using CIDS vocabulary, and no way for an agency's system to receive that request and filter its export accordingly.

## Proposed concept: Reporting Profiles

A **reporting profile** is a CIDS document that a funder publishes to define their reporting requirements. It specifies which taxonomy codes and CIDS classes the funder wants populated — but not what specific metrics to use.

### Example profile

A funder's youth employment funding stream might require:

- **Taxonomy codes:** SDG 8, IRIS+ OI4060, at least one PopulationServed code
- **CIDS classes required:** IndicatorReport, Stakeholder, ImpactModel, ImpactRisk, Counterfactual
- **CIDS classes optional:** Service, Activity (Full Tier bonus)
- **Minimum reporting:** At least one outcome indicator tagged to each required taxonomy code

### How it would work in KoNote

1. **Funder publishes a reporting profile** — a structured document (JSON-LD or simpler JSON) listing required codes and classes
2. **Agency admin imports the profile** — it appears as a named profile (e.g., "Prosper Canada Youth Employment 2025-26")
3. **System shows a mapping checklist** — "This funder requires SDG 8 outcomes. You have 3 metrics tagged SDG 8. Requirements met." Or: "This funder requires a Counterfactual. Your evaluation framework doesn't have one yet."
4. **Export filters through the profile** — when the agency exports for this funder, the CIDS document contains exactly what the funder asked for, structured the way they asked for it
5. **Funder receives structured exports from all funded agencies** — because every agency reported against the same profile, the funder can aggregate by taxonomy code

### What the funder can aggregate

With reporting profiles, a funder's funding-stream summary can answer:

- How many programs met their own targets (for indicators tagged to the required codes)?
- Which populations are being served across the stream?
- What impact risks are common across funded programs?
- How complete is CIDS reporting across the stream (Full Tier vs. Basic Tier)?
- Which programs have evaluator attestations?

What the funder does **not** get is a single averaged metric across agencies — because agencies measure differently. Instead they get thematic aggregation: "12 of 15 programs report positive outcomes for SDG 8."

## What already exists in KoNote

Most of the infrastructure is built:

- **Taxonomy codes on indicators** — metrics can be tagged with IRIS+, SDG, ICNPO codes
- **Taxonomy classification workflow** — AI suggests mappings, admin reviews and approves
- **Full Tier JSON-LD export** — assembles all 14 CIDS classes
- **Coverage dashboard** — shows which classes are populated per program

The new pieces would be:

- **Profile model** — stores funder name, required codes, required classes
- **Import mechanism** — parse a funder's profile document
- **Mapping UI** — show agency admin which requirements are met/unmet
- **Filtered export** — generate a CIDS document scoped to a specific profile

## Dependencies and open questions

- **Common Approach standardisation:** Does Common Approach envision reporting templates as CIDS documents? If they standardise a profile format, we should use it rather than inventing our own. This question has been raised in our working document shared with Common Approach (March 2026).
- **Profile format:** Could be JSON-LD (a CIDS document with required classes but no values), or a simpler JSON/YAML schema. Depends on what Common Approach recommends.
- **Multi-funder programs:** An agency program might report to multiple funders with different profiles. The UI needs to handle this without overwhelming the admin.
- **Partial compliance:** What happens when an agency can't fill all required fields? The profile should distinguish "required" from "recommended" to avoid blocking exports.

## Anti-patterns

- **Do not force common metrics.** The whole point is that agencies measure in their own way. A profile specifies taxonomy codes, not specific metric definitions.
- **Do not build this before Common Approach weighs in.** The profile format should align with whatever the standard community develops. Building a proprietary format risks rework.
- **Do not conflate profiles with data sharing agreements.** A reporting profile defines what data to include in an export — it does not grant access to data. Export approval and consent are separate workflows (already built).

## See also

- `tasks/wireframes/common-approach-working-document.html` — "How funders aggregate across agencies" section with mock funder dashboard
- `tasks/design-rationale/reporting-architecture.md` — existing reporting system architecture
- `tasks/design-rationale/phipa-consent-enforcement.md` — consent controls on data sharing
