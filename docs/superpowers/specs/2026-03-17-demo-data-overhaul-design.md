# Demo Data Overhaul — Design Specification

**Date:** 2026-03-17
**Status:** Draft
**Expert panel:** 4 experts (Nonprofit Evaluation, Privacy & Compliance, Product Demonstration, Systems Architecture), 3 rounds, consensus reached

---

## Problem Statement

KoNote's demo instances (demo.konote.ca, demo-dev.konote.ca) have insufficient demo data to showcase core features. Only 15 clients exist across 5 programs (3 per program), which falls below every privacy threshold:

- Metric distributions require 10+ participants (all programs fail)
- Quote collection requires 15+ participants (all programs fail)
- Executive dashboard suppresses stats for programs with < 5 participants (4 of 5 programs fail)
- Funder reports produce near-empty output
- FHIR metadata fields added during the FHIR-informed modelling phase are unpopulated

High-quality demo data is essential for marketing and demonstrating KoNote's value to prospective agencies.

---

## Design Goals

1. **Clear all privacy thresholds** so every feature displays meaningful data
2. **Populate all FHIR metadata fields** to demonstrate data governance maturity
3. **Exercise the permissions matrix** so each demo role shows a distinct, compelling view
4. **Tell a realistic evaluation story** with diverse outcome trends, not just success stories
5. **Maintain the 15 named personas** (DEMO-001 through DEMO-015) as curated narrative characters
6. **Remain idempotent** — safe to re-run on every container startup

---

## Architecture Decision: Config-Aware Engine as Default

**Current state:** `seed.py` calls the hardcoded `seed_demo_data` path unless `DEMO_DATA_PROFILE` env var is set. The config-aware `DemoDataEngine` is only used with an explicit profile.

**Change:** Make the config-aware engine the default path for all demo seeding. The engine already reads the instance's actual programs, metrics, and templates — it just needs a higher client count and FHIR metadata population.

**Flow after change:**
1. `seed.py` runs on container startup when `DEMO_MODE=True`
2. Always calls `DemoDataEngine.run()` with `clients_per_program=20`
3. If `DEMO_DATA_PROFILE` env var is set, loads that profile for richer content
4. Falls back to hardcoded `seed_demo_data` only if the engine fails

---

## Volume Targets

| Program | Service Model | Current Clients | Target Clients | Notes per Client | Total Notes |
|---------|--------------|-----------------|----------------|------------------|-------------|
| Supported Employment | individual | 3 | 20 | 8-12 | ~200 |
| Housing Stability | individual | 3 | 20 | 8-12 | ~200 |
| Youth Drop-In | both | 3 | 20 | 8-12 | ~200 |
| Newcomer Connections | individual | 3 | 20 | 8-12 | ~200 |
| Community Kitchen | group | 6 | 30 | 6-10 | ~240 |
| **Total** | | **15** | **~110** | | **~1,040** |

These volumes clear all thresholds:
- MIN_N_FOR_DISTRIBUTION (10) — 20 participants, minus ~4 "new" (1 assessment) = ~16 included
- MIN_PARTICIPANTS_FOR_QUOTES (15) — 20 participants, all with client_words text
- SMALL_PROGRAM_THRESHOLD (5) — 20 participants, well above
- Full data tier (50+ notes, 3+ months) — ~200 notes over 6 months

---

## Trend Distribution

Realistic Canadian nonprofit outcome trends, applied per-participant:

| Trend | Proportion | Description |
|-------|-----------|-------------|
| improving | 40% | Steady positive trajectory |
| stable | 20% | Maintaining at a good level |
| mixed | 20% | Two steps forward, one step back |
| struggling | 10% | Declining or stuck |
| crisis_then_improving | 10% | Initial crisis followed by recovery |

---

## Program-Specific Metric Mapping

Each program must use metrics that match its service model. Universal metrics (Goal Progress, Self-Efficacy, Satisfaction) are included in all programs.

### Supported Employment (individual)
- Goal Progress (universal, scale 1-5)
- Self-Efficacy (universal, scale 1-5)
- Satisfaction (universal, scale 1-5)
- Confidence in your job search (scale 1-5)
- How ready do you feel for work? (scale 1-5)
- Hours Worked (past week) (scale 0-168)
- Job Placement (achievement)

### Housing Stability (individual)
- Goal Progress (universal)
- Self-Efficacy (universal)
- Satisfaction (universal)
- How safe do you feel where you live? (scale 1-5)
- Nights in Shelter (past 30 days) (scale 0-30, lower-is-better)
- Monthly Income (scale 0-null)
- Housing Secured (achievement)

### Youth Drop-In (both — individual + group)
- Goal Progress (universal)
- Self-Efficacy (universal)
- Satisfaction (universal)
- How connected do you feel to the group? (scale 1-5)
- How are you feeling today? (scale 1-5)
- School Attendance Rate (scale 0-100%)
- School Enrolment (achievement)
- Inclusivity Battery (5-item instrument, scale 1-4)

### Newcomer Connections (individual)
- Goal Progress (universal)
- Self-Efficacy (universal)
- Satisfaction (universal)
- Comfort with English in daily life (scale 1-5)
- Confidence navigating services (scale 1-5)
- Community connections this month (scale 0-20)

### Community Kitchen (group)
- Goal Progress (universal)
- Self-Efficacy (universal)
- Satisfaction (universal)
- Cooking confidence (scale 1-5)
- Healthy meals prepared this week (scale 0-14)
- Sessions attended this month (scale 0-20)
- Inclusivity Battery (5-item instrument, scale 1-4)

---

## FHIR Metadata Population

### metric_library.json Enrichment

Add these fields to every metric in the library:

| Field | Description | Example Values |
|-------|-------------|----------------|
| `evidence_type` | Source of measurement | `self_report`, `staff_observed`, `administrative_record` |
| `measure_basis` | How measure was developed | `published_validated`, `published_adapted`, `custom_participatory` |
| `derivation_method` | How recorded value was produced | `direct_response`, `staff_rating`, `calculated_composite` |
| `iris_metric_code` | IRIS+ metric identifier (where applicable) | `PI2061` for employment metrics |
| `sdg_goals` | SDG goal numbers | `[8]` for employment, `[11]` for housing, `[3]` for mental health |

**Mapping rules:**
- PHQ-9, GAD-7, K10: `evidence_type=self_report`, `measure_basis=published_validated`, `derivation_method=direct_response`
- "How are you feeling today?", Self-Efficacy, etc.: `evidence_type=self_report`, `measure_basis=custom_participatory`, `derivation_method=direct_response`
- Hours Worked, Nights in Shelter: `evidence_type=self_report`, `measure_basis=custom_staff_designed`, `derivation_method=direct_response`
- Job Placement, Housing Secured: `evidence_type=staff_observed`, `measure_basis=custom_staff_designed`, `derivation_method=staff_rating`
- Inclusivity Battery: `evidence_type=self_report`, `measure_basis=published_adapted`, `derivation_method=direct_response`

### Program FHIR Fields

Populate during demo seeding:

| Program | `cids_sector_code` | `population_served_codes` | `default_goal_review_days` |
|---------|-------------------|--------------------------|---------------------------|
| Supported Employment | `6100` (Employment and training) | `["working_age_adults"]` | 90 |
| Housing Stability | `6200` (Housing) | `["working_age_adults", "at_risk_homelessness"]` | 90 |
| Youth Drop-In | `6300` (Social services — youth) | `["youth_13_18"]` | 60 |
| Newcomer Connections | `6400` (Social services — newcomers) | `["newcomers_immigrants"]` | 90 |
| Community Kitchen | `6500` (Social services — community) | `["general_community"]` | 30 |

### OrganizationProfile Seeding

Seed a realistic Canadian nonprofit profile:

```
legal_name: "Maple Community Services"
operating_name: "Maple Community Services"
description: "A multi-service community agency in Ontario providing employment support, housing stability, youth programming, newcomer settlement, and community kitchen services."
description_fr: "Un organisme communautaire multiservices en Ontario offrant du soutien à l'emploi, de la stabilité en logement, des programmes jeunesse, de l'établissement pour nouveaux arrivants et des cuisines communautaires."
legal_status: "Registered charity"
sector_codes: ["6100", "6200", "6300"]
street_address: "150 Main Street"
city: "Ottawa"
province: "ON"
postal_code: "K1A 0B1"
country: "CA"
website: "https://demo.konote.ca"
```

### TaxonomyMapping Seed Data

Create sample mappings for universal metrics:

| Metric | Taxonomy System | Code | Label |
|--------|----------------|------|-------|
| Goal Progress | `sdg` | `SDG-Target-1.4` | SDG 1: No Poverty |
| Self-Efficacy | `common_approach` | `CA-IND-001` | Individual Wellbeing |
| Job Placement | `iris_plus` | `PI2061` | Job Placement Rate |
| Job Placement | `sdg` | `SDG-8.5` | SDG 8: Decent Work |
| Housing Secured | `sdg` | `SDG-11.1` | SDG 11: Sustainable Cities |
| School Enrolment | `sdg` | `SDG-4.1` | SDG 4: Quality Education |

### CidsCodeList Seed Data

Seed the IRIS theme code list entries needed for the taxonomy mappings above, plus SDG goals 1-17 as a reference list.

---

## ServiceEpisode Lifecycle Data

### Active Episodes (majority)
- `status`: `active`
- `episode_type`: auto-derived (80% `new_intake`, 15% `re_enrolment`, 5% `transfer_in`)
- `referral_source`: distributed (30% `self`, 25% `agency_external`, 15% `healthcare`, 15% `community`, 15% mixed)
- `primary_worker`: assigned to Casey or Noor based on program
- `consent_to_aggregate_reporting`: `True` for all demo data
- `started_at`: backdated 1-8 months

### Finished Episodes (5-8 total across programs)
- `status`: `finished`
- `end_reason`: mix of `completed` (2), `goals_met` (2), `withdrew` (1-2), `lost_contact` (1)
- `ended_at`: 1-3 months ago
- These participants keep their notes and metric data for historical reporting

---

## PlanTarget Enrichment

- `achievement_status`: auto-computed from metric trends (already works via `save()` hook)
- `goal_source`: mix of `joint` (50%), `participant` (30%), `worker` (15%), `funder_required` (5%)
- `target_date`: set from `program.default_goal_review_days` offset from episode start
- `cids_outcome_uri`: left blank (populated per-funder, not appropriate for generic demo)

---

## Suggestion Themes

Seed 3-4 themes per program (15-20 total):

| Program | Theme | Priority | Status |
|---------|-------|----------|--------|
| Supported Employment | "More flexible scheduling for interviews" | important | open |
| Supported Employment | "Resume workshop follow-up" | noted | addressed |
| Housing Stability | "Faster landlord reference letters" | urgent | open |
| Housing Stability | "Budgeting workshop request" | noted | open |
| Youth Drop-In | "More weekend activities" | important | open |
| Youth Drop-In | "Homework help timing" | noted | addressed |
| Newcomer Connections | "Conversation circle frequency" | important | open |
| Newcomer Connections | "More translated materials" | noted | open |
| Community Kitchen | "Recipe books to take home" | noted | addressed |
| Community Kitchen | "Childcare during sessions" | important | open |
| Community Kitchen | "Allergen-free options" | noted | open |

Each theme linked to 3-8 participant suggestions via `SuggestionLink`.

---

## Permissions Matrix Compliance

### Role-Specific Demo Experience

| User | Role(s) | What They See | What They Don't See |
|------|---------|---------------|---------------------|
| **Casey Worker** | PM(Employment), Staff(Housing, Kitchen) | Full clinical access to Employment clients; program-scoped access to Housing/Kitchen; cross-enrolled clients visible in both programs | Newcomer/Youth data; Employment notes on Housing clients (PHIPA) |
| **Noor Worker** | Staff(Youth, Newcomer, Kitchen) | Program-scoped access to their 3 programs; group session logs for Youth/Kitchen | Employment/Housing data; management features |
| **Morgan Manager** | PM(Employment, Housing, Kitchen) | Insights, funder reports, suggestion themes for managed programs; clinical access (Tier 1-2) | Youth/Newcomer data; system admin |
| **Eva Executive** | Executive(all 5) | Dashboard aggregates across all programs; compliance summary | ANY individual client data, notes, plans |
| **Dana Front Desk** | Receptionist(all 5) | Client names, contact info, check-in | Notes, plans, metrics, clinical data |
| **Alex Admin** | Admin | System settings, user management, feature toggles, audit log | Client data (unless also has program role) |

### Cross-Program Visibility Demo

3+ clients cross-enrolled in Kitchen + their primary program demonstrate PHIPA consent filtering. When Casey views a cross-enrolled client's notes in Kitchen, they should not see that client's Employment notes (different program scope).

---

## Implementation Changes

### File: `seeds/metric_library.json`
- Add `evidence_type`, `measure_basis`, `derivation_method` to all metrics
- Add `iris_metric_code` to PHQ-9, GAD-7, K10, Job Placement
- Add `sdg_goals` to all metrics where applicable

### File: `apps/admin_settings/management/commands/generate_demo_data.py`
- Change default `--clients-per-program` from 3 to 20

### File: `apps/admin_settings/demo_engine.py`
- Add `_seed_organization_profile()` method
- Add `_seed_taxonomy_mappings()` method
- Add `_seed_cids_code_lists()` method
- Populate ServiceEpisode fields: `episode_type`, `referral_source`, `primary_worker`
- Create 5-8 finished episodes with `end_reason`
- Set `goal_source` on PlanTarget records
- Set `target_date` on PlanTarget records from program defaults
- Increase suggestion themes to 3-4 per program with `SuggestionLink` records
- Populate Program FHIR fields: `cids_sector_code`, `population_served_codes`, `default_goal_review_days`
- Use 30 clients for group programs (`service_model="group"`)

### File: `apps/admin_settings/management/commands/seed.py`
- Change default DEMO_MODE path to always use config-aware engine
- Pass `clients_per_program=20` (not the engine's default of 3)
- Fall back to hardcoded `seed_demo_data` only on engine failure

### File: `apps/admin_settings/management/commands/seed.py` (seed_metrics)
- Ensure new metric_library.json fields are persisted via `get_or_create` defaults and backfill logic

---

## Verification Checklist

After seeding, verify:

- [ ] Each program has 20+ active participants (30 for Community Kitchen)
- [ ] Insights page for each program shows: descriptor distribution, engagement distribution, metric distributions, achievement rates, suggestion themes, quotes
- [ ] Executive dashboard shows stats for all 5 programs (no privacy suppression)
- [ ] Funder report (CCF template) generates with demographic breakdowns and metrics
- [ ] Each demo user sees appropriate data per their role
- [ ] Casey cannot see Newcomer/Youth client data
- [ ] Eva cannot see any individual client records
- [ ] Dana cannot see notes, plans, or metrics
- [ ] MetricDefinition records have `evidence_type`, `measure_basis`, `derivation_method` populated
- [ ] OrganizationProfile exists with complete Canadian nonprofit data
- [ ] TaxonomyMapping records exist for universal metrics
- [ ] 5+ finished episodes exist with `end_reason` values
- [ ] Group programs have GroupSession records with attendance data
- [ ] Portal view for DEMO-001 (Jordan) shows progress charts and journal entries
