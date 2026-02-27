# FHIR-Informed Data Modelling — Implementation Plan

**Task ID:** FHIR-DATA1
**Created:** 2026-02-27
**Status:** Draft — awaiting GK review
**Depends on:** Should be built BEFORE CIDS Phase 1 (see Sequencing section)
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
4. **The unified domain taxonomy should be designed before CIDS Phase 1.** One vocabulary serving three purposes (CIDS export, FHIR-informed tracking, internal reporting).
5. **Presenting issues should be computed from existing data**, not a new data entry requirement.
6. **Episode type should be auto-derived from history**, not worker-entered.
7. **Discharge reason is the one new question workers answer.** A single question ("Why is this person leaving?") with 5-6 radio buttons.

### Priority order (expert consensus):

ServiceEpisode ≫ Unified Domain Taxonomy ≫ Goal Achievement Status ≫ Encounter Role > Presenting Issues (computed) > Referral Tracking > Care Team

---

## Implementation Phases

### Phase F0: Unified Outcome Domain Taxonomy (foundation for both FHIR and CIDS)

**Do this before CIDS Phase 1.** Both CIDS themes and FHIR Goal categories need a shared domain vocabulary. Design it once, use it everywhere.

#### New code list: `OutcomeDomain` (stored in CidsCodeList)

| Domain Code | Display Label (EN) | Display Label (FR) | CIDS IRISImpactTheme | Gravity SDOH Category | Current MetricDef Category |
|---|---|---|---|---|---|
| `housing` | Housing & Shelter | Logement et hébergement | IRIS Housing | Housing Instability | `housing` |
| `employment` | Employment & Income | Emploi et revenu | IRIS Employment | Employment Status | `employment` |
| `mental_health` | Mental Health & Wellbeing | Santé mentale et bien-être | IRIS Health | — | `mental_health` |
| `substance_use` | Substance Use | Consommation de substances | IRIS Health | — | `substance_use` |
| `food_security` | Food Security | Sécurité alimentaire | IRIS Basic Needs | Food Insecurity | — |
| `education` | Education & Training | Éducation et formation | IRIS Education | Education Access | — |
| `social_connection` | Social Connection | Liens sociaux | IRIS Community | Social Isolation | — |
| `financial` | Financial Stability | Stabilité financière | IRIS Financial | Financial Strain | — |
| `safety` | Safety & Protection | Sécurité et protection | — | Intimate Partner Violence | — |
| `youth` | Youth Development | Développement des jeunes | IRIS Youth | — | `youth` |
| `transportation` | Transportation | Transport | — | Transportation Insecurity | — |
| `legal` | Legal & Justice | Justice et droit | — | — | — |
| `health` | Physical Health | Santé physique | IRIS Health | — | — |
| `custom` | Other | Autre | — | — | `custom`, `general` |

#### Changes to existing models

**MetricDefinition:** Replace `category` (CharField with 7 choices) with `outcome_domain` (CharField referencing OutcomeDomain codes). Data migration maps existing values:
- `mental_health` → `mental_health`
- `housing` → `housing`
- `employment` → `employment`
- `substance_use` → `substance_use`
- `youth` → `youth`
- `general` → `custom` (review individually during migration)
- `custom` → `custom`

**Program:** Add `outcome_domain` (CharField, blank=True). What domain does this program primarily serve? Auto-derived from the program's most common metric domains if not set.

**PlanTarget:** Add `outcome_domain` (CharField, blank=True). Inherited from the plan section's program domain or from the target's metrics. Can be overridden.

**Why this replaces `cids_theme` on MetricDefinition:** The CIDS plan (Phase 1b) proposed a separate `cids_theme` field. With the unified taxonomy, `outcome_domain` serves that purpose — the CIDS export maps `outcome_domain` to the corresponding IRIS Impact Theme code. One field, not two.

**Impact on CIDS Phase 1:** The `cids_theme` field in Phase 1b becomes unnecessary. Instead, Phase 1b adds the other CIDS-specific fields (`cids_indicator_uri`, `iris_metric_code`, `sdg_goals`, `cids_unit_description`, `cids_defined_by`, `cids_has_baseline`) and relies on `outcome_domain` for theme mapping. Similarly, `cids_impact_theme` on PlanTarget (Phase 1d) is replaced by `outcome_domain`.

---

### Phase F1: ServiceEpisode (replaces ClientProgramEnrolment)

**FHIR source:** EpisodeOfCare resource (status state machine + statusHistory pattern)

#### New model: `ServiceEpisode`

**Where it lives:** `apps/clients/models.py` (alongside existing ClientFile)

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
| `enrolled_at` | DateTimeField(auto_now_add=True) | — | When the record was created (preserves current behaviour) |
| `created_at` | DateTimeField(auto_now_add=True) | — | |
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

#### Data migration from ClientProgramEnrolment

```
For each ClientProgramEnrolment:
  → Create ServiceEpisode:
      client_file = enrolment.client_file
      program = enrolment.program
      status = "active" if enrolment.status == "enrolled" else "finished"
      started_at = enrolment.enrolled_at
      ended_at = enrolment.unenrolled_at (if unenrolled)
      episode_type = "" (unknown for historical data)
      end_reason = "" (unknown for historical data)
      enrolled_at = enrolment.enrolled_at
  → Create initial ServiceEpisodeStatusChange:
      status = episode.status
      reason = "Migrated from ClientProgramEnrolment"
      changed_at = enrolment.enrolled_at
```

**All new fields are nullable/optional.** Historical data gets enriched opportunistically; going forward, the system captures complete data.

**Migration safety:** Keep the `ClientProgramEnrolment` table for one release cycle. Add a deprecation warning to any code that queries it directly. Remove in the following release.

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

#### New field on `PlanTarget`

| Field | Type | Notes |
|---|---|---|
| `achievement_status` | CharField(max_length=20, blank=True) | Derived or worker-assessed |
| `achievement_status_source` | CharField(max_length=20, blank=True) | `auto_computed` or `worker_assessed` |
| `achievement_status_updated_at` | DateTimeField(null=True) | When last computed/assessed |

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
| `good_place` (In a good place) | `achieved` (first time) or `sustaining` (if previously achieved) |

**Fallback:** If no metrics and no progress_descriptor recorded, leave as `in_progress`.

**Computation trigger:** Recalculate when a ProgressNote is saved that includes a ProgressNoteTarget for this goal. Store the result on PlanTarget so reports can query it directly without recomputing.

**Worker override:** Achievement status is shown on the plan view with an "(auto)" badge. Workers can click to override (sets `achievement_status_source` to `worker_assessed`). Next auto-computation only overwrites if source is `auto_computed`.

#### Reporting queries enabled

```python
# "Percentage of clients showing improvement on housing goals"
housing_goals = PlanTarget.objects.filter(
    outcome_domain="housing",
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

1. **From program enrolment:** Client enrolled in a housing program (program.outcome_domain = `housing`) → presenting issue: `housing`
2. **From plan targets:** Client has a goal in the `employment` domain → presenting issue: `employment`
3. **From metrics:** Client has MetricValues for a `substance_use` metric → presenting issue: `substance_use`

#### Implementation

A Django model manager method or queryset annotation that computes presenting issues on the fly:

```python
def get_presenting_issues(client_file):
    """Compute presenting issues from program, goal, and metric domains."""
    domains = set()

    # From active episodes
    for ep in client_file.service_episodes.filter(status="active"):
        if ep.program.outcome_domain:
            domains.add(ep.program.outcome_domain)

    # From active plan targets
    for target in client_file.plan_targets.filter(status="default"):
        if target.outcome_domain:
            domains.add(target.outcome_domain)

    return sorted(domains)
```

#### Reporting queries enabled

- "How many clients present with housing needs?" → Count clients with `housing` in their computed presenting issues
- "Outcomes for clients who present with multiple needs" → Filter by clients with 2+ domains
- "Cross-domain analysis: do clients with substance use needs show different housing outcomes?" → Compare achievement_status by presenting issue combination

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

The expert panel recommended building FHIR-informed foundations *before* CIDS Phase 1, because:

1. CIDS Phase 1 adds `cids_theme` to MetricDefinition — with the unified domain taxonomy, this becomes `outcome_domain` instead (one field, not two)
2. CIDS Phase 2.5 (enriched reports) produces better output with ServiceEpisode in place
3. CIDS Phase 3 (JSON-LD export) needs `cids:Activity` counts scoped to reporting periods — ServiceEpisode makes these precise

### Revised combined sequence

| Order | Phase | What | Effort | Value |
|---|---|---|---|---|
| **1** | **F0** | Unified Outcome Domain taxonomy | Low | High — foundation for everything |
| **2** | **F1** | ServiceEpisode + StatusChange (replaces ClientProgramEnrolment) | Medium | Very High — solves reporting headaches |
| **3** | **CIDS 1** | Metadata fields on MetricDefinition, Program, PlanTarget + OrganizationProfile | Medium | High — CIDS foundation |
| **4** | **F2** | Goal Achievement Status on PlanTarget | Low | High — nuanced outcome reporting |
| **5** | **F3** | Encounter Participant Role on ProgressNote | Very Low | Medium — auto-filled, no workflow change |
| **6** | **CIDS 2** | Import CIDS code lists + admin UI dropdowns | Medium | High |
| **7** | **CIDS 2.5** | CIDS-enriched CSV/PDF reports | Low | High — immediate funder value |
| **8** | **CIDS 3** | JSON-LD export with SHACL validation | High | Very High — the differentiator |
| **9** | **CIDS 4** | Computed impact dimensions | Medium | High |
| **10** | **CIDS 5** | Conformance badge + validation reporting | Low | Medium |
| — | **F4** | Presenting Issues (computed view) | Low | Medium — build when a funder asks |
| — | **F5** | Service Referrals | Medium | Medium — build at multi-agency phase |
| — | **F6** | Care Team | Medium | Low (now) — build at multi-agency phase |

### What changes in the CIDS plan

1. **`cids_theme` on MetricDefinition** (Phase 1b) → replaced by `outcome_domain` from Phase F0. The CIDS export layer maps `outcome_domain` to the corresponding IRIS Impact Theme code.
2. **`cids_impact_theme` on PlanTarget** (Phase 1d) → replaced by `outcome_domain` from Phase F0.
3. **`cids:Activity` computation** (Phase 3) → enhanced by ServiceEpisode. Encounter counts scoped to episodes, not just date ranges.
4. **`cids:BeneficialStakeholder` cohort definition** (Phase 3) → enriched by episode_type and end_reason. Can define cohorts as "new intakes" vs. "re-enrolments" vs. "all active."
5. **`cids:ImpactDepth` computation** (Phase 4) → enriched by achievement_status for nuanced depth beyond simple "met target" percentage.

All other CIDS plan elements are unchanged.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Migration corrupts enrolment data | Low | High | Dry-run on staging database; keep old table for one release cycle |
| Workers don't fill in discharge reason | Medium | Medium | Required radio buttons in discharge modal, not optional text |
| Achievement status computation produces misleading results | Medium | Medium | "Auto" badge; worker override; 3-point trend (not single-point) |
| Unified domain taxonomy doesn't cover all programs | Low | Low | Include `custom` domain; agencies can request additions |
| Over-engineering: models nobody uses | Medium | Low | Build F0+F1+F2 only; defer F4-F6 until triggered |
| CIDS Phase 1 conflict if taxonomy not settled first | Medium | Medium | Resolve taxonomy (F0) before starting CIDS-META1 |
| ServiceEpisode adds complexity to existing queries | Low | Medium | Provide compatibility helpers; all existing ClientProgramEnrolment queries map 1:1 |

---

## What Staff Experience Changes

| Who | What Changes | How Much Disruption |
|---|---|---|
| **Caseworkers** | Discharge modal has a "Why?" question (5-6 radio buttons) | Minimal — one new question |
| **Caseworkers** | Achievement status shown on plan view with "(auto)" badge | No action required — informational |
| **Program Managers** | New reporting filters: episode type, end reason, achievement status | Positive — better data |
| **Admins** | Outcome domain dropdown on program and metric forms | Minimal — one new field |
| **Everyone else** | Nothing | No change |

---

## What This Does NOT Require

- **No FHIR server or FHIR API.** Plain Django models.
- **No FHIR validation or SHACL shapes.** No terminology bindings.
- **No new data entry for frontline staff** (except the discharge reason question).
- **No breaking changes to existing views.** ServiceEpisode is a superset of ClientProgramEnrolment.
- **No external dependencies.** No new Python packages.
- **No changes to existing ProgressNote, MetricValue, or MetricDefinition models** (except adding `outcome_domain` to MetricDefinition and `achievement_status` to PlanTarget).

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
