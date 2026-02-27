# Implementation Prompts: FHIR-Informed Data Foundations + CIDS Compliance

This file contains prompts for each session in the interleaved FHIR + CIDS implementation sequence. Paste the relevant session section into a new Claude Code conversation.

**Interleaved sequence overview** (from `tasks/fhir-informed-data-modelling.md`):

| Session | Steps | What | TODO IDs |
|---|---|---|---|
| **1** | F0 + CIDS 1 | Outcome Domain taxonomy + CIDS metadata fields + OrganizationProfile | FHIR-DOMAIN1 + CIDS-META1 + CIDS-ORG1 |
| **2** | CIDS 2 + 2.5 | Code list import + admin dropdowns + enriched CSV/PDF reports | CIDS-CODES1 + CIDS-ADMIN1 + CIDS-ENRICH1 |
| **3** | F1 | ServiceEpisode (extend ClientProgramEnrolment) + status history | FHIR-EPISODE1 + FHIR-MIGRATE1 |
| **4** | F2 + F3 | Goal achievement status + encounter participant role | FHIR-ACHIEVE1 + FHIR-ROLE1 |
| **5** | CIDS 3 + 4 + 5 | JSON-LD export + impact dimensions + conformance badge | CIDS-EXPORT1 + CIDS-IMPACT1 + CIDS-VALIDATE1 |

**Required reading for ALL sessions:**
- `tasks/design-rationale/fhir-informed-modelling.md` — anti-patterns and trade-offs. **DO NOT violate these.**
- `tasks/fhir-informed-data-modelling.md` — the full implementation plan
- `tasks/cids-json-ld-export.md` — CIDS implementation plan (validated against v3.2.0)
- `tasks/cids-plan-validation.md` — corrections applied to the CIDS plan

---

## Session 1: Unified Outcome Domain + CIDS Metadata Fields

**Steps:** F0 + CIDS Phase 1
**TODO IDs:** FHIR-DOMAIN1 + CIDS-META1 + CIDS-ORG1

### Before you start

1. Read the required files listed above (all four)
2. Read the current models:
   - `apps/plans/models.py` — MetricDefinition (has `category` field to replace) and PlanTarget
   - `apps/programs/models.py` — Program model
   - `apps/admin_settings/models.py` — existing TerminologyOverride/FeatureToggle/InstanceSetting patterns
   - `apps/clients/models.py` — ClientProgramEnrolment (for context — not changed in this session)

### Key design decisions (from DRR)

- **Borrow FHIR concepts without FHIR compliance.** Plain Django models, no FHIR server/API/validation.
- **DO NOT use FHIR CodeableConcept wrapper structures.** Use CharField with choices.
- **Unified domain taxonomy** serves three purposes: internal reporting, FHIR-informed tracking, and CIDS export.
- **CIDS Theme is derived at export time** via three-tier approach (not stored as a separate field):
  1. `iris_metric_code` → CidsCodeList lookup → parent IRIS Impact Theme (precise)
  2. `outcome_domain` → default mapping table (fallback)
  3. `cids_theme_override` (admin correction for edge cases)
- **`cids_impact_theme` on PlanTarget was removed** — derived from the target's metric's theme at export time.

### What to build

#### 1. Outcome Domain taxonomy on MetricDefinition (Phase F0)

Replace the existing `category` CharField (7 values) with `outcome_domain` CharField (14 values).

**Outcome Domain choices:**

| Code | Display (EN) | Display (FR) | Maps from old `category` |
|---|---|---|---|
| `housing` | Housing & Shelter | Logement et hébergement | `housing` |
| `employment` | Employment & Income | Emploi et revenu | `employment` |
| `mental_health` | Mental Health & Wellbeing | Santé mentale et bien-être | `mental_health` |
| `substance_use` | Substance Use | Consommation de substances | `substance_use` |
| `food_security` | Food Security | Sécurité alimentaire | — |
| `education` | Education & Training | Éducation et formation | — |
| `social_connection` | Social Connection | Liens sociaux | — |
| `financial` | Financial Stability | Stabilité financière | — |
| `safety` | Safety & Protection | Sécurité et protection | — |
| `youth` | Youth Development | Développement des jeunes | `youth` |
| `transportation` | Transportation | Transport | — |
| `legal` | Legal & Justice | Justice et droit | — |
| `health` | Physical Health | Santé physique | — |
| `custom` | Other | Autre | `custom`, `general` |

**Data migration:** Map old values to new. The value `general` maps to `custom` for now (flag for manual review).

#### 2. Outcome Domain on Program and PlanTarget (Phase F0)

**On Program:** Add `outcome_domain` (CharField, max_length=30, blank=True). What domain does this program primarily serve? Can be auto-derived from the program's most common metric domains if not set.

**On PlanTarget:** Add `outcome_domain` (CharField, max_length=30, blank=True). Inherited from the plan section's program domain or from the target's metrics. Can be overridden.

#### 3. CIDS metadata fields on MetricDefinition (CIDS Phase 1b)

| Field | Type | CIDS Property | Notes |
|---|---|---|---|
| `cids_indicator_uri` | CharField(max_length=500, blank=True) | `@id` | CIDS identifier. CharField not URLField — URIs may use `urn:` schemes. |
| `iris_metric_code` | CharField(max_length=50, blank=True) | `cids:hasCode` | From IrisMetric53 code list (e.g., "PI2061") |
| `sdg_goals` | JSONField(default=list) | `cids:hasCode` | List of SDG numbers 1-17 (e.g., [1, 11]) |
| `cids_unit_description` | CharField(max_length=100, blank=True) | `cids:unitDescription` | Human-readable unit label (e.g., "score", "percentage") |
| `cids_defined_by` | CharField(max_length=500, blank=True) | `cids:definedBy` | URI of defining organisation (e.g., GIIN for IRIS+). Required at EssentialTier. |
| `cids_has_baseline` | CharField(max_length=200, blank=True) | `cids:hasBaseline` | Human-readable baseline description (e.g., "Average score 3.2 at intake"). Required at EssentialTier. |
| `cids_theme_override` | CharField(max_length=50, blank=True) | — | Admin escape hatch for three-tier theme derivation. Only used when auto-derived theme is wrong. |

#### 4. CIDS metadata fields on Program (CIDS Phase 1c)

| Field | Type | CIDS Property | Notes |
|---|---|---|---|
| `cids_sector_code` | CharField(max_length=50, blank=True) | `cids:hasCode` | From ICNPOsector or ESDCSector |
| `population_served_codes` | JSONField(default=list) | `cids:hasCode` | From PopulationServed code list |
| `description_fr` | TextField(blank=True) | — | French description. Currently missing from Program. Needed for bilingual CIDS exports. |
| `funder_program_code` | CharField(max_length=100, blank=True) | — | Funder-assigned ID for cross-referencing |

#### 5. CIDS metadata field on PlanTarget (CIDS Phase 1d)

| Field | Type | CIDS Property | Notes |
|---|---|---|---|
| `cids_outcome_uri` | CharField(max_length=500, blank=True) | `@id` | CIDS outcome identifier. CharField not URLField. |

**Do NOT add `cids_impact_theme`** — it was removed in favour of three-tier derivation at export time.

#### 6. New model: OrganizationProfile (CIDS Phase 1a)

Stores CIDS BasicTier org metadata. Singleton — one row per agency instance.

**Where it lives:** `apps/admin_settings/models.py` (alongside existing TerminologyOverride / FeatureToggle / InstanceSetting)

| Field | Type | CIDS Property | Notes |
|---|---|---|---|
| `legal_name` | CharField(max_length=255, blank=True) | `org:hasLegalName` | Required for BasicTier |
| `operating_name` | CharField(max_length=255, blank=True) | `org:hasName` | Display name |
| `description` | TextField(blank=True) | `cids:hasDescription` | Mission statement |
| `description_fr` | TextField(blank=True) | — | French description |
| `legal_status` | CharField(max_length=50, blank=True) | `org:hasLegalStatus` | Charity, nonprofit, etc. |
| `sector_codes` | JSONField(default=list) | `cids:hasCode` | From ICNPOsector code list |
| `street_address` | CharField(max_length=255, blank=True) | `cids:streetAddress` | Required for CIDS Address |
| `city` | CharField(max_length=100, blank=True) | `cids:addressLocality` | Required for CIDS Address |
| `province` | CharField(max_length=10, blank=True) | `cids:addressRegion` | From ProvinceTerritory code list |
| `postal_code` | CharField(max_length=10, blank=True) | `cids:postalCode` | Required for CIDS Address |
| `country` | CharField(max_length=10, default="CA") | `cids:addressCountry` | Default "CA" |
| `website` | URLField(blank=True) | `sch:url` | |

**Singleton pattern:** Follow the InstanceSetting pattern (class method to get-or-create the single row). No external dependency needed.

### Rules

- Create `forms.py` entries for any admin-facing forms (Django ModelForm, never raw POST)
- Write tests for the data migration logic (old `category` → new `outcome_domain`) and new fields
- Run `makemigrations` and `migrate`, commit migration files
- Run translations: `python manage.py translate_strings` after any template changes
- All new fields must be `blank=True` or have defaults — no data loss on migration
- Follow the project's existing patterns — check how other CharFields with choices are done
- Update the admin settings form if OrganizationProfile needs UI (collapsible section)

### What NOT to build yet

- ServiceEpisode (Phase F1 — Session 3)
- Achievement status (Phase F2 — Session 4)
- Author role (Phase F3 — Session 4)
- CidsCodeList import (CIDS Phase 2 — Session 2)
- Admin UI dropdowns for CIDS codes (CIDS Phase 2 — Session 2)
- JSON-LD export (CIDS Phase 3 — Session 5)

### When done

- Mark these TODO.md tasks as done: FHIR-DOMAIN1 + CIDS-META1 + CIDS-ORG1
- Run relevant tests: `pytest tests/test_plans.py tests/test_clients.py tests/test_programs.py`
- Create a PR to merge into main

---

## Session 2: CIDS Code Lists + Enriched Reports

**Steps:** CIDS Phase 2 + CIDS Phase 2.5
**TODO IDs:** CIDS-CODES1 + CIDS-ADMIN1 + CIDS-ENRICH1
**Depends on:** Session 1 complete

### Before you start

1. Read the required files listed at the top
2. Read `apps/admin_settings/models.py` — OrganizationProfile from Session 1
3. Read `apps/plans/models.py` — MetricDefinition with new CIDS fields from Session 1
4. Read `apps/reports/funder_report.py` and `apps/reports/export_engine.py` — existing report generation
5. Read `apps/reports/models.py` — ReportTemplate, ReportMetric, SecureExportLink

### What to build

#### 1. CidsCodeList model (CIDS Phase 2a)

New model in `apps/admin_settings/models.py` (or a new `apps/cids/models.py` if the file is getting large).

| Field | Type | CIDS Property | Notes |
|---|---|---|---|
| `list_name` | CharField(max_length=100) | — | e.g., "ICNPOsector", "SDGImpacts", "IrisMetric53" |
| `code` | CharField(max_length=100) | `sch:codeValue` | The code value (e.g., "ICNPO-4", "SDG-11", "PI2061") |
| `label` | CharField(max_length=255) | `org:hasName` | Display label (English) |
| `label_fr` | CharField(max_length=255, blank=True) | — | French label |
| `description` | TextField(blank=True) | `cids:hasDescription` | Longer description |
| `specification_uri` | CharField(max_length=500, blank=True) | `cids:hasSpecification` | URI of code list spec |
| `defined_by_name` | CharField(max_length=255, blank=True) | `cids:definedBy` → `org:hasLegalName` | Organisation name (e.g., "GIIN") |
| `defined_by_uri` | CharField(max_length=500, blank=True) | `cids:definedBy` → `@id` | URI of defining organisation |
| `source_url` | URLField(blank=True) | — | Link to Common Approach code list page |
| `version_date` | DateField(blank=True, null=True) | — | For staleness warnings |

**Indexes:** `unique_together = [("list_name", "code")]`

**Why the extra fields:** CIDS SHACL EssentialTier requires Code objects with `hasName`, `hasDescription`, `codeValue`, `definedBy`, and `hasSpecification`. The JSON-LD export (Session 5) needs these to construct full Code objects.

#### 2. Management command: `import_cids_codelists` (CIDS Phase 2)

Fetches from `codelist.commonapproach.org` and populates the CidsCodeList table. Available formats: JSON-LD, CSV, Turtle, RDF/XML. CSV is simplest.

- Import all 17 lists but prioritise #1-10 (see `tasks/cids-plan-validation.md` for the full list with relevance ratings)
- Warn when local copy is stale (compare `version_date` to current date)
- Idempotent — safe to re-run
- Run once during setup, re-run to update

#### 3. Admin UI for CIDS tagging (CIDS Phase 2b)

- Add CIDS fields to the existing MetricDefinition admin form in a collapsible "Funder Reporting" section
- Add CIDS fields to the existing Program admin form in a collapsible "Funder Reporting" section
- Use select2-style dropdowns (or standard `<select>`) populated from `CidsCodeList` filtered by `list_name`
- PlanTarget CIDS fields can be set via plan templates (auto-apply to client targets)
- Integrate into config template system — e.g., a funder config template pre-maps CIDS codes for standard metrics

#### 4. CIDS-enriched CSV/PDF reports (CIDS Phase 2.5)

**This is the quick win for funders.** No JSON-LD, no ServiceEpisode needed — just enrich existing reports.

- Add IRIS+ metric codes next to indicator names in CSV/PDF exports (e.g., "Housing Stability (IRIS+ PI2061)")
- Add SDG goal references to outcome sections
- Add a **"Standards Alignment" appendix page** to PDF funder reports:

  > **Standards Alignment**
  > This report uses the Common Impact Data Standard (CIDS) v3.2
  > - Organisation: [Legal Name] — [Province]
  > - Sector: Social Services (ICNPO-4)
  > - SDG Alignment: SDG 1 (No Poverty), SDG 11 (Sustainable Cities)
  > - Outcome indicators mapped to IRIS+ metrics
  > - Code lists sourced from codelist.commonapproach.org (version: [date])

- **Graceful degradation:** If no CIDS codes are configured, reports look exactly the same as today
- Modify `generate_funder_report_csv_rows()` to include CIDS codes when available
- Modify funder report PDF template to add Standards Alignment appendix

### Rules

- Same rules as Session 1 (forms, tests, migrations, translations)
- The code list import command should handle network errors gracefully (warn, don't crash)
- Test that reports with no CIDS codes configured are unchanged

### What NOT to build yet

- JSON-LD export format (CIDS Phase 3 — Session 5)
- ServiceEpisode (Phase F1 — Session 3)
- SHACL validation (CIDS Phase 3 — Session 5)

### When done

- Mark TODO.md tasks: CIDS-CODES1 + CIDS-ADMIN1 + CIDS-ENRICH1
- Run relevant tests: `pytest tests/test_plans.py tests/test_exports.py`
- Create a PR to merge into main

---

## Session 3: ServiceEpisode

**Steps:** Phase F1
**TODO IDs:** FHIR-EPISODE1 + FHIR-MIGRATE1
**Depends on:** Session 1 complete (needs outcome_domain). Sessions 2 is independent.

### Before you start

1. Read the required files listed at the top (especially the DRR anti-patterns)
2. Read `apps/clients/models.py` — ClientProgramEnrolment (the class to extend)
3. Read all views/templates that reference `ClientProgramEnrolment` — the class alias means these won't break, but understand the surface area
4. Read `tasks/fhir-informed-data-modelling.md` Phase F1 for full field specs

### Key design decisions (from DRR)

- **Extend in place** — rename class to ServiceEpisode, keep `db_table`, add `ClientProgramEnrolment = ServiceEpisode` alias. All existing imports and queries continue working unchanged.
- **Use Django `RenameModel` migration** — NOT a new model pointing at the same table.
- **Episode type is auto-derived** from episode history, NOT worker-entered.
- **Discharge reason is the one new question workers answer** — radio buttons, not optional text.
- **DO NOT build Care Team** — `primary_worker` on ServiceEpisode covers the 80% case.
- **DO NOT let workers select episode type** — the system knows this better than the worker.

### What to build

#### 1. Rename ClientProgramEnrolment → ServiceEpisode (in place)

```python
# In apps/clients/models.py
class ServiceEpisode(models.Model):
    class Meta:
        db_table = "clients_clientprogramenrolment"  # Keep existing table
    # ... existing fields + new fields ...

# Backwards compatibility alias
ClientProgramEnrolment = ServiceEpisode
```

Migration uses `RenameModel`:
```python
operations = [
    migrations.RenameModel(
        old_name="ClientProgramEnrolment",
        new_name="ServiceEpisode",
    ),
    # Then AddField for each new field...
]
```

#### 2. New fields on ServiceEpisode

| Field | Type | Notes |
|---|---|---|
| `status` | CharField(max_length=20) | Replace old 2-value choices with 6-value: planned, waitlist, active, on_hold, finished, cancelled |
| `status_reason` | TextField(blank=True) | Why the status changed |
| `episode_type` | CharField(max_length=20, blank=True) | Auto-derived: new_intake, re_enrolment, transfer_in, crisis, short_term |
| `primary_worker` | FK to User(null=True, blank=True, on_delete=SET_NULL) | Assigned case worker |
| `referral_source` | CharField(max_length=30, blank=True) | Choices: self, family, agency_internal, agency_external, healthcare, school, court, shelter, community, other |
| `started_at` | DateTimeField(null=True, blank=True) | When active service began |
| `ended_at` | DateTimeField(null=True, blank=True) | When service ended |
| `end_reason` | CharField(max_length=30, blank=True) | Choices: completed, goals_met, withdrew, transferred, referred_out, lost_contact, moved, ineligible, deceased, other |

See `tasks/fhir-informed-data-modelling.md` Phase F1 for the full choice tables with display labels and FHIR equivalents.

#### 3. New model: ServiceEpisodeStatusChange

Append-only status history for reporting.

| Field | Type | Notes |
|---|---|---|
| `episode` | FK to ServiceEpisode(on_delete=CASCADE) | |
| `status` | CharField(max_length=20) | The new status |
| `reason` | TextField(blank=True) | Why |
| `changed_by` | FK to User(null=True, on_delete=SET_NULL) | |
| `changed_at` | DateTimeField(auto_now_add=True) | |

**Index:** `(episode, changed_at)` for chronological queries.

**Write pattern:** Every time `ServiceEpisode.status` changes, append a row. Use model `save()` with dirty-field tracking or `post_save` signal.

#### 4. Data migration (in-place)

No data copying — just populate new fields on existing rows:
- `started_at` = `enrolled_at`
- New `status`: `"active"` if old status was `"enrolled"`, else `"finished"`
- `ended_at` = `unenrolled_at` (if set)
- `episode_type`, `end_reason`, `referral_source` — leave blank for historical data
- Create initial `ServiceEpisodeStatusChange` for each row

#### 5. UI changes (minimal)

- **Discharge modal:** Replace simple status toggle with "Why is this person leaving?" radio buttons (`end_reason` choices) + optional text for `status_reason`. System sets status to `finished`, records `ended_at`.
- **Transfer workflow:** Finish episode A with `end_reason='transferred'`, create episode B with auto-derived `episode_type='transfer_in'`.
- **On Hold / Resume:** New actions on client profile. "Put on hold" asks for reason. "Resume service" sets back to `active`.
- **Episode type auto-derivation:** On episode creation, check for prior episodes in same program. No prior → `new_intake`. Prior finished → `re_enrolment`. Prior transferred from another program → `transfer_in`.

### Rules

- Same rules as Sessions 1-2
- **Dry-run migrations on test database** before applying — this is a model rename
- Verify the `ClientProgramEnrolment` alias works in all existing imports
- Write tests for: status transitions, episode type auto-derivation, discharge modal, data migration

### What NOT to build yet

- Achievement status (Phase F2 — Session 4)
- Care Team (deferred — see DRR)
- Presenting Issues (Phase F4 — deferred until a funder asks)
- Service Referrals (Phase F5 — deferred until multi-agency phase)

### When done

- Mark TODO.md tasks: FHIR-EPISODE1 + FHIR-MIGRATE1
- Run relevant tests: `pytest tests/test_clients.py tests/test_plans.py`
- Create a PR to merge into main

---

## Session 4: Goal Achievement Status + Encounter Role

**Steps:** Phase F2 + Phase F3
**TODO IDs:** FHIR-ACHIEVE1 + FHIR-ROLE1
**Depends on:** Session 1 complete (needs outcome_domain)

### Before you start

1. Read the required files listed at the top
2. Read `apps/plans/models.py` — PlanTarget (adding achievement fields)
3. Read `apps/notes/models.py` — ProgressNote (adding author_role), ProgressNoteTarget (has `progress_descriptor`), MetricValue
4. Read `tasks/fhir-informed-data-modelling.md` Phases F2 and F3 for full specs

### Key design decisions (from DRR)

- **Achievement status is derived, not entered.** Zero new data entry for frontline staff.
- **Separate lifecycle from achievement.** `status` (active/completed/deactivated) answers "Is this goal still being worked on?" — `achievement_status` answers "How is the client doing?"
- **Auto-compute with worker override.** "(auto)" badge on plan view. Worker can click to override.
- **`not_attainable` is NEVER auto-computed.** Always a deliberate worker/PM decision.
- **Author role is auto-filled** from UserProgramRole at note creation time. Workers never see or select this field.
- **DO NOT ask workers to select their role when writing a note.**

### What to build

#### 1. New fields on PlanTarget (Phase F2)

| Field | Type | Notes |
|---|---|---|
| `achievement_status` | CharField(max_length=20, blank=True) | Derived or worker-assessed |
| `achievement_status_source` | CharField(max_length=20, blank=True) | `auto_computed` or `worker_assessed` |
| `achievement_status_updated_at` | DateTimeField(null=True) | When last computed/assessed |
| `first_achieved_at` | DateTimeField(null=True, blank=True) | When achievement_status first became `achieved`. Never cleared once set. Enables time-to-achievement reporting. |

**Achievement status choices:**

| Value | Display (EN) | Display (FR) | Meaning |
|---|---|---|---|
| `in_progress` | In progress | En cours | Working toward goal, no clear trend yet |
| `improving` | Improving | En amélioration | Positive trajectory (2 of last 3 points improve) |
| `worsening` | Worsening | En détérioration | Negative trajectory |
| `no_change` | No change | Aucun changement | Stable |
| `achieved` | Achieved | Atteint | Target reached |
| `sustaining` | Sustaining | Maintenu | Maintaining gains after achieving |
| `not_achieved` | Not achieved | Non atteint | Goal concluded without reaching target |
| `not_attainable` | Not attainable | Non réalisable | Goal needs revision — NEVER auto-computed |

#### 2. Achievement derivation logic

**Quantitative goals (MetricValues exist):** Compute from the last 3 recorded MetricValues for the primary metric.

| Data Points | Behaviour |
|---|---|
| 0 | `in_progress` — no data |
| 1 | `in_progress` unless the single point meets target → `achieved` |
| 2 | Compare: improving if 2nd better, worsening if worse, no_change if equal |
| 3+ | 2 of last 3 show improvement → `improving`; 2 of 3 decline → `worsening`; mixed → `no_change` |

Target met → `achieved`. Previously achieved + still met → `sustaining`. Previously achieved + dropped below → `worsening`.

**Qualitative goals (progress_descriptor only):**

| progress_descriptor | achievement_status |
|---|---|
| `harder` | `worsening` |
| `holding` | `no_change` |
| `shifting` | `improving` |
| `good_place` | `achieved` (first time) or `sustaining` (if previously achieved) |

**Fallback:** No metrics and no descriptor → `in_progress`.

**Computation trigger:** Recalculate when a ProgressNote is saved that includes a ProgressNoteTarget for this goal. Store on PlanTarget for direct query.

**Worker override:** Show on plan view with "(auto)" badge. Worker clicks to override → sets `achievement_status_source = "worker_assessed"`. Next auto-computation only overwrites if source is `auto_computed`.

#### 3. New field on ProgressNote (Phase F3)

| Field | Type | Notes |
|---|---|---|
| `author_role` | CharField(max_length=30, blank=True) | Auto-filled from UserProgramRole |

**Auto-fill logic:** On ProgressNote creation, look up the author's UserProgramRole for `author_program` and store the role value (receptionist, staff, program_manager, executive). Captures role-at-time-of-service.

**No UI change.** The worker never sees or selects this field.

### Rules

- Same rules as previous sessions
- Test sparse data edge cases (0, 1, 2, 3+ data points)
- Test that `not_attainable` is never auto-set
- Test worker override persists across auto-computations
- Test author_role auto-fill with multiple roles across programs

### When done

- Mark TODO.md tasks: FHIR-ACHIEVE1 + FHIR-ROLE1
- Run relevant tests: `pytest tests/test_plans.py tests/test_notes.py`
- Create a PR to merge into main

---

## Session 5: CIDS JSON-LD Export + Impact Dimensions + Conformance

**Steps:** CIDS Phase 3 + Phase 4 + Phase 5
**TODO IDs:** CIDS-EXPORT1 + CIDS-IMPACT1 + CIDS-VALIDATE1
**Depends on:** Sessions 1-4 complete (benefits from all FHIR work)

### Before you start

1. Read the required files listed at the top
2. Read `tasks/cids-json-ld-export.md` Phases 3-5 in detail — includes full JSON-LD examples for BasicTier, EssentialTier, and FullTier
3. Read `tasks/cids-plan-validation.md` — the SHACL field requirements tables are essential
4. Read `apps/reports/funder_report.py` — `generate_funder_report_data()` is the data source
5. Read `apps/reports/aggregations.py` — `metric_stats()` for ImpactScale/ImpactDepth computation
6. Read `apps/reports/models.py` — SecureExportLink for download security

### Key design decisions

- **Aggregate only — no PII.** JSON-LD exports contain organisation/program/outcome data, never individual client records.
- **Use official cidsContext.jsonld** as `@context` — avoids namespace errors.
- **PHIPA consent filtering applies** to CIDS export (per the phipa-consent-enforcement DRR).
- **Basic SHACL validation before export** using `pyshacl` — pass/fail check, warn user if non-compliant.
- **Target FullTier directly.** BasicTier validation is an internal milestone, not a separate deliverable.
- **BeneficialStakeholder = program cohort** (group), NOT individual ClientFile.
- **StakeholderOutcome is constructed at export time** from Program cohort + PlanTarget — no new database model needed.

### What to build

#### 1. JSON-LD export (CIDS Phase 3)

- New file: `apps/reports/cids_export.py` — builds the JSON-LD structure from existing data
- New format option in `FunderReportForm`: `("jsonld", _("JSON-LD (CIDS standard)"))`
- Reuse existing `generate_funder_report_data()` as the data source
- Add CIDS metadata from model fields (from Sessions 1-2)
- Every entity includes an `@id` for graph interoperability
- Use `"@context": "https://ontology.commonapproach.org/contexts/cidsContext.jsonld"`
- Construct full Code objects from CidsCodeList rows (6 required SHACL fields)
- Construct StakeholderOutcome at export time (junction of Stakeholder + Outcome)
- Measurement values use nested `i72:Measure` objects: `{"@type": "i72:Measure", "i72:hasNumericalValue": "7.8"}` — note `hasNumericalValue` is xsd:string, not number
- Secure export link works same as CSV/PDF — no new security model
- **Note:** `oep:partOf` (required at FullTier) is not in the official JSON-LD context. Extend context inline: `"oep": "http://www.w3.org/2001/sw/BestPractices/OEP/SimplePartWhole/part.owl#"`

See the full JSON-LD examples in `tasks/cids-json-ld-export.md` (BasicTier, EssentialTier, FullTier) for exact structure.

#### 2. Basic SHACL validation (CIDS Phase 3c)

- Add `pyshacl` to requirements
- Validate JSON-LD against BasicTier SHACL shapes before export
- Pass/fail check — warn user if non-compliant, but still allow export
- Graduate to EssentialTier and FullTier validation as metadata coverage increases

SHACL shape files: `cids.basictier.shacl.ttl`, `cids.essentialtier.shacl.ttl`, `cids.fulltier.shacl.ttl` from the CIDS GitHub repo.

#### 3. Impact dimensions (CIDS Phase 4)

Computed from existing KoNote data — no new data entry.

| CIDS Dimension | Tier | Computation |
|---|---|---|
| **ImpactScale** (how many) | EssentialTier | Count of clients with MetricValues for this target during reporting period |
| **ImpactDepth** (degree of change) | EssentialTier | Achievement rate — % of clients with `achievement_status` in [`achieved`, `sustaining`]. Enriched by Session 4 work. |
| **ImpactDuration** (how long) | EssentialTier | Reporting period (`prov:startedAtTime` / `prov:endedAtTime`). Enhanced: % who maintained achievement for 6+ consecutive months (using `first_achieved_at`). |

Each dimension requires: `i72:value` (nested `i72:Measure`), `cids:hasDescription` (human-readable), `cids:forIndicator` (link to the Indicator).

#### 4. Conformance badge (CIDS Phase 5)

- Detailed SHACL error reporting (not just pass/fail)
- Display a "CIDS Conformance" badge on exports that pass validation
- Conformance level indicator: BasicTier / EssentialTier / FullTier
- Optionally submit to Common Approach's validator (if one exists)

### Rules

- Same rules as previous sessions
- Add `pyshacl` as a dependency (needed for SHACL validation)
- Test JSON-LD output against BasicTier SHACL shapes
- Test that no PII leaks into JSON-LD export (encrypted fields must not appear)
- Test graceful degradation: export with no CIDS codes configured should still produce valid JSON-LD structure
- Test PHIPA consent filtering applies to CIDS exports

### When done

- Mark TODO.md tasks: CIDS-EXPORT1 + CIDS-IMPACT1 + CIDS-VALIDATE1
- Run relevant tests: `pytest tests/test_exports.py tests/test_plans.py`
- Create a PR to merge into main

---

## Deferred work (build when triggered)

These phases are documented in `tasks/fhir-informed-data-modelling.md` but not scheduled:

- **F4: Presenting Issues** (computed view, no model) — build when a funder asks "outcomes by presenting issue"
- **F5: Service Referrals** — build at multi-agency phase
- **F6: Care Team** — build at multi-agency phase
- **Circles FHIR codes** (RelationshipType) — see `tasks/design-rationale/circles-family-entity.md` Level 4
