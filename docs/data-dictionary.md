# KoNote Data Dictionary

A reference mapping KoNote's data model to FHIR R4 resource definitions. KoNote borrows FHIR's vocabulary and relationship patterns for outcome tracking without requiring FHIR compliance.

For the design rationale behind this approach, see `tasks/design-rationale/fhir-informed-modelling.md`.

---

## How to Read This Document

Each section covers a KoNote entity and maps its fields to the corresponding FHIR R4 resource. Fields marked **auto** are populated automatically by the system — staff never interact with them directly.

**Legend:**
- **PII** = Personally identifiable information (encrypted at rest)
- **Auto** = Auto-populated on save or by management command
- **Admin** = Configurable by agency administrators

---

## Service Episode (FHIR: EpisodeOfCare)

Tracks a participant's enrolment in a program from intake to discharge.

**Django model:** `apps.clients.models.ServiceEpisode`
**Database table:** `client_program_enrolments`

| KoNote Field | Type | FHIR R4 Mapping | Population | Description |
|---|---|---|---|---|
| `client_file` | FK → ClientFile | EpisodeOfCare.patient | Staff | The participant |
| `program` | FK → Program | EpisodeOfCare.managingOrganization | Staff | The program providing service |
| `status` | CharField | EpisodeOfCare.status | Staff/System | planned, waitlist, active, on_hold, finished, cancelled |
| `episode_type` | CharField | EpisodeOfCare.type | Auto | new_intake, re_enrolment, transfer_in, crisis, short_term |
| `primary_worker` | FK → User | EpisodeOfCare.careManager | Staff | Assigned case worker |
| `referral_source` | CharField | ServiceRequest (simplified) | Staff | self, family, agency_internal, agency_external, healthcare, school, court, shelter, community, other |
| `started_at` | DateTime | EpisodeOfCare.period.start | Auto | When active service began |
| `ended_at` | DateTime | EpisodeOfCare.period.end | System | When service ended |
| `end_reason` | CharField | — | Staff | completed, goals_met, withdrew, transferred, referred_out, lost_contact, moved, ineligible, deceased, other |
| `enrolled_at` | DateTime | — | Auto | When the record was created |

**Status history:** Each status change is recorded in `ServiceEpisodeStatusChange` (maps to FHIR EpisodeOfCare.statusHistory), with the new status, reason, who changed it, and when.

---

## Goal / Outcome Target (FHIR: Goal)

A specific outcome a participant is working toward within their plan.

**Django model:** `apps.plans.models.PlanTarget`
**Database table:** `plan_targets`

| KoNote Field | Type | FHIR R4 Mapping | Population | Description |
|---|---|---|---|---|
| `name` | Encrypted text | Goal.description | Staff | Name of the goal |
| `description` | Encrypted text | Goal.description (detail) | Staff | Worker's clinical description |
| `client_goal` | Encrypted text | Goal.description (patient) | Staff | Participant's own words about this goal |
| `status` | CharField | Goal.lifecycleStatus | Staff | default (Active), on_hold, completed, deactivated |
| `achievement_status` | CharField | Goal.achievementStatus | Auto | in_progress, improving, worsening, no_change, achieved, sustaining, not_achieved, not_attainable |
| `achievement_status_source` | CharField | — | Auto | auto_computed or worker_assessed |
| `first_achieved_at` | DateTime | — | Auto | When achievement_status first became "achieved" (never cleared) |
| `goal_source` | CharField | Goal.source | Auto | participant, worker, joint, funder_required — classified from description/client_goal field patterns |
| `goal_source_method` | CharField | — | Auto | How goal_source was derived (heuristic, worker_set, ai_inferred) |
| `target_date` | Date | Goal.target.due | Auto/Admin | Target completion date — auto-set from Program.default_goal_review_days |
| `cids_outcome_uri` | CharField | — | Admin | CIDS outcome identifier for standards reporting |
| `plan_section` | FK → PlanSection | CarePlan (implicit) | Staff | Which plan section this goal belongs to |
| `metrics` | M2M → MetricDefinition | Goal.target.measure | Staff | Measurement instruments linked to this goal |

**Achievement status derivation:** Computed from the last 3 metric values (quantitative goals) or progress descriptors (qualitative goals). See `tasks/fhir-informed-data-modelling.md` Phase F2 for the full algorithm.

**ACTIVE_STATUSES constant:** `["default", "on_hold"]` — used in queries to mean "goals still in play." Metric collection uses `status="default"` only (on-hold goals skip metric entry).

---

## Plan Section (FHIR: CarePlan)

A grouping of goals within a participant's plan (e.g., "Housing Goals", "Employment Goals").

**Django model:** `apps.plans.models.PlanSection`
**Database table:** `plan_sections`

| KoNote Field | Type | FHIR R4 Mapping | Population | Description |
|---|---|---|---|---|
| `name` | CharField | CarePlan.title | Staff | Section name |
| `status` | CharField | CarePlan.status | Staff | default (Active), completed, deactivated |
| `program` | FK → Program | CarePlan.category | Staff | Which program this section belongs to |
| `client_file` | FK → ClientFile | CarePlan.subject | Staff | The participant |

---

## Progress Note / Encounter (FHIR: Encounter)

A record of a service interaction with a participant.

**Django model:** `apps.notes.models.ProgressNote`
**Database table:** `progress_notes`

| KoNote Field | Type | FHIR R4 Mapping | Population | Description |
|---|---|---|---|---|
| `client_file` | FK → ClientFile | Encounter.subject | Staff | The participant |
| `author` | FK → User | Encounter.participant.actor | Staff | Who wrote the note |
| `author_program` | FK → Program | Encounter.serviceProvider | Staff | Program context for this encounter |
| `author_role` | CharField | Encounter.participant.type | Auto | Role at time of service (from UserProgramRole) |
| `episode` | FK → ServiceEpisode | Encounter.episodeOfCare | Auto | Service episode this encounter belongs to |
| `interaction_type` | CharField | Encounter.type | Staff | session, group, phone, sms, email, collateral, home_visit, admin, other |
| `modality` | CharField | Encounter.class | Staff | in_person, phone, video, email_text |
| `duration_minutes` | Integer | Encounter.length | Staff | Session duration |
| `begin_timestamp` | DateTime | Encounter.actualPeriod.start | Staff | When the session started |
| `status` | CharField | Encounter.status | Staff | default (Active), cancelled |
| `notes_text` | Encrypted text | — (PII) | Staff | Quick note content |
| `summary` | Encrypted text | — (PII) | Staff | Session summary |
| `participant_reflection` | Encrypted text | — (PII) | Staff | Participant's own words |
| `participant_suggestion` | Encrypted text | — (PII) | Staff | Participant's suggestion for improvement |
| `engagement_observation` | CharField | — | Staff | disengaged, motions, guarded, engaged, valuing, no_interaction |
| `alliance_rating` | Integer (1-5) | — | Staff/Participant | Working relationship quality |
| `follow_up_date` | Date | — | Staff | When to follow up |

**Episode auto-linking:** On save, the system looks up the active ServiceEpisode for the note's client + author_program and links automatically. Historical notes are backfilled using date-range matching via `backfill_fhir_metadata --episodes`.

---

## Metric Definition (FHIR: ObservationDefinition)

A reusable measurement instrument that can be linked to goals.

**Django model:** `apps.plans.models.MetricDefinition`
**Database table:** `metric_definitions`

| KoNote Field | Type | FHIR R4 Mapping | Population | Description |
|---|---|---|---|---|
| `name` | CharField | ObservationDefinition.title | Admin | Instrument name (e.g., "PHQ-9", "Housing Stability Scale") |
| `metric_type` | CharField | ObservationDefinition.permittedDataType | Admin | scale, achievement, open_text |
| `category` | CharField | — | Admin | UI grouping: mental_health, housing, employment, substance_use, youth, general, client_experience, custom |
| `evidence_type` | CharField | — | Admin | self_report, staff_observed, administrative_record, third_party_assessed, coded_qualitative |
| `iris_metric_code` | CharField | — | Admin | CIDS IRIS indicator code |
| `sdg_goals` | JSONField | — | Admin | UN Sustainable Development Goal mappings |
| `cids_theme_override` | CharField | — | Admin | Override for auto-derived CIDS theme |

---

## Metric Value (FHIR: Observation)

A single measurement recorded during a progress note.

**Django model:** `apps.notes.models.MetricValue`
**Database table:** `metric_values`

| KoNote Field | Type | FHIR R4 Mapping | Population | Description |
|---|---|---|---|---|
| `metric_definition` | FK → MetricDefinition | Observation.code | System | Which instrument was measured |
| `value` | CharField | Observation.value | Staff | The recorded value |
| `progress_note_target` | FK → ProgressNoteTarget | Observation.encounter (indirect) | System | Links to the note + goal context |

---

## Program (FHIR: Organization subset)

An organisational unit delivering services.

**Django model:** `apps.programs.models.Program`
**Database table:** `programs`

| KoNote Field | Type | FHIR R4 Mapping | Population | Description |
|---|---|---|---|---|
| `name` | CharField | Organization.name | Admin | Program name |
| `service_model` | CharField | — | Admin | individual, group, both |
| `default_goal_review_days` | Integer | — | Admin | Default target_date offset for goals in this program |
| `cids_sector_code` | CharField | — | Admin | CIDS sector classification |
| `population_served_codes` | JSONField | — | Admin | CIDS population codes |
| `funder_program_code` | CharField | — | Admin | Funder-assigned program code |

---

## Participant (FHIR: Patient)

A person receiving services. All identifying fields are encrypted at rest.

**Django model:** `apps.clients.models.ClientFile`
**Database table:** `client_files`

| KoNote Field | Type | FHIR R4 Mapping | Population | Description |
|---|---|---|---|---|
| `first_name` | Encrypted text | Patient.name.given | Staff | PII — encrypted |
| `preferred_name` | Encrypted text | Patient.name.text | Staff | PII — encrypted |
| `last_name` | Encrypted text | Patient.name.family | Staff | PII — encrypted |
| `birth_date` | Encrypted text | Patient.birthDate | Staff | PII — encrypted |
| `phone` | Encrypted text | Patient.telecom | Staff | PII — encrypted |
| `email` | Encrypted text | Patient.telecom | Staff | PII — encrypted |
| `status` | CharField | — | System | active, inactive, discharged |

---

## Reporting Queries Enabled by FHIR Metadata

The auto-populated FHIR metadata fields enable these report queries without additional data entry:

| Report Question | Query Approach | Fields Used |
|---|---|---|
| Service hours per episode | SUM(duration_minutes) grouped by episode | ProgressNote.episode, duration_minutes |
| Contacts per episode | COUNT(notes) grouped by episode | ProgressNote.episode |
| Service intensity for completers vs. dropouts | Compare hours/contacts for finished episodes by end_reason | episode, end_reason, duration_minutes |
| Were goals participant-driven? | COUNT by goal_source | PlanTarget.goal_source |
| Goal source distribution | VALUES(goal_source).annotate(count) | PlanTarget.goal_source |
| Goals achieved on time | first_achieved_at <= target_date | PlanTarget.first_achieved_at, target_date |
| Average time to achievement | AVG(first_achieved_at - created_at) | PlanTarget.first_achieved_at, created_at |
| New vs. returning participants | COUNT by episode_type | ServiceEpisode.episode_type |
| Completion rate | finished episodes with end_reason in (completed, goals_met) / total finished | ServiceEpisode.end_reason |
| Currently on hold (goals) | PlanTarget.status = "on_hold" | PlanTarget.status |

---

## Standards Alignment

| Standard | KoNote Coverage | How |
|---|---|---|
| **FHIR R4** | Data definitions only (no FHIR server/API) | Field names, value sets, and relationships borrowed from FHIR resources |
| **CIDS** | Metadata + JSON-LD export | iris_metric_code, sdg_goals, cids_outcome_uri on models; export via CIDS phases |
| **PHIPA** | Consent enforcement | Cross-program note visibility controlled by agency/participant consent settings |
| **PIPEDA** | Privacy by design | Fernet encryption for PII, audit logging, small-cell suppression in reports |
| **WCAG 2.2 AA** | Accessibility | Semantic HTML, colour contrast, keyboard navigation, screen reader support |
| **AODA** | Ontario accessibility | Built on WCAG 2.2 AA compliance |

---

## Management Commands

| Command | Purpose | When to Run |
|---|---|---|
| `backfill_fhir_metadata --all` | Populate episode FK and goal_source on existing records | After deploying FHIR metadata fields |
| `backfill_fhir_metadata --episodes` | Link existing notes to episodes only | After fixing episode data |
| `backfill_fhir_metadata --goals` | Classify goal_source on existing targets only | After fixing goal data |
| All commands support `--dry-run` | Preview changes without saving | Before any backfill |
