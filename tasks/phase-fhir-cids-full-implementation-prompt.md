# Full Implementation Prompt: FHIR-Informed Data Foundations + CIDS Compliance

**Purpose:** Paste this entire prompt into a single Claude Code session. It will execute all 5 phases of the FHIR+CIDS implementation plan using parallel agents where possible.

**Estimated scope:** ~15 new model fields across 3 existing models, 2 new models, 1 new singleton model, 1 management command, 1 new model for taxonomy mapping, ServiceEpisode model refactor with data migration, achievement status derivation engine, JSON-LD export with SHACL validation, and supporting UI/test/translation work.

**Prerequisites:** PR #125 (taxonomy panel revisions) must be merged before starting. That PR updates the implementation plan, phase prompts, design rationale, and TODO.md.

---

## Prompt

I need you to implement the full FHIR-Informed Data Foundations + CIDS Compliance plan for KoNote. This is the entire interleaved 5-session sequence from `tasks/fhir-informed-data-modelling.md`. Use agents to parallelise independent work within each session. Each session must complete (PR merged to main) before the next begins.

### Step 0: Read all planning documents

**Before writing any code**, read these files in order — they contain anti-patterns, field specs, corrections, and design decisions that constrain what you can build:

1. `tasks/fhir-informed-data-modelling.md` — master implementation plan. Key sections: Phase F0 (REMOVED — understand why), Phase F1 (ServiceEpisode), Phase F2 (achievement status), Phase F3 (author_role), sequencing table, risk assessment.
2. `tasks/design-rationale/fhir-informed-modelling.md` — anti-patterns and trade-offs. **Critical:** read every anti-pattern before building anything. Especially:
   - DO NOT hardcode an internal outcome taxonomy (taxonomy panel, 4 experts, unanimous)
   - DO NOT implement a FHIR server or FHIR RESTful API
   - DO NOT use FHIR CodeableConcept wrapper structures
   - DO NOT let workers select episode type (auto-derive from history)
   - DO NOT ask workers to select their role when writing a note (auto-fill)
   - DO NOT add presenting issues as a mandatory intake field
   - DO NOT build Care Team before multi-agency phase
3. `tasks/cids-json-ld-export.md` — CIDS implementation plan. Phase 1 field specs (1a–1d), Phase 2 (CidsCodeList, management command), Phase 2.5 (enriched reports), Phase 3 (JSON-LD export), Phase 4 (impact dimensions), Phase 5 (conformance badge).
4. `tasks/cids-plan-validation.md` — 5 corrections required + 6 Phase 3 implementation notes. Namespace URIs, SHACL field requirements, StakeholderOutcome construction, BeneficialStakeholder = group not individual.
5. `tasks/phase-fhir-cids-prompt.md` — per-session prompts with field tables. **This is the source of truth for field specs** — it supersedes the CIDS plan where they conflict (specifically: `cids_theme` and `cids_impact_theme` are removed).
6. `CLAUDE.md` — project conventions, development rules, consultation gates, git workflow.

### Step 0b: Read the current models

These are the models you'll be modifying. Read them to understand current structure, patterns, and conventions:

- `apps/plans/models.py` — **MetricDefinition** (has `category` CharField with 7 choices: mental_health, housing, employment, substance_use, youth, general, custom — DO NOT change this field), **PlanTarget** (has encrypted fields via property accessors, status: default/completed/deactivated)
- `apps/notes/models.py` — **ProgressNote** (has `author`, `author_program` FKs), **ProgressNoteTarget** (has `progress_descriptor`: harder/holding/shifting/good_place)
- `apps/clients/models.py` — **ClientProgramEnrolment** (current status choices: enrolled/unenrolled; fields: client_file FK, program FK, status, enrolled_at auto_now_add, unenrolled_at nullable). **112 files reference this model** — the extend-in-place strategy with class alias is critical.
- `apps/programs/models.py` — **Program** (name, description, colour_hex, service_model, status, is_confidential), **UserProgramRole** (role choices: receptionist/staff/program_manager/executive)
- `apps/admin_settings/models.py` — **InstanceSetting** (key-value singleton pattern with `get(key, default)` and `get_all()` class methods), **FeatureToggle**, **TerminologyOverride**. Follow InstanceSetting's pattern for OrganizationProfile singleton.

### Global rules (apply to ALL sessions)

1. **Git workflow:** Create a feature branch for each session (`feat/cids-session-1`, `feat/cids-session-2`, etc.). Never commit to main. Push and create PR when done. Merge PRs with `--merge` (never squash).
2. **Pull main** before starting each session: `git pull origin main`
3. **forms.py:** Use Django ModelForm for all admin-facing forms. Never use raw `request.POST.get()`.
4. **Tests:** Write tests for every new model, field, migration, and view. Run relevant tests after each change.
5. **Migrations:** Run `makemigrations` and `migrate` after every model change. Commit migration files.
6. **Translations:** Run `python manage.py translate_strings` after template changes. Fill French translations. Commit .po and .mo files.
7. **All new fields** must be `blank=True` or have defaults — no data loss on migration.
8. **DO NOT add `outcome_domain`** to any model. It was explicitly removed by the taxonomy panel. `MetricDefinition.category` stays unchanged.
9. **Commit after each edit** — never leave changes uncommitted across tool calls.
10. **GK review gates:** Flag PRs for GK review when they touch outcome models (MetricDefinition, PlanTarget), data model structure (ServiceEpisode), or methodology (achievement_status derivation). Add "GK reviews: [what]" to PR description.

---

## Session 1: CIDS Phase 1 — Metadata Fields + OrganizationProfile

**Branch:** `feat/cids-session-1`
**TODO tasks:** CIDS-META1 + CIDS-ORG1
**GK review:** Yes — CIDS metadata field selection

### What to build

Three independent pieces — **use agents to build these in parallel:**

#### Agent 1: MetricDefinition + PlanTarget CIDS fields

Add to **MetricDefinition** (`apps/plans/models.py`):

| Field | Type | Notes |
|---|---|---|
| `cids_indicator_uri` | CharField(max_length=500, blank=True) | CIDS `@id` — CharField not URLField (URIs may use `urn:` schemes) |
| `iris_metric_code` | CharField(max_length=100, blank=True) | From IrisMetric53 code list (e.g., "PI2061") |
| `sdg_goals` | JSONField(default=list, blank=True) | List of SDG numbers [1–17] |
| `cids_unit_description` | CharField(max_length=255, blank=True) | Human-readable unit label (maps to `cids:unitDescription`) |
| `cids_defined_by` | CharField(max_length=500, blank=True) | URI of defining organisation (e.g., GIIN for IRIS+ metrics) |
| `cids_has_baseline` | CharField(max_length=255, blank=True) | **CharField, NOT BooleanField** — stores human-readable baseline like "Average score 3.2 at intake" |
| `cids_theme_override` | CharField(max_length=50, blank=True) | Admin escape hatch for CIDS theme derivation when auto-derivation is wrong |

Add to **PlanTarget** (`apps/plans/models.py`):

| Field | Type | Notes |
|---|---|---|
| `cids_outcome_uri` | CharField(max_length=500, blank=True) | CIDS outcome `@id` |

**DO NOT** add `cids_impact_theme` — removed by taxonomy panel.
**DO NOT** change `MetricDefinition.category` — leave completely untouched.

Write tests for: new field defaults, blank values, JSONField serialisation for sdg_goals.

#### Agent 2: Program CIDS fields

Add to **Program** (`apps/programs/models.py`):

| Field | Type | Notes |
|---|---|---|
| `cids_sector_code` | CharField(max_length=100, blank=True) | From ICNPOsector or ESDCSector code list |
| `population_served_codes` | JSONField(default=list, blank=True) | From PopulationServed code list |
| `description_fr` | TextField(blank=True) | French description for bilingual CIDS exports |
| `funder_program_code` | CharField(max_length=100, blank=True) | Funder-assigned program ID |

Write tests for: new field defaults, JSONField serialisation.

#### Agent 3: OrganizationProfile singleton

Create **OrganizationProfile** in `apps/admin_settings/models.py` (alongside InstanceSetting):

| Field | Type | Notes |
|---|---|---|
| `legal_name` | CharField(max_length=255, blank=True) | Required for CIDS BasicTier (`org:hasLegalName`) |
| `operating_name` | CharField(max_length=255, blank=True) | Display name |
| `description` | TextField(blank=True) | Mission statement |
| `description_fr` | TextField(blank=True) | French mission statement |
| `legal_status` | CharField(max_length=100, blank=True) | Charity, nonprofit, etc. |
| `sector_codes` | JSONField(default=list, blank=True) | ICNPOsector codes — **JSONField not CharField** |
| `street_address` | CharField(max_length=255, blank=True) | |
| `city` | CharField(max_length=100, blank=True) | |
| `province` | CharField(max_length=2, blank=True) | Two-letter province code (ON, QC, BC, etc.) |
| `postal_code` | CharField(max_length=10, blank=True) | Canadian format: A1A 1A1 |
| `country` | CharField(max_length=2, default="CA") | ISO 3166-1 alpha-2 |
| `website` | URLField(blank=True) | Organisation website |

Implement singleton pattern following InstanceSetting's approach — `get_solo()` class method or similar. Only one row should exist per instance.

Add an admin view/form for editing OrganizationProfile (if the admin settings section has one). Use Django ModelForm.

Write tests for: singleton enforcement, `get_solo()` creates-if-missing, all field defaults.

### After all agents complete

1. Run `makemigrations` and `migrate` (may need to combine if agents created separate migration files)
2. Run `python manage.py translate_strings`
3. Run tests: `pytest tests/test_plans.py tests/test_programs.py`
4. Mark TODO.md: CIDS-META1 + CIDS-ORG1 done
5. Create PR with note: "GK reviews: CIDS metadata field selection"
6. **Wait for PR merge before starting Session 2**

---

## Session 2: CIDS Phase 2 + 2.5 — Code Lists, Taxonomy Mapping, Enriched Reports

**Branch:** `feat/cids-session-2`
**TODO tasks:** CIDS-CODES1 + CIDS-ADMIN1 + CIDS-ENRICH1
**Depends on:** Session 1 merged

### What to build

Four pieces — Agents 1 and 2 can run in parallel, then Agent 3 needs their output, then Agent 4 needs Agent 3's output:

#### Agent 1: CidsCodeList model + management command (parallel with Agent 2)

Create **CidsCodeList** in `apps/admin_settings/models.py` (or a new `apps/cids/` app if the team prefers — check project conventions for where utility models live):

| Field | Type | Notes |
|---|---|---|
| `list_name` | CharField(max_length=100) | e.g., "ICNPOsector", "SDGImpacts", "IrisMetric53" |
| `code` | CharField(max_length=100) | The code value |
| `label` | CharField(max_length=255) | Display label (English) |
| `label_fr` | CharField(max_length=255, blank=True) | French label |
| `description` | TextField(blank=True) | Longer description |
| `specification_uri` | CharField(max_length=500, blank=True) | URI of code list spec (for SHACL `cids:hasSpecification`) |
| `defined_by_name` | CharField(max_length=255, blank=True) | Defining organisation name (e.g., "GIIN", "United Nations") |
| `defined_by_uri` | CharField(max_length=500, blank=True) | URI of defining organisation (for SHACL `cids:definedBy`) |
| `source_url` | URLField(blank=True) | Common Approach code list page URL |
| `version_date` | DateField(blank=True, null=True) | For staleness warnings |

**Constraints:** `unique_together = [("list_name", "code")]`

**Management command: `import_cids_codelists`**
- Fetch 17 code lists from `codelist.commonapproach.org` (they publish CSV/JSON files)
- Populate CidsCodeList table (upsert — update existing, insert new)
- Support `--dry-run` flag (show what would change, don't write)
- Support `--force` flag (reimport even if version_date matches)
- Warn if local copy is stale (local version_date < remote)
- Prioritise lists #1–10 (High/Medium relevance — see `tasks/cids-plan-validation.md` list table)
- The 17 lists: SDGImpacts, IRISImpactTheme, IrisMetric53, UnitsOfMeasureList, IRISImpactCategory, ICNPOsector, ESDCSector, PopulationServed, EquityDeservingGroupsESDC, ProvinceTerritory, OrgTypeGOC, CanadianCorporateRegistries, LocalityStatsCan, FundingState, RallyImpactArea, SELI-GLI, StatsCanSector

Write tests for: model constraints, management command (mock HTTP), upsert logic, dry-run mode.

#### Agent 2: TaxonomyMapping model (parallel with Agent 1)

**This model is new** — it was added by the taxonomy panel (2026-02-27) to solve the multi-funder taxonomy problem. It is NOT in the original CIDS plan. See `tasks/design-rationale/fhir-informed-modelling.md` — "DO NOT hardcode an internal outcome taxonomy."

**Requirements:**
- A single metric (or program, or plan target) can have multiple taxonomy mappings
- Each mapping identifies: which taxonomy system (e.g., `cids_iris`, `united_way`, `phac`, `provincial`), which code within that system, which display label, and optionally which funder/partner relationship this mapping serves (blank = universal mapping)
- Config templates can pre-populate these mappings during agency onboarding (bulk creation)

**Design decision — GenericFK vs explicit FKs:**
The project does NOT currently use GenericForeignKey anywhere. Evaluate both options:
- **Option A: Explicit nullable FKs** — `metric_definition` (FK, nullable), `program` (FK, nullable), `plan_target` (FK, nullable). Simpler queries, standard Django patterns, but only 1 of 3 should be set per row.
- **Option B: GenericFK** — `content_type` + `object_id`. More flexible but adds complexity the project hasn't used before.

**Choose Option A** (explicit FKs) unless there's a strong reason otherwise — it's simpler, matches the project's patterns, and the set of mappable models is small and known.

Suggested fields:

| Field | Type | Notes |
|---|---|---|
| `metric_definition` | FK to MetricDefinition(null=True, blank=True) | SET_NULL |
| `program` | FK to Program(null=True, blank=True) | SET_NULL |
| `plan_target` | FK to PlanTarget(null=True, blank=True) | SET_NULL |
| `taxonomy_system` | CharField(max_length=50) | e.g., "cids_iris", "united_way", "phac" |
| `taxonomy_code` | CharField(max_length=100) | Code within the system |
| `taxonomy_label` | CharField(max_length=255, blank=True) | Display label |
| `funder_context` | CharField(max_length=100, blank=True) | Which funder this mapping serves (blank = universal) |
| `created_at` | DateTimeField(auto_now_add=True) | |

**Constraints:** Add a model `clean()` method that validates exactly one of the three FKs is set.

Write tests for: validation (exactly one FK set), multiple mappings per metric, funder scoping, bulk creation.

#### Agent 3: Admin UI for CIDS tagging (depends on Agents 1 + 2)

After CidsCodeList and TaxonomyMapping exist:

- On MetricDefinition admin form: add dropdown for `iris_metric_code` populated from `CidsCodeList.objects.filter(list_name="IrisMetric53")`
- On MetricDefinition admin form: add multi-select for `sdg_goals` from `CidsCodeList.objects.filter(list_name="SDGImpacts")`
- On Program admin form: add dropdown for `cids_sector_code` from CidsCodeList
- Pre-mapping via config templates means these fields arrive pre-populated — admin UI is for overrides only
- Add admin view for managing TaxonomyMapping entries per metric/program

Write tests for: form rendering, dropdown population, form submission.

#### Agent 4: CIDS-enriched reports (depends on Agent 3)

Add CIDS data to existing CSV/PDF partner reports:

- Include IRIS+ codes, SDG alignment in report data
- Add "Standards Alignment" appendix page showing: which CIDS indicators are mapped, SDG alignment, CIDS theme derivation results
- **CIDS theme derivation logic:**
  1. Primary: `iris_metric_code` → look up in CidsCodeList (list_name="IRISImpactTheme") → get parent theme. This is precise.
  2. Admin override: `cids_theme_override` on MetricDefinition (for edge cases where derivation is wrong)
  3. Future (Session 5): TaxonomyMapping lookups will add a third derivation tier
- Reference CIDS v3.2 (not v2.0) in the appendix
- This is the **quick win for funders** — no ServiceEpisode needed

Read the existing report code first: `apps/reports/` — understand the current CSV/PDF generation patterns before adding to them.

Write tests for: report generation with CIDS data, theme derivation logic.

### After all agents complete

1. Run migrations
2. Run translations
3. Run `import_cids_codelists --dry-run` to verify command works
4. Run tests: `pytest tests/test_plans.py tests/test_exports.py`
5. Mark TODO.md: CIDS-CODES1 + CIDS-ADMIN1 + CIDS-ENRICH1 done
6. Create PR
7. **Wait for PR merge before starting Session 3**

---

## Session 3: Phase F1 — ServiceEpisode

**Branch:** `feat/cids-session-3`
**TODO tasks:** FHIR-EPISODE1 + FHIR-MIGRATE1
**GK review:** Yes — ServiceEpisode data model, status choices, end_reason choices
**Depends on:** Session 2 merged

**This is the biggest and most sensitive change.** 112 files reference ClientProgramEnrolment. The extend-in-place strategy with class alias is critical to avoid breaking everything.

### What to build

Two phases — model changes first, then UI:

#### Phase A: Model + Migration (do first)

**Extend ClientProgramEnrolment into ServiceEpisode** in `apps/clients/models.py`:

```python
class ServiceEpisode(models.Model):  # Was: ClientProgramEnrolment
    """Extended with FHIR-informed fields. Keeps existing table."""
    class Meta:
        db_table = "clients_clientprogramenrolment"  # Keep existing table name
    # ... existing fields + new fields ...

# Backwards compatibility — all existing imports continue working
ClientProgramEnrolment = ServiceEpisode
```

**Expand existing `status` field choices** (this is an EXISTING CharField getting new values):

| Value | Display | When |
|---|---|---|
| `planned` | Planned | Intake scheduled but not yet started |
| `waitlist` | Waitlisted | Client waiting for a spot |
| `active` | Active | Currently receiving service (was: `enrolled`) |
| `on_hold` | On Hold | Temporarily paused |
| `finished` | Finished | Service ended (was: `unenrolled`) |
| `cancelled` | Cancelled | Planned/waitlisted that never started |

**New fields** (all nullable/optional):

| Field | Type | Notes |
|---|---|---|
| `status_reason` | TextField(blank=True) | Why the status changed |
| `episode_type` | CharField(max_length=20, blank=True) | **Auto-derived, NEVER worker-entered.** Values: new_intake, re_enrolment, transfer_in, crisis, short_term |
| `primary_worker` | FK to User(null=True, blank=True, on_delete=SET_NULL) | Assigned case worker |
| `referral_source` | CharField(max_length=30, blank=True) | Values: self, family, agency_internal, agency_external, healthcare, school, court, shelter, community, other |
| `started_at` | DateTimeField(null=True) | When active service began — populated from enrolled_at in migration |
| `ended_at` | DateTimeField(null=True, blank=True) | When service ended |
| `end_reason` | CharField(max_length=30, blank=True) | Values: completed, goals_met, withdrew, transferred, referred_out, lost_contact, moved, ineligible, deceased, other |

**Episode type auto-derivation logic** (implement in model save or a helper):
- No prior episodes for this client × program → `new_intake`
- Has a prior `finished` episode in this program → `re_enrolment`
- Has a prior episode that ended with `end_reason='transferred'` from another program → `transfer_in`
- `crisis` and `short_term` are set explicitly by admin (not auto-derived)

**New model: ServiceEpisodeStatusChange** (append-only history):

| Field | Type | Notes |
|---|---|---|
| `episode` | FK to ServiceEpisode(CASCADE) | |
| `status` | CharField(max_length=20) | The new status |
| `reason` | TextField(blank=True) | Why it changed |
| `changed_by` | FK to User(null=True, on_delete=SET_NULL) | |
| `changed_at` | DateTimeField(auto_now_add=True) | |

**Index:** `(episode, changed_at)` for chronological queries.

**Write pattern:** Every time `ServiceEpisode.status` changes, append a StatusChange row. Track dirty status field in `save()` method or use `post_save` signal. Also write to AuditLog for compliance trail.

**Data migration** (Django RunPython):

```
For each existing ClientProgramEnrolment row:
  1. Set started_at = enrolled_at
  2. Set status: "enrolled" → "active", "unenrolled" → "finished"
  3. Set ended_at = unenrolled_at (if unenrolled)
  4. Leave episode_type, end_reason, referral_source blank (unknown for historical)
  5. Create initial ServiceEpisodeStatusChange:
       status = new status value
       reason = "Migrated from ClientProgramEnrolment"
       changed_at = enrolled_at
```

**Migration approach:**
```python
operations = [
    migrations.RenameModel(
        old_name="ClientProgramEnrolment",
        new_name="ServiceEpisode",
    ),
    # Then AddField for each new field...
    # Then RunPython for data migration...
]
```

**Verify:** After migration, run a check that no existing code is broken:
- All 112 files that reference ClientProgramEnrolment should still work via the alias
- Run `pytest tests/test_clients.py` to verify

#### Phase B: UI changes (do after Phase A works)

1. **Discharge modal:** Replace the simple status toggle with a modal. One question: "Why is this person leaving?" — radio buttons for `end_reason` choices + optional text field for `status_reason`. System sets status to `finished`, records `ended_at`, writes StatusChange.

2. **Transfer enhancement:** When transferring (unenrol from program A, enrol in program B), finish episode A with `end_reason='transferred'`, create episode B with auto-derived `episode_type='transfer_in'`.

3. **On hold / resume:** New actions on client profile. "Put on hold" asks for a reason (text field), sets status to `on_hold`. "Resume service" sets status back to `active`. Both write StatusChange rows.

4. **Episode info display:** Show episode_type as informational on client profile (e.g., "Re-enrolment — previously served Jan–Aug 2024"). Display is read-only — workers cannot edit episode_type.

5. **Discharge reason is required** — radio buttons in the discharge modal. Include "Other" with optional text for edge cases.

### After completion

1. Run migrations (this is the most critical migration in the plan — dry-run on a test database first)
2. Run translations
3. Run FULL client tests: `pytest tests/test_clients.py`
4. Run broader tests to verify alias works: `pytest tests/test_plans.py tests/test_access_grants.py tests/test_exports.py`
5. Mark TODO.md: FHIR-EPISODE1 + FHIR-MIGRATE1 done
6. Create PR with note: "GK reviews: ServiceEpisode data model — status lifecycle choices, end_reason choices, episode_type auto-derivation logic, discharge modal UX"
7. **Wait for PR merge before starting Session 4**

---

## Session 4: Phase F2 + F3 — Achievement Status + Encounter Role

**Branch:** `feat/cids-session-4`
**TODO tasks:** FHIR-ACHIEVE1 + FHIR-ROLE1
**GK review:** Yes — achievement_status derivation logic, progress_descriptor mapping
**Depends on:** Session 3 merged

### What to build

Two independent pieces — **use agents in parallel:**

#### Agent 1: Achievement Status (Phase F2)

**New fields on PlanTarget** (`apps/plans/models.py`):

| Field | Type | Notes |
|---|---|---|
| `achievement_status` | CharField(max_length=20, blank=True) | See choices below |
| `achievement_status_source` | CharField(max_length=20, blank=True) | `auto_computed` or `worker_assessed` |
| `achievement_status_updated_at` | DateTimeField(null=True) | When last computed/assessed |
| `first_achieved_at` | DateTimeField(null=True, blank=True) | Timestamp when first `achieved`. **Never cleared once set.** Enables "time to achievement" reporting and `sustaining` detection. |

**Achievement status choices:**

| Value | Display (EN) | Display (FR) | Meaning |
|---|---|---|---|
| `in_progress` | In progress | En cours | Working toward goal, no clear trend yet |
| `improving` | Improving | En amélioration | Positive trajectory |
| `worsening` | Worsening | En détérioration | Negative trajectory |
| `no_change` | No change | Aucun changement | Stable |
| `achieved` | Achieved | Atteint | Target reached |
| `sustaining` | Sustaining | Maintenu | Maintaining gains after achieving |
| `not_achieved` | Not achieved | Non atteint | Goal concluded without reaching target |
| `not_attainable` | Not attainable | Non réalisable | Goal needs revision — **NEVER auto-computed** |

**Derivation logic — quantitative goals (MetricValues exist):**

Compute from the last 3 recorded MetricValues for the primary metric:
- 2 of 3 show improvement → `improving`
- 2 of 3 show decline → `worsening`
- Mixed or flat → `no_change`
- Latest value meets/exceeds target threshold → `achieved`
- Previously `achieved` and still meets threshold → `sustaining`
- Previously `achieved` but drops below → `worsening`

**"Improvement" direction** depends on `MetricDefinition.higher_is_better`:
- If `higher_is_better=True`: higher value = improvement
- If `higher_is_better=False`: lower value = improvement

**Derivation logic — qualitative goals (progress_descriptor only):**

Map from ProgressNoteTarget.progress_descriptor:

| progress_descriptor | achievement_status |
|---|---|
| `harder` | `worsening` |
| `holding` | `no_change` |
| `shifting` | `improving` |
| `good_place` | `achieved` (first time) or `sustaining` (if previously achieved) |

**Sparse data rules:**

| Data Points | Behaviour |
|---|---|
| 0 | `in_progress` — no data |
| 1 | `in_progress` (unless single point meets target → `achieved`) |
| 2 | Simple comparison (2nd vs 1st) |
| 3+ | Full 3-point trend analysis |

**`not_attainable` — NEVER auto-computed.** Always requires deliberate worker/PM action. It means the goal needs revision, not that the client failed.

**`achieved` trigger:** When latest metric meets/exceeds target, set `achievement_status = "achieved"` and record `first_achieved_at` (if not already set). If already set and still meets → `sustaining`. If drops below → `worsening`.

**Computation trigger:** Recalculate when a ProgressNote is saved that includes a ProgressNoteTarget for this goal. Store result on PlanTarget for direct reporting queries.

**Worker override:** Show achievement_status on plan view with "(auto)" badge. Workers can click to override → sets `achievement_status_source = "worker_assessed"`. Next auto-computation only overwrites if source is `auto_computed`.

**UI:** Add achievement_status display to the plan target view. Show "(auto)" badge. Add override action (small edit icon or link). No new forms — override is a simple HTMX action that sets the status.

Write tests for: derivation logic (quantitative — improving/worsening/no_change/achieved/sustaining), derivation logic (qualitative — all 4 descriptors), sparse data (0/1/2/3+ points), `higher_is_better` direction, `first_achieved_at` set/never-cleared, worker override preserves through auto-computation, `not_attainable` never auto-set.

#### Agent 2: Encounter Participant Role (Phase F3)

**New field on ProgressNote** (`apps/notes/models.py`):

| Field | Type | Notes |
|---|---|---|
| `author_role` | CharField(max_length=30, blank=True) | Auto-filled from UserProgramRole at note creation |

**Auto-fill logic:** When a ProgressNote is created, look up `UserProgramRole.objects.filter(user=author, program=author_program, status="active").first()` and store `role` value (receptionist/staff/program_manager/executive).

**No UI change.** The worker never sees or selects this field. It's recorded automatically for reporting accuracy.

**Backfill migration:** For existing notes, attempt to fill `author_role` from current UserProgramRole (understanding it may be wrong if roles changed — this is acceptable for historical data, note it in the migration).

Write tests for: auto-fill on creation, correct role lookup, missing UserProgramRole handled gracefully (blank), backfill migration.

### After all agents complete

1. Run migrations
2. Run translations
3. Run tests: `pytest tests/test_plans.py tests/test_notes.py`
4. Mark TODO.md: FHIR-ACHIEVE1 + FHIR-ROLE1 done
5. Create PR with note: "GK reviews: achievement_status derivation methodology — quantitative trend analysis, qualitative descriptor mapping, sparse data rules, worker override logic"
6. **Wait for PR merge before starting Session 5**

---

## Session 5: CIDS Phase 3 + 4 + 5 — JSON-LD Export, Impact Dimensions, Conformance

**Branch:** `feat/cids-session-5`
**TODO tasks:** CIDS-EXPORT1 + CIDS-IMPACT1 + CIDS-VALIDATE1
**Depends on:** Session 4 merged

**Note:** Phase 3 alone is substantial. If context or time is limited, complete Phase 3 and create a PR. Phases 4 and 5 can be a follow-up session.

### What to build

#### Part 1: JSON-LD Export (CIDS Phase 3) — do first

Build a management command or admin action: "Export CIDS JSON-LD"

**Export structure** (construct from existing data — no new models needed):

| CIDS Class | KoNote Source | Notes |
|---|---|---|
| `cids:Organization` | OrganizationProfile | `org:hasLegalName` from `legal_name` |
| `cids:Program` | Program | FullTier only |
| `cids:Outcome` | PlanTarget (aggregated) | `org:hasName` from target name |
| `cids:Indicator` | MetricDefinition | `cids:unitDescription` from `cids_unit_description` |
| `cids:IndicatorReport` | MetricValue (aggregated) | Wraps values in `i72:Measure` objects |
| `cids:Theme` | CidsCodeList (IRISImpactTheme) | Derived from iris_metric_code |
| `cids:Code` | CidsCodeList | 6 required SHACL fields (see validation report) |
| `cids:BeneficialStakeholder` | Program cohort description | **Group/cohort, NOT individual client** |
| `cids:StakeholderOutcome` | Constructed at export time | Junction: stakeholder group × outcome |
| `cids:Target` | PlanTarget target values | Separate from Outcome |
| `cids:Activity` | ProgressNote (aggregated by type) | Session/encounter counts |
| `cids:ImpactReport` | Computed from data | Links to impact dimensions |

**JSON-LD format:**
- Use official context URL: `"@context": "https://ontology.commonapproach.org/contexts/cidsContext.jsonld"`
- All entities get `@id` and `@type` fields
- Use context-defined terms: `hasName` (not `sch:name`), `hasDescription` (not `sch:description`), `hasLegalName` (for Organisation only)
- Measurement values: wrap in `i72:Measure` with `i72:hasNumericalValue` (xsd:string, not number literal)
- Reference CIDS v3.2.0

**CIDS theme derivation** (three tiers, by this point all tiers are available):
1. `iris_metric_code` → CidsCodeList lookup → parent IRISImpactTheme (precise)
2. TaxonomyMapping lookup for `taxonomy_system="cids_iris"` (when available)
3. `cids_theme_override` on MetricDefinition (admin escape hatch)

**SHACL validation:**
- Use `pyshacl` library to validate generated JSON-LD against CIDS SHACL shapes
- Validate against BasicTier first, then EssentialTier, then FullTier
- SHACL shape files: `cids.basictier.shacl.ttl`, `cids.essentialtier.shacl.ttl`, `cids.fulltier.shacl.ttl`
- Report pass/fail per tier with detailed error messages
- The SHACL files are published at ontology.commonapproach.org — download and store in `validation/shacl/` or fetch on demand

**ServiceEpisode enrichments** (from Session 3):
- `cids:Activity` counts scoped to specific episodes
- `cids:BeneficialStakeholder` cohorts defined by episode_type (new_intake vs re_enrolment)
- `cids:Output` scoped to episodes, not just date ranges

**Achievement status enrichments** (from Session 4):
- `cids:Outcome` exports enriched with achievement data
- More nuanced depth reporting than simple "met target" percentages

Write comprehensive tests for: JSON-LD structure validation, theme derivation (all 3 tiers), SHACL validation pass/fail, aggregate data (no individual PII), i72:Measure wrapping, BeneficialStakeholder as group.

#### Part 2: Impact Dimensions (CIDS Phase 4) — can be deferred

Compute the three HowMuchImpact dimensions (all EssentialTier):

| Dimension | Source | Computation |
|---|---|---|
| **ImpactScale** | ServiceEpisode counts | How many people affected — count distinct clients with active episodes in reporting period |
| **ImpactDepth** | PlanTarget.achievement_status | How much change — distribution of achievement_status values (% improving, % achieved, % sustaining) |
| **ImpactDuration** | ServiceEpisode dates + first_achieved_at | How long it lasts — time from episode start to end, time from first_achieved_at to reporting date |

Each dimension produces `i72:value` (Measure) + `cids:hasDescription` in the JSON-LD export.

#### Part 3: Conformance Badge (CIDS Phase 5) — can be deferred

- Run SHACL validation against all three tiers
- Display results on admin dashboard as a conformance badge (BasicTier ✓, EssentialTier ✓, FullTier ✓)
- Detailed validation report showing per-entity results
- Link to the exported JSON-LD file

### After completion

1. Run full test suite: `pytest -m "not browser and not scenario_eval"`
2. Mark TODO.md: CIDS-EXPORT1 done (+ CIDS-IMPACT1, CIDS-VALIDATE1 if completed)
3. Create PR
4. **After merge, run `/review-session` to review the full implementation across all 5 sessions**

---

## Summary of parallelisation opportunities

| Session | Parallel agents | Sequential dependencies |
|---|---|---|
| **1** | 3 agents: MetricDefinition+PlanTarget fields, Program fields, OrganizationProfile | None — all independent |
| **2** | 2 agents: CidsCodeList+command, TaxonomyMapping | Admin UI depends on both models; Reports depend on admin UI |
| **3** | None — ServiceEpisode is one large sequential change | Model → Migration → UI (must be sequential) |
| **4** | 2 agents: Achievement status (F2), Author role (F3) | None — fully independent |
| **5** | Possibly: Phase 4 + Phase 5 after Phase 3 | Phase 3 must complete first |

## Summary of GK review gates

| Session | GK Reviews | What to flag |
|---|---|---|
| 1 | Yes | CIDS metadata field selection |
| 2 | No | Standard implementation of approved design |
| 3 | Yes | ServiceEpisode data model, status choices, end_reason choices |
| 4 | Yes | Achievement status derivation methodology |
| 5 | No | Standard implementation of approved design |

## Key anti-patterns (DO NOT violate)

1. **DO NOT add `outcome_domain`** to any model — removed by taxonomy panel
2. **DO NOT change `MetricDefinition.category`** — stays as-is (7 values) for UI grouping
3. **DO NOT implement a FHIR server, API, or validation** — plain Django models only
4. **DO NOT use FHIR CodeableConcept wrappers** — CharField with choices
5. **DO NOT let workers select episode type** — auto-derive from history
6. **DO NOT ask workers to select role** — auto-fill from UserProgramRole
7. **DO NOT add presenting issues as intake field** — compute from existing data (deferred)
8. **DO NOT build Care Team** — deferred to multi-agency phase
9. **DO NOT auto-compute `not_attainable`** — always deliberate worker decision
10. **`cids_has_baseline` is a CharField, NOT a BooleanField** — stores human-readable baseline text
