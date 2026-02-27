# FHIR-Informed Data Modelling — Design Rationale

**Created:** 2026-02-27
**Expert panel:** 5 experts, 3 rounds, consensus reached
**Implementation plan:** tasks/fhir-informed-data-modelling.md

---

## Core Decision: Borrow FHIR Concepts Without FHIR Compliance

**Chosen:** Use FHIR's data relationships, status vocabularies, and structural patterns as Django models. No FHIR server, validation, or API compliance.

**Why:** FHIR's resource model is the product of thousands of hours of domain analysis for tracking service episodes, goals, encounters, and team composition. Ignoring that work and designing from scratch would be foolish. But full FHIR compliance (terminology bindings, SHACL-like validation, RESTful API conformance) serves clinical healthcare interoperability — not a nonprofit outcome tracker.

**Trade-off:** If KoNote ever needs to exchange data with a healthcare system via FHIR, we'll need an export translation layer. But the internal models will already use FHIR-compatible vocabulary, so the mapping will be straightforward.

**Domains:** Architecture, Interoperability, Scope

---

## Anti-Patterns (Things Explicitly Rejected)

### DO NOT implement a FHIR server or FHIR RESTful API

**Why it seems like a good idea:** "If we're using FHIR concepts, why not go all the way? Then we're interoperable with health systems."

**Why it was rejected:**

1. **KoNote is not an EHR/EMR.** This boundary is explicit (docs/archive/what-konote-is.md). Adding a FHIR API pulls KoNote toward clinical territory with clinical compliance requirements (HL7 certification, terminology bindings, capability statements).

2. **No consumer exists.** No Canadian health authority or EMR system has asked to receive data from a nonprofit outcome tracker via FHIR. Building an API with no consumer is waste.

3. **Compliance overhead is enormous.** FHIR conformance requires: mandatory terminology bindings (SNOMED-CT, LOINC), resource validation, search parameter support, capability statements, and conformance testing. This is months of work that serves zero current users.

**When to reconsider:** When a specific health system integration partner requests FHIR data exchange. At that point, build a FHIR export layer (similar to the CIDS JSON-LD export) rather than making the internal models FHIR-native.

### DO NOT use FHIR CodeableConcept wrapper structures

**Why it seems like a good idea:** FHIR wraps every coded value in a `CodeableConcept` object with `coding` (system + code + display) and `text`. This enables multiple coding systems for the same concept.

**Why it was rejected:** Django CharFields with documented value sets are simpler, faster, and sufficient. KoNote uses one coding system per field (our own). The CodeableConcept wrapper adds complexity without value for internal storage.

**Instead:** Use CharField with choices. Document the FHIR mapping in the implementation plan so export layers can construct CodeableConcepts if needed.

### DO NOT add presenting issues as a mandatory intake field

**Why it seems like a good idea:** Structured needs assessment enables "outcomes relative to presenting needs" reporting. Funders increasingly want this.

**Why it was rejected:**

1. **Adoption killer.** Community nonprofit intake is often a kitchen table conversation, not a structured clinical assessment. Requiring coded presenting issues at intake will either (a) block client creation behind a form that workers skip, or (b) produce garbage data ("Other" selected 80% of the time).

2. **The data already exists.** A client enrolled in a housing program with housing stability goals has a presenting issue of housing instability. Deriving this from existing data avoids double-entry.

3. **The Gravity Project's screening tools assume a healthcare context.** Their SDOH screening (e.g., the AHC-HRSN) is designed for clinical settings where patients complete a questionnaire. Most community nonprofits don't run formal screening tools.

**Instead:** Compute presenting issues from program enrolment + plan target domains. Add explicit tagging only when a specific funder requires it, and make it a program manager task (post-hoc), not a caseworker task (at intake).

**When to reconsider:** When an agency adopts a formal screening tool (e.g., SDOH screening) as part of their intake process. At that point, the screening responses become the presenting issues.

### DO NOT build Care Team before multi-agency phase

**Why it seems like a good idea:** FHIR CareTeam tracks the group of providers supporting a client, with roles and time periods.

**Why it was rejected for now:**

1. **Most small nonprofits have 1-2 workers per client.** The `primary_worker` field on ServiceEpisode covers this.

2. **Care Team becomes valuable in multi-disciplinary or multi-agency settings.** That's the multi-tenancy phase, not now.

3. **Building it now creates empty tables** that nobody populates, and views that show "Care Team: (none)" — which looks like the system is incomplete.

**When to reconsider:** When multi-agency collaboration begins (multi-tenancy phase) or when agencies report that multiple workers routinely share clients and need to coordinate.

### DO NOT ask workers to select their role when writing a note

**Why it seems like a good idea:** Captures role-at-time-of-service for accurate historical reporting.

**Why it was rejected as a user action:** Any additional field on the progress note form reduces compliance. Workers write notes quickly between sessions.

**Instead:** Auto-fill `author_role` from `UserProgramRole` at note creation time. The worker never sees or selects this field. If they have multiple roles across programs, use the role for `author_program`.

### DO NOT let workers select episode type

**Why it seems like a good idea:** Workers know whether this is a new intake or a return.

**Why it was rejected:** The system knows this better than the worker. Check for prior episodes in the same program → if none, it's `new_intake`. If a prior finished episode exists, it's `re_enrolment`. If the most recent episode in another program ended with `transferred`, it's `transfer_in`. Workers get it wrong or pick whatever is fastest.

**Instead:** Auto-derive from episode history. Display on the client profile as informational ("Re-enrolment — previously served Jan-Aug 2024").

---

## Decided Trade-offs

### Replace vs. extend ClientProgramEnrolment
- **Chosen:** Replace with ServiceEpisode via data migration
- **Trade-off:** Migration risk; all queries touching ClientProgramEnrolment need updating
- **Reason:** ServiceEpisode is a strict superset. Maintaining both creates divergence and confusion about which is authoritative.
- **Mitigation:** Keep old table for one release cycle; thorough search-and-replace; dry-run migration on staging
- **Domains:** Architecture, Migration

### Single achievement_status field vs. separate lifecycle + achievement
- **Chosen:** Keep existing `status` (lifecycle: active/completed/deactivated) and add `achievement_status` (progress: improving/worsening/etc.) as a separate field
- **Trade-off:** Two status fields on PlanTarget
- **Reason:** They answer different questions. "Is this goal still being worked on?" (status) vs. "How is the client doing on this goal?" (achievement_status). Conflating them loses information.
- **Domains:** Data Model, Reporting

### Auto-compute achievement status vs. worker-assessed only
- **Chosen:** Auto-compute with worker override
- **Trade-off:** Auto-computation may sometimes be wrong (one good data point after a decline shows "improving" when the trend is actually down)
- **Reason:** Eliminates data entry burden; most workers won't assess achievement status if it's a separate field
- **Mitigation:** 3-point trend analysis (not single-point); "(auto)" badge; worker override with `achievement_status_source` tracking
- **Domains:** Data Quality, UX, Reporting

### Unified domain taxonomy vs. separate CIDS themes and FHIR categories
- **Chosen:** One taxonomy (`outcome_domain`) serving CIDS export, FHIR-informed tracking, and internal reporting
- **Trade-off:** Some loss of granularity (CIDS IRIS Impact Theme has 25+ categories; our taxonomy has 14)
- **Reason:** Two overlapping taxonomies that don't quite map creates confusion. One field that maps to both standards is cleaner.
- **Mitigation:** The CIDS export layer can map `outcome_domain` to the nearest IRIS Impact Theme code; `custom` domain catches anything that doesn't fit
- **Domains:** Standards, Data Model

### Discharge reason as required vs. optional
- **Chosen:** Required (radio buttons in discharge modal)
- **Trade-off:** One more step in the discharge workflow
- **Reason:** The distinction between "completed" and "withdrew" is the single most important data point for program evaluation. Without it, completion rates are meaningless.
- **Mitigation:** Radio buttons (not a text field) — 2 seconds of effort. "Other" option with optional text for edge cases.
- **Domains:** Data Quality, UX, Evaluation

---

## Risk Registry

| Risk | Likelihood | Impact | Monitoring | Mitigation |
|---|---|---|---|---|
| Workers choose the first discharge reason without thinking | Medium | Medium | Check distribution — if >80% are "completed," the data is suspect | Review discharge reason distribution quarterly; add "Are you sure?" confirmation for "completed" if the client has no achieved goals |
| Achievement status auto-computation creates false confidence | Medium | Medium | Compare auto-computed vs. worker-overridden achievement status rates | Log overrides; if >20% are overridden, the algorithm needs tuning |
| Episode history gets complex for long-term clients | Low | Low | Monitor clients with >3 episodes | Acceptable complexity — these are the exact clients funders ask about |
| Unified domain taxonomy is too coarse for some programs | Low | Low | Track how often `custom` domain is selected | Add new domains as patterns emerge; keep the list under 20 |

---

## Graduated Complexity Path

### Phase 1 (current plan): Core models
- ServiceEpisode with statusHistory
- Unified Outcome Domain taxonomy
- Goal Achievement Status (auto-computed)
- Encounter Participant Role (auto-filled)

### Phase 2 (triggered by need): Referrals and computed presenting issues
- **Trigger:** A funder asks "how many referrals?" or "outcomes by presenting issue"
- ServiceReferral model
- Computed presenting issues view (from domains)

### Phase 3 (triggered by multi-agency): Teams and explicit presenting issues
- **Trigger:** Multi-tenancy phase or multi-disciplinary team requirement
- CareTeam model
- ClientPresentingIssue model (explicit override layer)
- RelationshipType table on CircleMembership (deferred from circles DRR)
- FHIR export capability (if health system integration needed)
