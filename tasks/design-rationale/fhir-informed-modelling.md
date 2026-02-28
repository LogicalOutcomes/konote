# FHIR-Informed Data Modelling — Design Rationale

**Created:** 2026-02-27
**Expert panel:** 5 experts, 3 rounds, consensus reached
**Review panel:** 4 experts, 3 rounds — 5 revisions incorporated 2026-02-27
**Taxonomy panel:** 4 experts, 3 rounds — outcome_domain removed 2026-02-27
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

### DO NOT hardcode an internal outcome taxonomy (added 2026-02-27)

**Why it seems like a good idea:** "If every metric and program has a domain (housing, employment, mental_health…), we can group outcomes, derive CIDS themes, and compute presenting issues automatically."

**Why it was rejected:**

1. **Every funder has a different taxonomy.** United Way uses "Poverty to Possibility" domains. PHAC uses population health categories. Provincial ministries use program-area codes. A housing stability program might report under "housing" to one funder, "poverty reduction" to another, and "community safety" to a third.

2. **It's not just funders.** Partners, collaborations, and sector networks all use different classification systems. A single internal taxonomy cannot serve as a Rosetta Stone.

3. **One metric maps to many indicators.** A PHQ-9 score maps simultaneously to PHAC's "mental health," United Way's "individual wellbeing," CIDS's IRIS Health theme, and SDG Goal 3. A single CharField cannot represent this.

4. **The sector has tried and failed.** Canadian nonprofits have attempted taxonomy standardisation for years. No consensus exists, and building a system that assumes one will emerge is a design error.

5. **`custom` becomes the default.** Any hardcoded taxonomy will be too coarse for most programs, causing agencies to select "custom/other" for 80%+ of their metrics — rendering the taxonomy useless for reporting.

**Expert panel:** 4 experts (Nonprofit Evaluation Specialist, Data Interoperability Specialist, Product Designer, Systems Architect), 3 rounds, unanimous consensus. GK (nonprofit evaluation consultant) confirmed: "every single funder has a different taxonomy. We have tried for years to get people in the non-profit sector to settle on a taxonomy, and it's not possible."

**Instead:**
- **Keep `MetricDefinition.category`** (7 values) for internal admin UI grouping — it works, nobody cares about it beyond filtering
- **Use `TaxonomyMapping` model** for external taxonomy compliance — a metric can have multiple mappings to different external taxonomies (CIDS IRIS, United Way, PHAC, etc.), each optionally scoped to a funder/partner relationship
- **Populate via config templates** — per-funder templates pre-map metrics to that funder's taxonomy during onboarding

**When to reconsider:** Never. This is a fundamental reality of the Canadian nonprofit sector, not a temporary coordination problem.

---

## Decided Trade-offs

### Replace vs. extend ClientProgramEnrolment
- **Chosen (revised):** Extend in place — keep `db_table`, add fields, alias old class name
- **Trade-off:** Old class name persists as alias (minor naming clutter)
- **Reason:** Eliminates the mass query rewrite risk entirely. All existing imports, foreign keys, and queries continue working. ServiceEpisode is the new class name; `ClientProgramEnrolment = ServiceEpisode` is the alias.
- **Mitigation:** Dry-run migrations on staging. The alias can be removed in a future cleanup pass once all references are updated.
- **Why the original approach (full replacement) was rejected:** The review panel identified that touching every view, template, and query that references ClientProgramEnrolment is a large blast radius for a team doing AI-assisted development. Extend-in-place achieves the same data model with near-zero disruption.
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

### ~~Unified domain taxonomy~~ → Taxonomy-neutral platform with mapping layer (revised 2026-02-27)
- **Original (review panel):** `outcome_domain` (14 values) for internal use. CIDS Theme derived at export time via three-tier approach.
- **Revised (taxonomy panel):** **Remove `outcome_domain` entirely.** Keep `MetricDefinition.category` (7 values) for UI grouping only. Add `TaxonomyMapping` model for external taxonomy compliance. CIDS Theme derived via: (1) `iris_metric_code` → CidsCodeList lookup (precise); (2) explicit taxonomy mapping (when available); (3) `cids_theme_override` (admin override).
- **Why the revision:** GK (nonprofit evaluation consultant) identified that every funder, partner, and collaboration uses a different taxonomy. A 4-expert taxonomy panel confirmed this is unfixable — the sector has tried for years. A hardcoded internal taxonomy would result in 80%+ "custom" selections, rendering it useless.
- **Trade-off:** No internal domain vocabulary means presenting issues (Phase F4) must be computed from program enrolment and metric categories rather than domain codes. This is less precise but avoids false precision.
- **Domains:** Standards, Data Model, Evaluation

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
| Achievement status unreliable with sparse data (1-2 points) | Medium | Low | Track percentage of goals with <3 data points | Document in reporting: "based on limited data" badge for goals with <3 points; full trend requires 3+ |
| `not_attainable` misused by workers | Low | Medium | Monitor frequency and review with PM | Never auto-computed; requires deliberate worker action; review in supervision |
| Taxonomy mapping layer adds complexity to config templates | Low | Low | Monitor how many mappings per template | Config templates handle bulk mapping; admin UI provides override |

---

## Graduated Complexity Path

### Phase 1 (current plan): Core models
- CIDS metadata fields + OrganizationProfile
- Taxonomy mapping layer (multi-funder, multi-taxonomy)
- ServiceEpisode with statusHistory
- Goal Achievement Status (auto-computed)
- Encounter Participant Role (auto-filled)

### Phase 2 (triggered by need): Referrals and computed presenting issues
- **Trigger:** A funder asks "how many referrals?" or "outcomes by presenting issue"
- ServiceReferral model
- Computed presenting issues view (from program enrolment + metric categories)

### Phase 3 (triggered by multi-agency): Teams and explicit presenting issues
- **Trigger:** Multi-tenancy phase or multi-disciplinary team requirement
- CareTeam model
- ClientPresentingIssue model (explicit override layer)
- RelationshipType table on CircleMembership (deferred from circles DRR)
- FHIR export capability (if health system integration needed)
