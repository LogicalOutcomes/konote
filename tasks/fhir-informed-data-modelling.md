# FHIR-Informed Data Modelling — Implementation Plan

**Task ID:** FHIR-DATA1
**Created:** 2026-02-27
**Status:** Draft — awaiting GK review
**Depends on:** Interleaved with CIDS phases (see Sequencing section)
**Reviewed by:** Second expert panel (4 experts, 3 rounds) — 5 revisions incorporated 2026-02-27
**Expert panel:** 5-expert panel (Social Services Data Architect, Health Informatics Specialist, Nonprofit Technology Strategist, Evaluation & Measurement Specialist, Systems Architect) — consensus reached 2026-02-27

---

## What This Is

KoNote borrows data modelling patterns from FHIR R4 (and the Gravity Project's SDOH Clinical Care IG) to solve real reporting problems — **without requiring FHIR compliance**. No FHIR server, no FHIR validation, no FHIR profiles. Plain Django models that use FHIR's vocabulary and relationship patterns.

**Design principle:** "Borrow FHIR concepts without FHIR compliance." Use the data relationships that FHIR has refined over thousands of hours of domain analysis, but implement them as standard Django models. If health system interoperability is ever needed, the mapping is already done.

**Why now:** The CIDS implementation plan (tasks/cids-json-ld-export.md) adds metadata for standardised reporting exports. FHIR-informed models structure the *underlying data* so those exports are richer and more precise. The two standards complement each other:
- **CIDS** tells you *what to export* (Organisation → Outcome → Indicator → IndicatorReport)
- **FHIR-informed models** structure *how you track the data* (Episode → Encounter → Goal → Observation)

**Why not full FHIR:** KoNote explicitly chose not to be an EHR/EMR (see docs/archive/what-konote-is.md). Full FHIR compliance requires terminology bindings (SNOMED-CT, LOINC), resource validation, RESTful API conformance, and capability statements — none of which serve a nonprofit outcome tracker.

---

## What Problem This Solves

### The "What counts as new?" problem

Every funder defines "new participant" differently:

| Funder Definition | What the agency has to do today |
|---|---|
| "New = first enrolled this calendar year" | Cross-reference enrolment dates manually |
| "New = enrolled within last 3 months" | Calculate from enrolment date, hope nobody forgot to unenrol |
| "New = not connected with agency in last 12 months" | Search through old records, compare dates across spreadsheets |
| "New = never served by this program before" | Check all historical enrolments — if they exist |
| "Returning" (explicit category) | No way to distinguish from "new" in the current data model |

**Current model** (`ClientProgramEnrolment`): Two fields — `enrolled_at` and `unenrolled_at`. One row per enrolment. No status history, no reason for leaving, no distinction between first-time and returning.

**With ServiceEpisode:** The data is recorded once. The definition of "new" becomes a report-time filter. Every funder gets their number from the same data.

### The "binary outcomes" problem

KoNote tracks PlanTarget status as `default/completed/deactivated`. That's a lifecycle state, not a progress measure. A client who went from a wellbeing score of 2 to 6 but didn't reach the target of 7 is counted as "not completed." A client who hit 7, then dropped to 4 is counted as "completed."

FHIR's Goal resource separates lifecycle (is the goal still being worked on?) from achievement (how is the client actually doing?). KoNote already captures the data for achievement — the `progress_descriptor` on ProgressNoteTarget (harder/holding/shifting/good_place) — but doesn't map it to a reportable vocabulary.

### The "who did what in which role?" problem

ProgressNote captures `author` but not the author's role at time of service. If someone was a staff worker who later became a program manager, historical reports that group by role are wrong.

---

## Expert Panel Consensus (2026-02-27)

### Agreed by all five experts:

1. **"Borrow concepts, don't comply" is the right approach.** FHIR's data relationships are valuable; FHIR's compliance overhead is not.
2. **ServiceEpisode is the highest-priority change.** It solves the most pressing reporting problems and is the foundation for other improvements.
3. **Achievement status should be derived, not entered.** Map from existing progress_descriptor (qualitative) or compute from metric trajectory (quantitative). Zero new data entry.
4. **KoNote should not impose its own internal taxonomy.** Every funder, partner, and collaboration uses a different outcome classification system. A hardcoded 14-value taxonomy will fail the same way every sector attempt at standardisation has failed. Keep `category` (7 values) for UI grouping; handle external taxonomies via a mapping layer (see Taxonomy Panel addendum 2026-02-27).
5. **Presenting issues should be computed from existing data**, not a new data entry requirement.
6. **Episode type should be auto-derived from history**, not worker-entered.
7. **Discharge reason is the one new question workers answer.** A single question ("Why is this person leaving?") with 5-6 radio buttons.

### Priority order (expert consensus):

ServiceEpisode ≫ Goal Achievement Status ≫ Encounter Role > Presenting Issues (computed) > Referral Tracking > Care Team

---

## Implementation Phases

### ~~Phase F0: Unified Outcome Domain Taxonomy~~ — REMOVED (2026-02-27)

> **Taxonomy Panel decision (2026-02-27):** A 4-expert panel (Nonprofit Evaluation Specialist, Data Interoperability Specialist, Product Designer, Systems Architect) reviewed GK's feedback that every funder, partner, and collaboration uses a different outcome taxonomy. The panel unanimously recommended **removing the hardcoded 14-value `outcome_domain` taxonomy** from the plan. See `tasks/design-rationale/fhir-informed-modelling.md` for the full panel record.

**What was planned:** Replace `MetricDefinition.category` (7 values) with `outcome_domain` (14 values). Add `outcome_domain` to Program and PlanTarget. Use as a Rosetta Stone for mapping to external taxonomies.

**Why it was removed:**

1. **Every funder has a different taxonomy.** United Way, PHAC, provincial ministries, and sector collaborations all classify outcomes differently. A single internal taxonomy cannot map to all of them without `custom` becoming the default.
2. **One metric, many indicators.** A PHQ-9 score maps to PHAC's "mental health," United Way's "individual wellbeing," CIDS's IRIS Health theme, and SDG Goal 3 — simultaneously. A single CharField cannot represent this.
3. **The sector has tried and failed.** Canadian nonprofits have attempted taxonomy standardisation for years. No consensus exists, and KoNote should not pretend to solve this.
4. **`category` already works for its purpose.** The existing 7-value `category` field is used for admin UI grouping. It's not a reporting field or a standards alignment field. It should stay unchanged.

**What replaces it:**

- **Keep `MetricDefinition.category` as-is** (7 values, admin UI grouping only)
- **Do NOT add `outcome_domain` to MetricDefinition, Program, or PlanTarget**
- **Do NOT create a data migration mapping `category` → `outcome_domain`**
- **CIDS metadata fields proceed as planned** (iris_metric_code, sdg_goals, etc.) — these are direct identifiers, not a taxonomy
- **Taxonomy mapping layer arrives in CIDS Phase 2** (alongside code list import) — designed for multiple external taxonomies from the start

#### CIDS Theme derivation (revised — two tiers instead of three)

Since `outcome_domain` is removed, the middle tier of the original three-tier derivation is no longer available. CIDS Theme derivation at export time now uses two tiers:

1. **Primary:** `iris_metric_code` (from CIDS Phase 1b) → look up in `CidsCodeList` → get the parent IRIS Impact Theme. This is precise and spec-compliant.
2. **Admin override:** `cids_theme_override` (new CharField on MetricDefinition, blank=True) — admin correction for metrics without an `iris_metric_code` or where the auto-derived theme is wrong.

When the taxonomy mapping layer arrives (CIDS Phase 2), a third tier can be inserted between these two: explicit CIDS taxonomy mapping from the mapping table.

**New field on MetricDefinition:** `cids_theme_override` (CharField, max_length=50, blank=True). Only used when the auto-derived theme is wrong or when a metric has no `iris_metric_code`.

**Impact on CIDS Phase 1:** Phase 1b retains all originally planned fields (`cids_indicator_uri`, `iris_metric_code`, `sdg_goals`, `cids_unit_description`, `cids_defined_by`, `cids_has_baseline`) and adds `cids_theme_override`. The originally proposed `cids_theme` and `cids_impact_theme` fields are unnecessary — the export layer derives themes from `iris_metric_code` and taxonomy mappings.

---

### Phase F1: ServiceEpisode (extends ClientProgramEnrolment in place)

**FHIR source:** EpisodeOfCare resource (status state machine + statusHistory pattern)

**Migration strategy (revised per review panel):** Extend ClientProgramEnrolment in place rather than replacing it. Rename the existing class to `ServiceEpisode`, add new fields, create a `ClientProgramEnrolment` alias for backwards compatibility. This eliminates the mass query rewrite risk — all existing references continue working unchanged.

**Django migration approach:** Use `RenameModel` operation (or manual `state_operations` with `migrations.RenameModel`) so Django's migration framework knows the model was renamed, not deleted and recreated. Do NOT create a new model class pointing at the same `db_table` — Django may interpret that as creating a new model.

```python
# In apps/clients/models.py — rename the existing class, add fields
class ServiceEpisode(models.Model):  # Was: ClientProgramEnrolment
    """Extended with FHIR-informed fields. Keeps existing table."""
    class Meta:
        db_table = "clients_clientprogramenrolment"  # Keep existing table
    # ... existing fields + new fields below ...

# Backwards compatibility alias — all existing imports still work
ClientProgramEnrolment = ServiceEpisode
```

```python
# In the migration file
operations = [
    migrations.RenameModel(
        old_name="ClientProgramEnrolment",
        new_name="ServiceEpisode",
    ),
    # Then AddField for each new field...
]
```

#### Model: `ServiceEpisode` (extends existing table)

**Where it lives:** `apps/clients/models.py` (replaces ClientProgramEnrolment class definition)

| Field | Type | FHIR Concept | Notes |
|---|---|---|---|
| `client_file` | FK to ClientFile | EpisodeOfCare.patient | CASCADE |
| `program` | FK to Program | managingOrganization | CASCADE |
| `status` | CharField(max_length=20) | EpisodeOfCare.status | See status choices below |
| `status_reason` | TextField(blank=True) | — | Why the status changed |
| `episode_type` | CharField(max_length=20, blank=True) | EpisodeOfCare.type | **Auto-derived** — see logic below |
| `primary_worker` | FK to User(null=True, blank=True) | careManager | SET_NULL. Assigned case worker |
| `referral_source` | CharField(max_length=30, blank=True) | referralRequest | How they got here |
| `started_at` | DateTimeField | period.start | When active service began |
| `ended_at` | DateTimeField(null=True, blank=True) | period.end | When service ended |
| `end_reason` | CharField(max_length=30, blank=True) | — | Why service ended |
| `enrolled_at` | DateTimeField(auto_now_add=True) | — | When the record was created (preserves current behaviour). Serves as `created_at` — no separate timestamp needed. |
| `updated_at` | DateTimeField(auto_now=True) | — | |

**Status choices** (from FHIR EpisodeOfCare, adapted for social services):

| Value | Display | FHIR Equivalent | When |
|---|---|---|---|
| `planned` | Planned | planned | Intake scheduled but not yet started |
| `waitlist` | Waitlisted | waitlist | Client is waiting for a spot |
| `active` | Active | active | Currently receiving service |
| `on_hold` | On Hold | onhold | Temporarily paused (e.g., family emergency, seasonal) |
| `finished` | Finished | finished | Service ended (see end_reason) |
| `cancelled` | Cancelled | cancelled | Planned/waitlisted episode that never started |

**Episode type choices** (auto-derived, not worker-entered):

| Value | Display | Auto-derivation Logic |
|---|---|---|
| `new_intake` | New Intake | No prior episodes for this client × program |
| `re_enrolment` | Re-enrolment | Has a prior `finished` episode in this program |
| `transfer_in` | Transfer In | Has a prior episode that ended with `end_reason='transferred'` from another program |
| `crisis` | Crisis | Set explicitly by crisis intake workflow (if built) |
| `short_term` | Short-term | Set explicitly by admin (e.g., drop-in programs) |

**End reason choices:**

| Value | Display | Reporting Use |
|---|---|---|
| `completed` | Completed program | Success / planned discharge |
| `goals_met` | Goals met | Success — client achieved their goals |
| `withdrew` | Withdrew | Client chose to leave |
| `transferred` | Transferred to another program | Internal transfer |
| `referred_out` | Referred to external agency | External referral |
| `lost_contact` | Lost contact | Could not reach client |
| `moved` | Moved away | Client relocated |
| `ineligible` | No longer eligible | Eligibility change |
| `deceased` | Deceased | |
| `other` | Other | Requires status_reason text |

**Referral source choices:**

| Value | Display |
|---|---|
| `self` | Self-referred |
| `family` | Family/friend |
| `agency_internal` | Internal program transfer |
| `agency_external` | External agency referral |
| `healthcare` | Healthcare provider |
| `school` | School/education |
| `court` | Court/justice system |
| `shelter` | Shelter/housing |
| `community` | Community organisation |
| `other` | Other |

#### New model: `ServiceEpisodeStatusChange`

Append-only status history for reporting queries.

| Field | Type | Notes |
|---|---|---|
| `episode` | FK to ServiceEpisode | CASCADE |
| `status` | CharField(max_length=20) | The new status |
| `reason` | TextField(blank=True) | Why it changed |
| `changed_by` | FK to User(null=True) | SET_NULL |
| `changed_at` | DateTimeField(auto_now_add=True) | When |

**Indexes:** `(episode, changed_at)` for chronological queries.

**Write pattern:** Every time `ServiceEpisode.status` changes, a `ServiceEpisodeStatusChange` row is appended. This happens in the model's `save()` method (track dirty status field) or via a `post_save` signal. Also write to AuditLog for compliance trail.

#### Data migration (in-place field population)

Since we extend the existing table, migration is simpler — no data copying:

```
Django migration:
  0. RenameModel: ClientProgramEnrolment → ServiceEpisode
  1. Add new fields (all nullable) to clients_clientprogramenrolment table
  2. Replace STATUS_CHOICES:
       Old: enrolled, unenrolled (2 values)
       New: planned, waitlist, active, on_hold, finished, cancelled (6 values)
       The old "enrolled" and "unenrolled" values are REMOVED from choices.
       The data migration (step 3) converts all existing rows before the
       new choices take effect, so no orphaned values remain.
  3. Run data migration:
     For each existing row:
       → Set started_at = enrolled_at
       → Set new status: "active" if old status == "enrolled", else "finished"
       → Set ended_at = unenrolled_at (if unenrolled)
       → Leave episode_type, end_reason, referral_source blank (unknown for historical data)
  4. Create initial ServiceEpisodeStatusChange for each row:
       status = new status value
       reason = "Migrated from ClientProgramEnrolment"
       changed_at = enrolled_at
```

**All new fields are nullable/optional.** Historical data gets enriched opportunistically; going forward, the system captures complete data.

**Migration safety:** The `ClientProgramEnrolment` class name is aliased to `ServiceEpisode`, so all existing imports and queries continue working. No table rename, no foreign key changes, no mass query rewrite. Dry-run on staging database before production.

#### UI changes (minimal)

**Enrol client:** No change to the UI. Worker clicks "Enrol" as today. System creates a ServiceEpisode with status `active`, auto-derives `episode_type`.

**Discharge client:** New discharge modal replaces the simple status toggle. One question: **"Why is this person leaving?"** — radio buttons for `end_reason` choices + optional text field for `status_reason`. System sets status to `finished`, records `ended_at`, writes `ServiceEpisodeStatusChange`.

**Transfer client:** Existing transfer workflow (unenrol from program A, enrol in program B) enhanced to: finish episode A with `end_reason='transferred'`, create episode B with auto-derived `episode_type='transfer_in'`.

**Put on hold / resume:** New actions on the client profile. "Put on hold" asks for a reason, sets status to `on_hold`. "Resume service" sets status back to `active`. Both write status changes.

#### Reporting queries enabled

```python
# "New participants this fiscal year" (first-ever episode)
ServiceEpisode.objects.filter(
    program=program,
    episode_type="new_intake",
    started_at__gte=fiscal_year_start
).values("client_file").distinct().count()

# "Returning participants" (re-enrolments)
ServiceEpisode.objects.filter(
    program=program,
    episode_type="re_enrolment",
    started_at__gte=fiscal_year_start
).values("client_file").distinct().count()

# "Not served in 12 months" definition of new
from django.db.models import Max
# Clients whose most recent prior episode ended > 12 months ago
# (computed at report time from episode history)

# "Average time on waitlist"
# Duration between waitlist status and active status in StatusChange

# "Completion rate"
finished = ServiceEpisode.objects.filter(program=program, status="finished", ended_at__range=(start, end))
completed = finished.filter(end_reason__in=["completed", "goals_met"]).count()
total = finished.count()
completion_rate = completed / total if total else 0

# "Currently on hold and why"
ServiceEpisode.objects.filter(program=program, status="on_hold").select_related("client_file")
```

#### CIDS export impact

- `cids:Activity` counts can be scoped to specific episodes (e.g., "sessions delivered to clients with active episodes during reporting period")
- `cids:BeneficialStakeholder` cohorts can be defined precisely ("clients with `new_intake` episodes in the reporting period" vs. "all clients ever enrolled")
- `cids:Output` (session counts, service stats) scoped to episodes, not just date ranges

---

### Phase F2: Goal Achievement Status (on PlanTarget)

**FHIR source:** Goal.achievementStatus vocabulary

#### New fields on `PlanTarget`

| Field | Type | Notes |
|---|---|---|
| `achievement_status` | CharField(max_length=20, blank=True) | Derived or worker-assessed |
| `achievement_status_source` | CharField(max_length=20, blank=True) | `auto_computed` or `worker_assessed` |
| `achievement_status_updated_at` | DateTimeField(null=True) | When last computed/assessed |
| `first_achieved_at` | DateTimeField(null=True, blank=True) | Timestamp when achievement_status first became `achieved`. Enables "time to achievement" reporting and `sustaining` detection. Never cleared once set. |

**Achievement status choices** (from FHIR Goal.achievementStatus, adapted):

| Value | Display (EN) | Display (FR) | Meaning |
|---|---|---|---|
| `in_progress` | In progress | En cours | Working toward goal, no clear trend yet |
| `improving` | Improving | En amélioration | Positive trajectory (2 of last 3 data points show improvement) |
| `worsening` | Worsening | En détérioration | Negative trajectory |
| `no_change` | No change | Aucun changement | Stable, not improving or worsening |
| `achieved` | Achieved | Atteint | Target reached |
| `sustaining` | Sustaining | Maintenu | Maintaining gains after achieving target |
| `not_achieved` | Not achieved | Non atteint | Goal concluded without reaching target |
| `not_attainable` | Not attainable | Non réalisable | Goal needs to be revised — not a failure, a clinical reality |

#### Derivation logic (zero new data entry)

**For goals with quantitative metrics (MetricValues exist):**

Compute from the last 3 recorded MetricValues for the primary metric:
- If 2 of 3 show improvement over the prior point → `improving`
- If 2 of 3 show decline → `worsening`
- If mixed or flat → `no_change`
- If the latest value meets or exceeds the target threshold → `achieved`
- If previously `achieved` and latest value still meets threshold → `sustaining`
- If previously `achieved` and latest value drops below threshold → `worsening`

**For qualitative goals (no metrics, only progress_descriptor):**

Map from the existing ProgressNoteTarget.progress_descriptor:

| progress_descriptor | achievement_status |
|---|---|
| `harder` (Harder right now) | `worsening` |
| `holding` (Holding steady) | `no_change` |
| `shifting` (Something's shifting) | `improving` |
| `good_place` (In a good place) | `achieved` (first time) or `sustaining` (if previously achieved). **GK to review:** this mapping may inflate achievement rates for qualitative goals — consider mapping to `sustaining` or `no_change` instead unless a quantitative target has also been met. |

**Fallback:** If no metrics and no progress_descriptor recorded, leave as `in_progress`.

#### Edge cases (revised per review panel)

**Sparse data rules:**

| Data Points | Behaviour |
|---|---|
| 0 points | `in_progress` — no data to compute from |
| 1 point | `in_progress` — insufficient data for trend. If this single point meets the target, set `achieved`. |
| 2 points | Compare the two: improving if 2nd > 1st, worsening if 2nd < 1st, no_change if equal. Less reliable than 3-point but better than nothing. |
| 3+ points | Full 3-point trend analysis (2 of last 3 show improvement → `improving`, etc.) |

**`achieved` trigger mechanism:**
- When the latest metric value meets or exceeds the target threshold, set `achievement_status = "achieved"` and record `first_achieved_at` (if not already set).
- If `first_achieved_at` is already set and the latest value still meets threshold → `sustaining`.
- If `first_achieved_at` is set but latest value drops below threshold → `worsening` (not back to `in_progress` — the client did achieve once).

**`not_attainable` — never auto-computed.** This is always a deliberate worker or program manager decision. It means the goal needs revision, not that the client failed. Auto-computing it would be clinically inappropriate.

**Computation trigger:** Recalculate when a ProgressNote is saved that includes a ProgressNoteTarget for this goal. Store the result on PlanTarget so reports can query it directly without recomputing.

**Worker override:** Achievement status is shown on the plan view with an "(auto)" badge. Workers can click to override (sets `achievement_status_source` to `worker_assessed`). Next auto-computation only overwrites if source is `auto_computed`.

#### Reporting queries enabled

```python
# "Percentage of clients showing improvement in a specific program"
program_goals = PlanTarget.objects.filter(
    plan_section__program=program,
    status="default",  # active goals
    achievement_status="improving"
)

# "Percentage who achieved their goals"
achieved = PlanTarget.objects.filter(
    plan_section__program=program,
    achievement_status__in=["achieved", "sustaining"]
).count()

# "Clients who are sustaining gains" (the most important and most ignored measure)
sustaining = PlanTarget.objects.filter(
    plan_section__program=program,
    achievement_status="sustaining"
).count()
```

#### CIDS export impact

- `cids:Outcome` exports enriched with achievement data
- `cids:ImpactDepth` computation uses `achievement_status` for more nuanced depth reporting than simple "met target" percentages

---

### Phase F3: Encounter Participant Role (on ProgressNote)

**FHIR source:** Encounter.participant.type

#### New field on `ProgressNote`

| Field | Type | Notes |
|---|---|---|
| `author_role` | CharField(max_length=30, blank=True) | Auto-filled from UserProgramRole at time of note creation |

**Auto-fill logic:** When a ProgressNote is created, look up the author's UserProgramRole for `author_program` and store the role value (receptionist, staff, program_manager, executive). This captures role-at-time-of-service, not current role.

**No UI change.** The worker never selects their role. The system records it automatically.

#### Reporting value

- "How many sessions were delivered by case workers vs. program managers?"
- "Service intensity by provider role" — useful for staffing analysis
- Historical accuracy when staff change roles over time

---

### Phase F4: Presenting Issues (computed view — no new data entry)

**FHIR source:** Condition resource + Gravity Project SDOH categories

**Not a new model.** Presenting issues are computed from existing data:

1. **From program enrolment:** Client enrolled in a housing program → presenting issue derived from that program's category/taxonomy mappings
2. **From plan targets:** Client has goals with metrics in specific categories → presenting issues derived from metric categories
3. **From metrics:** Client has MetricValues for metrics tagged with specific taxonomy codes → presenting issues from those codes

#### Implementation

A Django model manager method or queryset annotation that computes presenting issues on the fly:

```python
def get_presenting_issues(client_file):
    """Compute presenting issues from program enrolment and metric categories."""
    categories = set()

    # From active episodes — use program's metrics' categories
    for ep in client_file.service_episodes.filter(status="active"):
        for metric in ep.program.metric_definitions.all():
            if metric.category:
                categories.add(metric.category)

    # From active plan targets — use the target's metric category
    for target in client_file.plan_targets.filter(status="default"):
        if target.metric_definition and target.metric_definition.category:
            categories.add(target.metric_definition.category)

    return sorted(categories)
```

**Note:** When the taxonomy mapping layer arrives (CIDS Phase 2), this function can also pull from taxonomy mappings for richer, funder-specific presenting issue classifications.

#### Reporting queries enabled

- "How many clients present with housing needs?" → Count clients enrolled in programs with housing-category metrics
- "Outcomes for clients who present with multiple needs" → Filter by clients with metrics across 2+ categories
- "Cross-domain analysis" → Compare achievement_status by metric category combinations

#### When to add explicit tagging

If a specific funder requires presenting issues that can't be derived from existing data (e.g., "food insecurity" when the agency doesn't have food-specific programs or metrics), add an optional `ClientPresentingIssue` model as an override layer. But don't build it until triggered by need.

---

### Phases F5-F6: Deferred (build when triggered)

#### F5: Service Referrals (FHIR ServiceRequest)

**Build when:** Multi-agency collaboration begins or a funder asks "how many referrals did your program generate?"

New model: `ServiceReferral`

| Field | Type | Notes |
|---|---|---|
| `client_file` | FK to ClientFile | |
| `from_program` | FK to Program (nullable) | Internal referral source |
| `to_program` | FK to Program (nullable) | Internal referral destination |
| `to_external` | CharField(blank=True) | External agency name |
| `status` | CharField | sent, accepted, rejected, completed, expired |
| `reason` | TextField(blank=True) | Why the referral was made |
| `referred_by` | FK to User | |
| `created_at` | DateTimeField | |
| `resolved_at` | DateTimeField(nullable) | |
| `resulting_episode` | FK to ServiceEpisode(nullable) | Links to the episode created from this referral |

#### F6: Care Team (FHIR CareTeam)

**Build when:** Multi-disciplinary teams or multi-agency collaborations require tracking who is collectively supporting a client.

For now, `ServiceEpisode.primary_worker` covers the 80% case.

---

## Sequencing with CIDS Implementation Plan

**Revised per review panel:** Interleave FHIR and CIDS phases instead of doing all FHIR first. This delivers a CIDS quick win (enriched reports) to funders earlier, before the heavier ServiceEpisode work.

### Interleaved sequence (revised)

| Order | Phase | What | Effort | Value | Why this order |
|---|---|---|---|---|---|
| **1** | **CIDS 1** | CIDS metadata fields + OrganizationProfile (no taxonomy change) | Low–Medium | High | Adds CIDS identifiers to MetricDefinition, Program, PlanTarget. No `category` change, no data migration. |
| **2** | **CIDS 2** | Import CIDS code lists + taxonomy mapping layer + admin UI | Medium | High | Needed for theme derivation — `iris_metric_code` looks up its theme in CidsCodeList. Taxonomy mapping model supports multiple external taxonomies per metric. |
| **3** | **CIDS 2.5** | CIDS-enriched CSV/PDF reports | Low | High | **Quick win for funders.** Uses iris_metric_code + taxonomy mappings. No ServiceEpisode needed yet. |
| **4** | **F1** | ServiceEpisode (extend ClientProgramEnrolment) + StatusChange | Medium | Very High | Now has CIDS foundation in place. Solves reporting headaches. |
| **5** | **F2** | Goal Achievement Status on PlanTarget | Low | High | Adds `achievement_status` + `first_achieved_at`. Enriches both internal reports and CIDS export. |
| **6** | **F3** | Encounter Participant Role on ProgressNote | Very Low | Medium | Auto-filled, no workflow change. |
| **7** | **CIDS 3** | JSON-LD export with SHACL validation | High | Very High | Benefits from all FHIR work — episode scoping, achievement_status, theme derivation. |
| **8** | **CIDS 4** | Computed impact dimensions | Medium | High | Enriched by achievement_status for nuanced depth. |
| **9** | **CIDS 5** | Conformance badge + validation reporting | Low | Medium | |
| — | **F4** | Presenting Issues (computed view) | Low | Medium | Build when a funder asks. |
| — | **F5** | Service Referrals | Medium | Medium | Build at multi-agency phase. |
| — | **F6** | Care Team | Medium | Low (now) | Build at multi-agency phase. |

### What changes in the CIDS plan

1. **`cids_theme` on MetricDefinition** (Phase 1b) → **removed.** Theme is derived at export time: `iris_metric_code` → CidsCodeList lookup (primary), taxonomy mapping (when available from Phase 2), `cids_theme_override` (admin correction).
2. **`cids_impact_theme` on PlanTarget** (Phase 1d) → **removed.** Derived from the target's metric's theme at export time.
3. **New field added:** `cids_theme_override` on MetricDefinition (blank CharField for admin edge-case correction).
4. **`outcome_domain` on MetricDefinition, Program, PlanTarget** → **removed.** `MetricDefinition.category` (7 values) retained unchanged for UI grouping only. External taxonomy mappings handled by taxonomy mapping layer in Phase 2.
5. **`cids:Activity` computation** (Phase 3) → enhanced by ServiceEpisode. Encounter counts scoped to episodes, not just date ranges.
6. **`cids:BeneficialStakeholder` cohort definition** (Phase 3) → enriched by episode_type and end_reason. Can define cohorts as "new intakes" vs. "re-enrolments" vs. "all active."
7. **`cids:ImpactDepth` computation** (Phase 4) → enriched by achievement_status and `first_achieved_at` for time-to-achievement and nuanced depth reporting.

All other CIDS plan elements are unchanged.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Migration corrupts enrolment data | Very Low | High | Extend-in-place means no data copying — just adding nullable columns. Dry-run on staging. |
| Workers don't fill in discharge reason | Medium | Medium | Required radio buttons in discharge modal, not optional text |
| Achievement status computation produces misleading results | Medium | Medium | "Auto" badge; worker override; 3-point trend; documented sparse data rules |
| `not_attainable` auto-computed inappropriately | None | High | Never auto-computed — always requires deliberate worker action |
| Over-engineering: models nobody uses | Medium | Low | Build F1+F2 only; defer F4-F6 until triggered |
| ServiceEpisode adds complexity to existing queries | Very Low | Low | Extend-in-place with class alias — all existing references continue working unchanged |
| Three-tier theme derivation has gaps | Low | Low | `cids_theme_override` provides admin escape hatch for any metric that maps incorrectly |

---

## What Staff Experience Changes

| Who | What Changes | How Much Disruption |
|---|---|---|
| **Caseworkers** | Discharge modal has a "Why?" question (5-6 radio buttons) | Minimal — one new question |
| **Caseworkers** | Achievement status shown on plan view with "(auto)" badge | No action required — informational |
| **Program Managers** | New reporting filters: episode type, end reason, achievement status | Positive — better data |
| **Admins** | CIDS metadata visible in admin settings (auto-populated from config templates) | Minimal — no action required |
| **Everyone else** | Nothing | No change |

---

## What This Does NOT Require

- **No FHIR server or FHIR API.** Plain Django models.
- **No FHIR validation or SHACL shapes.** No terminology bindings.
- **No new data entry for frontline staff** (except the discharge reason question).
- **No breaking changes to existing views.** ServiceEpisode extends ClientProgramEnrolment in place with a class alias — all existing code continues working.
- **No external dependencies.** No new Python packages.
- **No changes to existing ProgressNote, MetricValue, or MetricDefinition models** (except adding CIDS metadata fields to MetricDefinition and `achievement_status` to PlanTarget). `MetricDefinition.category` is unchanged.

---

## References

### FHIR R4 Resources Used
- [EpisodeOfCare](https://hl7.org/fhir/R4/episodeofcare.html) — status state machine, statusHistory pattern
- [Goal](https://hl7.org/fhir/R4/goal.html) — achievementStatus vocabulary
- [Encounter](https://hl7.org/fhir/R4/encounter.html) — participant roles
- [Condition](https://hl7.org/fhir/R4/condition.html) — presenting issues pattern

### Gravity Project (SDOH)
- [Gravity Project](https://thegravityproject.net/) — SDOH categories and workflows
- [SDOH Clinical Care IG](https://hl7.org/fhir/us/sdoh-clinicalcare/) — FHIR profiles for social services
- [FHIR Human Services Directory IG](https://build.fhir.org/ig/HL7/FHIR-IG-Human-Services-Directory/)

### Canadian Context
- [Canadian FHIR Baseline](https://github.com/HL7-Canada/ca-baseline) — healthcare only, no social services profile yet
- No dedicated Canadian social services FHIR profile exists as of February 2026

### KoNote Internal
- [CIDS Implementation Plan](tasks/cids-json-ld-export.md)
- [CIDS Validation Report](tasks/cids-plan-validation.md)
- [Circles DRR](tasks/design-rationale/circles-family-entity.md) — deferred FHIR codes on relationship types
- [What KoNote Is](docs/archive/what-konote-is.md) — "not an EHR/EMR" boundary
