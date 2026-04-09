# De-Identified Microdata Export for Program Evaluation

**Date:** 2026-04-09
**Status:** Decided — GK
**Panels:** Expert panel review covering program evaluation, de-identification methodology, Indigenous and community data governance, nonprofit operations, and risk/systems analysis (multi-round).

---

## What Was Requested

External program evaluators need participant-level outcome data with demographic breakdowns to do rigorous evaluation — trajectory analysis, equity disaggregation, dose-response modelling, attrition analysis. KoNote currently offers aggregate-only template reports (which can't support individual-level analysis) and PII-containing individual exports (which include names and are too sensitive to hand to an external party). There is no middle option.

### Scope: Regular Program Evaluation, Not Research

This DRR governs the workflow for **regular program evaluation** — the everyday work of answering "is this program working, and for whom?" It does **not** attempt to serve **research-grade data access** (formal research studies, secondary data analysis, academic publication requiring complete microdata). Research-grade access is handled through an entirely separate workflow that is intentionally high-friction: a full agency export gated by ED authority, legal review, institutional data sharing agreements, and case-by-case governance. That workflow is **out of scope** for this DRR.

The practical consequence is clear and should be applied consistently: both export tiers below (EME and LTE) are designed for program evaluators who need **sufficient** data to assess outcomes, subgroup equity, dose-response, and service effectiveness — not **complete** data. An evaluator who insists on complete data (raw metric values, narrow demographics, names, or full client records) is doing research, not program evaluation, and the agency should direct them to the research workflow rather than relax the evaluation-export safeguards. This separation is deliberate: it protects participants and communities, it protects the agency from scope creep, and it gives staff a principled answer to pressure from well-meaning evaluators who "just need a bit more."

## The Decision

Build a **de-identified microdata export** — individual rows with pseudonymous IDs, generalised demographics, and outcome metric values, with all direct identifiers removed. Deliver as CSV via the existing SecureExportLink infrastructure.

This DRR defines **two** de-identified tiers sitting between template reports and PII-containing individual exports:

| Tier | What | Who | Contains PII | Population floor |
|---|---|---|---|---|
| Template reports | Aggregate metrics by demographic group | PM, Executive | No | k < 5 suppressed |
| **Evaluation Microdata Export (EME)** | **De-identified individual rows with generalised demographics and outcome metrics** | **ED / designated user** | **No (de-identified)** | **n ≥ 15, k ≥ 5** |
| **Longitudinal Trajectory Export (LTE)** | **De-identified longitudinal rows with NO demographic fields — fuzzed metric trajectories and service intensity** | **Privacy officer (separate permission)** | **No (de-identified)** | **n ≥ 10 (n ≥ 15 for OCAP- or EGAP-governed programs)** |
| Individual client export | Full client record including names | PM | Yes | n/a |
| Full agency export (research-grade, out of scope for this DRR) | Encrypted dump of everything | CLI / KoNote team | Yes | n/a |

### What Evaluators Get

- One row per participant (or per participant-per-time-point for longitudinal data)
- Pseudonymous study ID (random, not derived from real record ID)
- Demographic quasi-identifiers: age group, gender, ethnicity, geography (urban/rural) — subject to k-anonymity gating
- Program enrollment and exit (quarter/year, not exact dates)
- Service intensity: session count, total hours
- Outcome metric values at each measurement point

### What Evaluators Do NOT Get

- Names, birth dates, contact information, exact addresses
- Real record IDs
- Clinical note text
- Any direct identifier

## Why This Approach

### Why not just give evaluators the aggregate reports?

Aggregate reports answer "did the average participant improve?" They cannot answer:
- "Did outcomes differ by subgroup?" (equity analysis)
- "Did participants who attended more sessions have better outcomes?" (dose-response)
- "Who dropped out, and are they different from completers?" (attrition bias)
- "Did individual trajectories vary, or did everyone improve at the same rate?" (heterogeneity)

A weak evaluation harms participants — it fails to identify whether the program actually helps them, or whether it helps some groups and not others.

### Why not just remove names and hand over the file?

With small nonprofit populations (20-200 participants per program), demographic combinations become quasi-identifiers. A 67-year-old Indigenous woman in a rural program of 12 people is identifiable without a name. Removing direct identifiers is necessary but not sufficient.

### Why not a container / secure analysis environment?

Evaluated by the expert panel and rejected for KoNote's context:
- Every evaluator has different tools, workflows, and analysis needs — KoNote can't anticipate or support all of them
- Adds infrastructure complexity and cost disproportionate to the nonprofit market
- Agencies need to interview evaluators about their data analysis process regardless — KoNote providing an environment doesn't remove that responsibility
- The de-identification pipeline with k-anonymity enforcement makes the CSV safe enough to export

### Why not synthetic data?

Deferred to a future phase. Synthetic data preserves statistical distributions without mapping to real people, but:
- Requires validation that synthetic data preserves the analytical properties evaluators need
- Can distort the subgroup patterns that equity analysis aims to detect
- More complex to implement and explain to non-technical users
- Should be validated as a research project before being offered as a feature

## De-Identification Pipeline

The export runs a 10-step pipeline. Every step writes to the audit log.

### Step 1: Extract

Query raw data from PostgreSQL: ClientFile (encrypted PII), ServiceEpisode (enrollment/consent), ClientDetailValue (demographics), ProgressNote metrics, PlanTarget outcomes.

### Step 2: Decrypt & Stage

Decrypt PII fields in memory (never written to disk decrypted). Build a working recordset with all fields needed for the export. Names are decrypted only to build the exclusion list for output scanning — they are never included in output.

### Step 3: Consent Filter

Remove participants where `ServiceEpisode.consent_to_aggregate_reporting = False`. Consent language should be broadened to cover de-identified evaluation use: "I consent to my de-identified information being included in program reports and evaluations. No personally identifying information (name, date of birth, contact details) will be shared." No new database field needed — the existing boolean covers both aggregate and de-identified microdata.

### Step 4: Strip Direct Identifiers

Drop all direct identifiers: names, phone, email, exact birth date, real record ID. Assign pseudonymous study IDs (random, not sequential from record ID — no ordinal leakage). Store a linkage table (real ID ↔ study ID) encrypted and accessible only to agency admin, for the sole purpose of participant withdrawal requests ("remove my data from the evaluation"). Stored as encrypted JSON on the SecureExportLink record; destroyed when the link expires.

### Step 5: Generalise Quasi-Identifiers

Apply generalisation rules to reduce the specificity of demographic fields:

| Field | Generalisation |
|---|---|
| Age (from DOB) | 5-year bands (18-24, 25-29, 30-34, ...) |
| Geography (FSA) | Urban / Rural (derived from Stats Canada FSA classification) |
| Enrolment date | Quarter/Year (Q3-2025) |
| Exit date | Quarter/Year |
| Ethnicity | As collected (already categorical) |
| Gender | As collected (already categorical) |

Generalisation levels are configurable per export — tighter for smaller populations, looser for larger ones. The system enforces minimum generalisation.

### Step 6: K-Anonymity Check

For each record, compute its equivalence class (the set of records sharing identical quasi-identifier values). Report the minimum k across all classes. Target k = 5, consistent with KoNote's existing small-cell suppression threshold and CIHI Pan-Canadian De-Identification Guidelines.

### Step 7: Resolve K Violations

For each equivalence class where k < 5, apply a cascading resolution strategy:

1. **Widen** the most granular quasi-identifier (e.g., age 55-59 → 45+, merging adjacent bands until k is met)
2. If still below k after widening, **suppress** the field value (replace with null)
3. If the record is still unique after all QI generalisation, **suppress the entire record**

Constraints:
- Never widen to fewer than 2 categories (defeats the analytical purpose)
- If more than 15% of records would need suppression, **block the export** and advise fewer QI columns — the population is too small for this level of demographic detail

### Step 8: Population Threshold Gate

System-enforced minimums based on population size after consent filtering and suppression:

| Population (n) | Available Export Types |
|---|---|
| n < 15 | **Blocked.** Aggregate reports only. |
| 15 ≤ n < 30 | Microdata with maximum 3 quasi-identifier columns, k=5 enforced |
| n ≥ 30 | Full microdata with k=5 enforced, up to 5 quasi-identifier columns |

These thresholds align with Statistics Canada small-area data practices and IPC minimum cell size guidance.

### Step 9: Generate Output

Write CSV with metadata header containing: report name, program, period, generated date/by, evaluator details, population counts, suppression summary, effective k, quasi-identifiers used, generalisations applied. Create SecureExportLink with `export_type = "evaluation_microdata"`, `contains_pii = False`, `is_elevated = True` (always elevated for evaluation exports). Deliver via existing 24-hour download link.

### Step 10: Suppression Report

Generate a companion JSON file documenting: total eligible, consented, exported, suppressed counts; suppression reasons by field; generalisations applied; effective k. This file is downloadable alongside the CSV — evaluators need it to understand what was excluded and adjust their analysis accordingly.

## Access Control

### Who Can Generate Evaluation Exports

A new permission: `report.evaluation_export`. Not tied to any existing role by default — must be explicitly granted. Typically granted to the Executive Director or a designated privacy officer.

**Why not reuse the `executive` role directly?** Not every executive should generate evaluation exports. In a large agency, the board treasurer has the executive role but shouldn't be exporting de-identified microdata. A specific permission lets the agency grant it to exactly the right person.

**Why not Program Managers?** PMs can generate ad-hoc exports with PII for their own programs. Evaluation exports serve a different purpose (external sharing) with different safeguards (evaluator details, enhanced audit). Separating the permission clarifies the intent and audit trail.

### Evaluator Details (Mandatory for Audit)

The export form requires evaluator details before generation. These are stored in the audit log, not in a separate model:

- Evaluator name (required)
- Evaluator email (required)
- Evaluator organisation (required)
- Evaluation purpose (required)
- Data sharing agreement expiry date (required)

KoNote does not email the evaluator, create an evaluator account, or store/enforce the data sharing agreement document. These are metadata for the audit trail. The agency manages the evaluator relationship and agreement outside KoNote.

### What's NOT in KoNote's Scope

- **Sending the file to the evaluator** — the ED downloads it and delivers it via their own secure channel
- **Data sharing agreement management** — the expiry date is captured for audit; the agency manages the actual agreement
- **Evaluator accounts** — evaluators don't log into KoNote
- **Controlling what the evaluator does with the data** — that's governed by the data sharing agreement, not by software

## Enhanced Audit Trail

Standard report exports log a generic metadata blob. Evaluation exports log structured, detailed metadata because the data is more sensitive (de-identified individual rows vs. aggregate statistics):

```json
{
    "export_category": "evaluation_microdata",
    "evaluator_email": "dr.martinez@llewelyn.ca",
    "evaluator_name": "Dr. Ana Martinez",
    "evaluator_organisation": "Llewelyn Consulting",
    "evaluation_purpose": "Youth Employment outcome evaluation 2025-26",
    "data_sharing_agreement_expiry": "2026-04-30",
    "program_id": 7,
    "program_name": "Youth Employment",
    "period_start": "2025-09-01",
    "period_end": "2026-03-31",
    "pipeline_summary": {
        "eligible_count": 47,
        "consented_count": 42,
        "exported_count": 41,
        "suppressed_count": 1,
        "suppression_rate": 0.024,
        "effective_k": 5,
        "qi_columns": ["age_group", "gender", "geography"],
        "generalizations_applied": [
            {"field": "age_group", "original": "55-59", "widened_to": "45+"}
        ]
    }
}
```

The audit log is immutable (append-only, enforced at Django and PostgreSQL levels). If there is ever a privacy complaint, the audit entry answers: who exported what, for whom, with what de-identification applied, and under what authority.

## Longitudinal Trajectory Export (LTE) — Small-Population Tier

The LTE is a second, structurally separate export tier designed for small programs (10 ≤ n < 15) that the EME population floor would otherwise block. **It is not a relaxation of the EME.** It is a different data product with different trade-offs, gated by stronger governance, and routed through its own permission, its own form, and its own audit category.

### The Core Reframe

The EME defends against re-identification at the data layer by generalising and k-anonymising demographic quasi-identifiers, and then enforcing a population floor to prevent the quasi-identifier surface from overwhelming small populations. That approach works above n ≥ 15 but blocks evaluation of smaller programs entirely — and small programs are precisely where rigorous evaluation matters most, because they cannot fall back on aggregate averages to demonstrate impact. In very small programs, **demographic disaggregation is simultaneously statistically weak and re-identification-expensive** — claims about "women vs men" outcomes at n = 10 are noise, while the same demographic combination can uniquely identify a community member. The analytically valuable content in small-n evaluation is not subgroup breakdowns; it is:

- **Individual outcome trajectories** — intake → mid → exit paths for each participant, to see heterogeneity and response patterns
- **Service-intensity correlation** — sessions and hours correlated with metric change, to see dose-response
- **Attrition patterns** — who left, how far along, and where their trajectories were heading, to detect selection bias and drop-out signals

None of this requires demographic quasi-identifiers. The LTE therefore **drops demographics entirely** and delivers longitudinal individual rows. k-anonymity is trivially satisfied because there are no demographic fields to group on; every row is indistinguishable from every other row on any quasi-identifier. The re-identification surface shifts to the trajectory shape itself, which is addressed by fuzzing metric and service-intensity values.

### What LTE Exports

One row per participant, with the following columns:

- `study_id` — random UUID, generated fresh per export; never derived from record ID, sequence number, or any linkable pattern
- `enrolment_quarter` — quarter and year only (e.g., `Q3-2025`), never exact enrolment date
- `exit_quarter` — quarter and year only, null if still enrolled
- `sessions_count_banded` — session count rounded to the nearest 5
- `total_hours_banded` — total hours rounded to the nearest half-hour
- One column per metric per measurement point (e.g., `metric_wellbeing_intake`, `metric_wellbeing_mid`, `metric_wellbeing_exit`), with each value **rounded to the natural unit of the scale**:
  - 0–10 ordinal scales → rounded to the nearest integer
  - 0–100 percentage scales → rounded to the nearest 5
  - Continuous scales → rounded to one decimal place or the nearest unit, whichever is coarser

### What LTE Does NOT Export

- **No demographic fields of any kind.** Not age, not age band, not gender, not ethnicity, not geography, not urban/rural, not anything derived from demographics. This is a hard rule enforced at the schema layer, not a form option. The re-identification defence in LTE *is* the absence of these fields.
- **No clinical note text**, same as EME
- **No direct identifiers**, same as EME
- **No exact dates**, same as EME
- **No unrounded metric values**, even though EME permits them. Rounding is a re-identification safeguard specific to the LTE where trajectory shape could otherwise identify a socially-known participant.
- **No real record IDs**, same as EME

### Why Fuzz the Metric and Service-Intensity Values?

In the EME, demographic generalisation is the primary defence against re-identification: an evaluator looking at an EME row sees "Woman, 25–29, Urban, Q3-2025" which matches many people. In the LTE, demographic fields are gone, so the remaining re-identification surface is **the trajectory shape itself** — a known participant's approximate metric values plus their session count plus the quarter they enrolled could identify them to an evaluator who also knows participants socially (not an abstract threat — community evaluators are often themselves embedded in the community being evaluated). Rounding metric values to the natural scale unit and banding session/hour counts reduces the uniqueness of the trajectory profile at minimal analytical cost. Dose-response and trajectory analyses tolerate this rounding well because they look at the *shape* of change, not its exact magnitude.

### Population Floor

| Program type | Minimum n for LTE | Notes |
|---|---|---|
| Default | n ≥ 10 | Enforced at the form layer. No administrative waiver. |
| Programs with OCAP governance flag (First Nations, Inuit, Métis) | n ≥ 15 | Higher floor reflects the panel's finding that small Indigenous cohorts are inherently identifying at the community level. Requires community reviewer signoff in addition to the floor. |
| Programs with EGAP governance flag (Black communities) | n ≥ 15 | Same rationale. Requires community reviewer signoff in addition to the floor. |
| Programs with "other small-population community review" flag (e.g., newcomer, 2SLGBTQ+, disability community programs) | n ≥ 10 | Documented community reviewer signoff required, but the community framework is not OCAP or EGAP specifically. |
| Below the applicable floor | **Blocked.** | Direct the user to aggregate reports, or (if the use case is genuinely research) to the out-of-scope research workflow. No override. |

**The floor is system-enforced**, consistent with the existing "Advisory-only population thresholds" anti-pattern. Funders and stakeholders will pressure agencies to waive it; the system must refuse. The refusal is part of the design, not a bug to work around.

### Access Control

A **new permission**, distinct from the existing evaluation-export permission:

- `report.evaluation_export_small_population`

This permission is not bundled with `report.evaluation_export`, not granted to any default role, and not inferred from any other role. An agency admin must explicitly grant it. We strongly recommend one grantee per agency, typically the agency's privacy officer.

**Designation is a hard precondition.** If no user in the agency has been granted `report.evaluation_export_small_population`, the LTE form is unavailable to everyone — there is no "ED override" or temporary permission. Agencies that lack the governance capacity to designate a privacy officer are not ready for LTE, and the feature should not be reachable until the role is assigned. This creates constructive pressure to establish privacy governance before using the feature rather than after. Bundling this permission with the existing evaluation-export permission is an explicit anti-pattern (see Anti-Patterns section) because it erodes the "separate path, separate door" principle that keeps the LTE from becoming a default.

### Preconditions Enforced by the Form

Before generating an LTE, the form **requires** all of the following. Missing or invalid values block submission; there are no optional fields in this list.

1. **REB approval number** — a non-empty string of at least 5 characters, stored in the audit metadata. The string is not strictly format-validated because REB approval numbers vary by institution; the precondition is simply that a value is present and plausible. *(Future enhancement: verification against an external REB registry. Not required for v1.)*
2. **REB name and approval date**
3. **Data sharing agreement expiry date** — the DSA is necessary but not sufficient; it is captured because its existence is a precondition even though it does not unlock anything on its own.
4. **Evaluator name, organisation, email**
5. **Evaluator degree or certification** — structured field, required
6. **Evaluator years of evaluation experience** — numeric, required
7. **Evaluator prior programs evaluated** — free text, minimum 50 characters, required. Auditable narrative of prior work.
8. **Destruction attestation window** — 30, 60, or 90 days from download. KoNote sends a reminder email to the agency at the end of the window; the agency records the evaluator's destruction acknowledgement in the audit log **manually** (v1 has no automated evaluator acknowledgement UI — the agency enters the date on behalf of the evaluator). If no acknowledgement is recorded by the deadline, a follow-up task is auto-created for the privacy officer.
9. **Community governance flags**, where applicable:
   - **OCAP flag** — requires community reviewer name, affiliation, and signoff date
   - **EGAP flag** — requires community reviewer name, affiliation, and signoff date
   - **Other-community flag** — requires community reviewer name, affiliation, community framework description, and signoff date
10. **Purpose statement** — plain-language description of the evaluation question. This becomes part of the audit record and is printed in the CSV metadata header.
11. **Acknowledgement checkbox** — the submitter must explicitly check: *"I have read the re-identification risk notice and confirm this export is for program evaluation, not research. Research-grade data access (complete microdata, unfuzzed values, demographic detail) is handled through a separate workflow and is not available through this form."*

### Review and Cancel Window

After the form is submitted and the pipeline has prepared the export file, the download link is **inactive for 5 business days**. Business days (not calendar days) is the operational unit because it accommodates weekends, part-time privacy officers, and holidays without creating arbitrary weekend penalties for Friday submissions. Business days are defined as Monday through Friday in the agency's configured time zone, excluding any holidays the agency has configured.

The window serves three distinct purposes:

1. **Second-thought pause** for the submitter and the agency — time to notice a mistake before data leaves agency control
2. **Privacy officer review** — time for the designated privacy officer to read the export metadata, the evaluator credentials, the REB details, and the community governance signoffs, and either approve implicitly (let the window elapse), explicitly cancel, or explicitly flag concerns
3. **Distributed admin oversight** — any agency admin may cancel the export during the window; oversight is not reserved to the submitter or the privacy officer

**Countdown visibility.** The remaining window duration must be visible on the submitter's export history page and on the privacy officer's dashboard, as a clear countdown with the activation timestamp. The export must not be a black box: an invisible pause is not a pause.

**Cancellation rules.** Any agency admin may cancel the export at any time during the window. Cancellation discards the prepared file and the pipeline work; it is not a reset. The audit log retains the original submission metadata, marked "cancelled", including who cancelled and when. Re-submission after cancellation starts a fresh review-and-cancel window — there is no "resume" or "modify-and-continue" path.

**Withdrawal during the window.** If a participant withdraws their consent during the review-and-cancel window, the export is automatically invalidated and must be re-run. The prepared file is discarded. The pipeline is re-executed against the current consent state, and a new review-and-cancel window begins. This ensures withdrawn participants never appear in the final output even if the pipeline ran before their withdrawal was recorded.

**Population changes during the window.** The export is a snapshot at submission time, not at download time. New enrolments during the window do not enter the file. Consent withdrawals do remove rows (see above). If withdrawals drop the population below the applicable floor, the export is cancelled automatically and the submitter is notified.

**Link expiry after activation.** Once the review-and-cancel window elapses and the download link activates, the standard SecureExportLink 24-hour rule applies — if the link is not downloaded within 24 hours of activation, it expires permanently and the export must be re-requested (which re-runs the review-and-cancel window from scratch). This is deliberate.

### Distributed Oversight via Admin Notification

At LTE submission time, **all agency admins** (not just the submitter and the privacy officer) receive an email that an LTE has been initiated. The email contains:

- What was requested (program, period, evaluator, purpose)
- Review-and-cancel window activation timestamp
- A **"Flag concerns"** link that any admin may click to pause the export during the window

A flagged concern freezes the review-and-cancel countdown, notifies the privacy officer by email, and requires explicit privacy officer resolution before the window can resume. This distributes oversight beyond the privacy officer alone, creates social accountability for the event, and allows any admin to intervene without requiring them to hold the LTE permission themselves.

### Post-Hoc Privacy Officer Review

At submission time, KoNote auto-creates an admin task assigned to the agency's designated privacy officer: *"Review LTE export dated YYYY-MM-DD for Program X"*. The task must be resolved (marked reviewed, or flagged as a concern) **before the same agency can generate another LTE**. The rate limit is per-agency, not per-program — the review burden sits on the privacy officer and there is one per agency. A pending review from a prior LTE blocks submission of any new LTE agency-wide, regardless of which program it targets. This creates a natural rate limit based on the privacy officer's review throughput and ensures every small-population export is seen by a second pair of eyes.

### Enhanced Audit Metadata

LTE audit log entries have a **distinct category** (`longitudinal_trajectory_export`), not a flag or subtype on the EME category. This ensures LTE activity can be monitored, reported, and alerted on separately:

```json
{
    "export_category": "longitudinal_trajectory_export",
    "program_id": 7,
    "program_name": "Peer Support Circle",
    "period_start": "2025-09-01",
    "period_end": "2026-03-31",
    "population_count": 11,
    "evaluator_name": "Dr. Ana Martinez",
    "evaluator_email": "dr.martinez@llewelyn.ca",
    "evaluator_organisation": "Llewelyn Consulting",
    "evaluator_degree": "PhD Community Psychology, McMaster University",
    "evaluator_years_experience": 15,
    "evaluator_prior_programs": "Youth Employment Program (Llewelyn, 2021-2023); Community Mental Health Initiative (Hamilton, 2019-2022); First Nations Wellness Collaborative (external evaluator, 2020-2024).",
    "reb_name": "Llewelyn Consulting Research Ethics Board",
    "reb_approval_number": "LCR-2026-014",
    "reb_approval_date": "2026-03-15",
    "data_sharing_agreement_expiry": "2026-10-31",
    "destruction_window_days": 90,
    "destruction_confirmed_date": null,
    "community_governance_flags": {
        "ocap": false,
        "egap": false,
        "other_community": false
    },
    "community_reviewer": null,
    "purpose_statement": "Peer Support Circle outcome evaluation — trajectory and dose-response analysis",
    "review_and_cancel_window_ends": "2026-04-16T17:00:00Z",
    "review_and_cancel_window_business_days": 5,
    "post_hoc_review_task_id": 4231,
    "admin_notifications_sent": ["jane@agency.ca", "lee@agency.ca", "kwame@agency.ca"],
    "metric_rounding_applied": true,
    "session_count_banded_to": 5,
    "total_hours_banded_to": 0.5
}
```

`destruction_confirmed_date` is initially null and is updated when the agency records the evaluator's destruction acknowledgement (manual entry in v1; no automated evaluator-facing UI). If it remains null past the window, a follow-up task is auto-created for the privacy officer.

### What LTE Is NOT

The panel was clear that several adjacent designs are **not** what LTE is, and implementers should resist requests to morph LTE into any of them:

- **LTE is not a toggle on the EME form.** It is a separate route, a separate permission, a separate form, a separate audit category. Bundling erodes structural separation.
- **LTE is not a "DSA unlock."** The DSA is captured for the audit trail, but it is not the permission gate. REB approval and (where applicable) community governance review are the gates.
- **LTE is not research-grade access.** Researchers needing complete microdata have a separate, high-friction workflow outside the scope of this DRR. If an evaluator insists on complete data or unfuzzed values, they are not doing program evaluation.
- **LTE is not a workaround for the n ≥ 15 EME floor.** The EME floor exists for good reasons and remains enforced. LTE serves a different analytical need (trajectories without demographics) in a population range where EME cannot.
- **LTE is not available to evaluators who "the agency trusts."** Trust is not an operational concept in the pipeline. Structural safeguards and governance preconditions are.

## CSV Output Format

### EME (Evaluation Microdata Export)

```csv
# Evaluation Microdata Export — Youth Employment Program
# Period: 2025-09 to 2026-03
# Generated: 2026-04-07 by Jane Admin
# Evaluator: Dr. Ana Martinez (dr.martinez@llewelyn.ca), Llewelyn Consulting
# Purpose: Youth Employment outcome evaluation 2025-26
# Agreement expiry: 2026-04-30
# Population: 47 eligible, 42 consented, 41 exported, 1 suppressed (k<5)
# Effective k-anonymity: 5
# Quasi-identifiers: age_group, gender, geography
# Generalizations: age_group 55-59 widened to 45+
#
study_id,age_group,gender,geography,enrolment_quarter,exit_quarter,sessions_count,total_hours,metric_wellbeing_intake,metric_wellbeing_exit,metric_housing_intake,metric_housing_exit
EVL-001,25-29,Woman,Urban,Q3-2025,,12,18.5,3,6,2,4
EVL-002,25-29,Woman,Urban,Q3-2025,Q1-2026,8,12.0,4,5,3,5
```

### LTE (Longitudinal Trajectory Export)

```csv
# Longitudinal Trajectory Export — Peer Support Circle (pilot)
# Period: 2025-09 to 2026-03
# Submitted: 2026-04-09 by Sam Privacy-Officer
# Review-and-cancel window: 5 business days (activates 2026-04-16, expires 24h after activation)
# Evaluator: Dr. Ana Martinez (dr.martinez@llewelyn.ca), Llewelyn Consulting
# Evaluator degree: PhD Community Psychology, McMaster University
# Evaluator years experience: 15
# REB: Llewelyn Consulting REB, approval LCR-2026-014, approved 2026-03-15
# Agreement expiry: 2026-10-31
# Destruction window: 90 days from download (manual attestation)
# Purpose: Peer Support Circle outcome evaluation — trajectory and dose-response analysis
# Population: 13 eligible, 11 consented, 11 exported, 0 suppressed
# NO demographic fields. Metric values rounded to nearest scale unit.
# Session count banded to nearest 5. Total hours banded to nearest half-hour.
# This file is for PROGRAM EVALUATION, not research.
# Attempting to re-identify participants violates the data sharing agreement and REB approval.
#
study_id,enrolment_quarter,exit_quarter,sessions_count_banded,total_hours_banded,metric_wellbeing_intake,metric_wellbeing_mid,metric_wellbeing_exit,metric_connectedness_intake,metric_connectedness_mid,metric_connectedness_exit
LTE-001,Q3-2025,,15,22.5,3,4,6,2,3,5
LTE-002,Q3-2025,Q1-2026,10,15.0,4,5,5,3,4,4
```

The LTE format intentionally omits every quasi-identifier that EME includes. What remains is enough for trajectory analysis, attrition patterns, and dose-response modelling — the analyses that small-n evaluation actually needs — while leaving no demographic surface for re-identification.

## Anti-Patterns — Do Not Build

| Anti-pattern | Why |
|---|---|
| **Evaluator login to KoNote** | Violates the principle that external users don't access the system. Export is file-based, mediated by agency staff. |
| **Container / secure analysis environment** | Every evaluator has different tools and workflows. Adds infrastructure complexity disproportionate to nonprofit budgets. Agencies must manage the evaluator relationship regardless. |
| **Automatic evaluator notification** | KoNote should not email the evaluator or manage the delivery channel. The ED controls how and when data is shared. |
| **Reusing real record IDs as pseudonyms** | Linkable to other KoNote data. Pseudonymous IDs must be random with no derivable relationship to real IDs. |
| **Hashing record IDs as pseudonyms** | Hashes are reversible when the input space is small (sequential integers). Use random UUIDs or random short codes. |
| **Skipping k-anonymity for "trusted" evaluators** | Trust doesn't prevent laptop theft. De-identification protects against all downstream risks, not just the evaluator's intent. Applies equally to EME and LTE. A signed DSA is a liability instrument, not a risk-reduction instrument, and does not justify weakening de-identification. |
| **DSA as an unlock for relaxed thresholds** | The request "they signed a DSA, so we can give them more data" re-introduces the "trusted evaluator" anti-pattern in a new wrapper. DSAs shift liability downstream but do not reduce the upstream risk of device theft, laptop compromise, or unauthorised secondary use. The LTE tier is the approved alternative for small-population evaluation — it is gated by REB approval, community governance review, the review-and-cancel window, and post-hoc privacy officer review, **never by DSA alone**. |
| **Serving research-grade data access through the evaluation export path** | Researchers needing complete microdata (unfuzzed values, full demographic detail, unrounded metrics) have a separate, intentionally high-friction workflow (full agency export gated by ED authority, legal review, institutional data sharing agreements). If an evaluator insists on this level of access, direct them to the research workflow — do not relax EME or LTE safeguards to meet the request. Both evaluation export tiers are for *sufficient* data, not *complete* data. |
| **Advisory-only population thresholds** | Funders will pressure agencies to override warnings. System-enforced blocks protect the program manager from having to argue. This applies to both the EME floor (n ≥ 15) and the LTE floor (n ≥ 10, or n ≥ 15 for OCAP/EGAP-governed programs). No administrative waiver path exists for either. |
| **LTE available to agencies without a designated privacy officer** | The LTE assumes a privacy officer role for post-hoc review, distributed oversight, and destruction-attestation follow-up. Agencies that have not designated a privacy officer with the LTE permission should not be able to reach the form at all — the feature depends on governance capacity that the agency must establish first. |
| **Bundling LTE as a toggle on the EME form** | The LTE must be a structurally separate path with its own permission, its own form, its own route, and its own audit category. Bundling would allow the LTE to become the default through UI proximity and muscle memory, and would dilute the distinct governance preconditions. Separate path, separate door, separate key. |
| **Demographic fields in LTE output** | The LTE's re-identification defence comes from *removing* demographic quasi-identifiers entirely, not from generalising them. Adding any demographic field to LTE output — even "just age band" or "just urban/rural" — re-opens the full re-identification surface and violates the tier's design principle. The EME is the path for demographic analysis; LTE is the path for trajectory analysis. Do not blur them. |
| **Lowering the k-anonymity floor below 5** | k = 5 aligns with Statistics Canada and CIHI guidance and with KoNote's internal small-cell suppression threshold for CIDS aggregate reporting. Keeping the floor consistent across tiers removes ambiguity and prevents inter-tier pressure to "just lower it here too." |
| **LTE without REB approval** | REB approval is the substantive pre-review check for small-population evaluation; it evidences that the risk-benefit trade-off has been considered by an independent body with ethics authority. A DSA alone captures a contractual relationship but not an ethical review. If the evaluator does not have REB approval, they either need to obtain it or to accept the EME tier (where applicable) or aggregate reports. |
| **LTE bypass for Indigenous or Black community programs without community governance signoff** | OCAP and EGAP frameworks require community decision-making about community data. Agency ED authorisation is not a substitute for community review. A community reviewer signoff is a hard precondition for LTE on programs flagged under these frameworks. |
| **Fast-path early approval to shorten the review-and-cancel window** | A "privacy officer clicks approve to activate immediately" path was considered and deferred. The rubber-stamp risk is real, the operational need has not been demonstrated, and the pause is part of what makes the LTE a deliberate event rather than a routine one. Revisit only if real operational experience shows the default window is unworkable for legitimate cases. |
| **Separate consent flag for evaluation** | Creates consent fatigue at intake, introduces selection bias. Broaden existing consent language instead. The same consent language covers both EME and LTE. |
| **Synthetic data as default** | Can distort subgroup patterns that equity analysis aims to detect. Defer until validated. The LTE tier covers most of the small-n use cases that synthetic data was being held in reserve for. |

## What This DRR Does NOT Restrict

- **Template-driven aggregate reports** — unchanged, still the primary reporting path
- **Ad-hoc exports by PMs** — unchanged, still available for internal program management
- **Individual client exports** — unchanged, still available for PIPEDA requests
- **CIDS JSON-LD aggregate exports** — unchanged, governed by reporting architecture DRR

## What This DRR Does NOT Cover (Out of Scope)

- **Research-grade data access** — formal research studies, secondary data analysis, and academic publication that require *complete* microdata (unfuzzed values, narrow demographics, raw metric series, or direct identifiers) are handled through a separate, intentionally high-friction workflow: a full agency export gated by ED authority, legal review, institutional data sharing agreements, and case-by-case governance. An evaluator who cannot accept the EME or LTE data product is doing research, not program evaluation, and should be directed to the research workflow. The decision to grant research access is a governance decision, not a product decision, and sits outside the scope of this DRR.
- **Ongoing sharing with researchers** — continuous or periodic access by a researcher is neither EME nor LTE. If that need exists, treat it as a research agreement and handle it through the research workflow, not by automating repeat exports.
- **Cross-agency pooled microdata** — combining microdata from multiple KoNote tenants for a multi-site evaluation is governed by the data sovereignty and multi-tenancy DRRs. It is not something the EME or LTE pipelines do on their own.

## Future Considerations

1. **Long-format longitudinal export** — one row per participant-per-measurement-point instead of the wide LTE format (which puts each measurement point in its own column). Long format is more natural for some statistical tools but it increases the re-identification surface (multiple rows sharing a study_id create additional combinatorial leakage). Not implemented; the wide LTE format covers current analytical needs. Revisit only if multiple evaluators specifically request long format and can demonstrate that wide format cannot meet their tooling constraints.
2. **Synthetic data option** — the LTE tier covers most of the n < 15 use cases that synthetic data was being held in reserve for. Synthetic data remains a possible option for *very* small programs (n < 10) but requires validation research before implementation, and no strong need has been identified given that the LTE floor at n = 10 is defensible for the target audience (regular program evaluation, not research).
3. **REB registry verification** — the LTE form captures the REB approval number but does not verify it against an external registry at submission time. Future enhancement: integrate with a REB directory for the relevant jurisdictions (Canadian REBs, institutional REBs) to verify the approval number is real and currently active. Not blocking for v1.
4. **Automated destruction attestation UI for evaluators** — v1 captures destruction attestation through manual agency entry in the audit log. A future enhancement could let the evaluator acknowledge destruction directly via a magic-link form, or parse email replies. Deferred until operational experience shows whether manual entry is workable.
5. **Fast-path early approval** — the current review-and-cancel window is a fixed 5 business days. A future enhancement could let the privacy officer explicitly approve early to activate the download link sooner, for time-sensitive legitimate exports. Deferred because the rubber-stamp risk is real and the operational need has not been demonstrated. Revisit only if real operational experience shows the default window is unworkable for legitimate cases.
6. **Cross-program evaluation export** — spanning multiple programs in one export. Raises consent complexity (different programs may have different consent rates) and multi-program equivalence-class mathematics for the EME. Defer until single-program exports are proven in both tiers.
7. **Data sharing agreement tracking model** — if many agencies need to track multiple concurrent evaluations, a lightweight `EvaluationAgreement` model could be useful. Not needed for v1; the audit log metadata is sufficient.
8. **Secure delivery channel to the evaluator** — the DRR treats file delivery (from the agency to the evaluator) as out of scope, assuming the agency has a secure channel of its own. Small agencies may not, which is a known operational gap. A future enhancement could offer a KoNote-mediated secure delivery link (encrypted, time-limited, evaluator-email-gated) if demand justifies the added complexity.

## Related Documents

- `tasks/design-rationale/no-live-api-individual-data.md` — the two-tier export model this extends
- `tasks/design-rationale/reporting-architecture.md` — template-driven reporting (aggregate path)
- `tasks/design-rationale/phipa-consent-enforcement.md` — consent model and enforcement
- `tasks/design-rationale/data-access-residency-policy.md` — data access tiers
- `tasks/design-rationale/multi-tenancy.md` — suppression thresholds, consortium sharing
- `tasks/phase-evaluation-export-prompt.md` — implementation prompt for this feature
