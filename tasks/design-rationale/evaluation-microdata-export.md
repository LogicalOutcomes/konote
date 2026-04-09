# De-Identified Microdata Export for Program Evaluation

**Date:** 2026-04-07
**Status:** Decided — GK
**Panels:** 1 expert panel (program evaluator, privacy/data governance, nonprofit program manager, health informatics), 3 rounds

---

## What Was Requested

External program evaluators need participant-level outcome data with demographic breakdowns to do rigorous evaluation — trajectory analysis, equity disaggregation, dose-response modelling, attrition analysis. KoNote currently offers aggregate-only template reports (which can't support individual-level analysis) and PII-containing individual exports (which include names and are too sensitive to hand to an external party). There is no middle option.

## The Decision

Build a **de-identified microdata export** — individual rows with pseudonymous IDs, generalised demographics, and outcome metric values, with all direct identifiers removed. Deliver as CSV via the existing SecureExportLink infrastructure.

This is a new export tier sitting between template reports and individual exports:

| Tier | What | Who | Contains PII |
|---|---|---|---|
| Template reports | Aggregate metrics by demographic group | PM, Executive | No |
| **Evaluation export (new)** | **De-identified individual rows with generalised demographics** | **ED / designated user** | **No (de-identified)** |
| Individual client export | Full client record including names | PM | Yes |
| Full agency export | Encrypted dump of everything | CLI / KoNote team | Yes |

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

## CSV Output Format

```csv
# Evaluation Export — Youth Employment Program
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

## Anti-Patterns — Do Not Build

| Anti-pattern | Why |
|---|---|
| **Evaluator login to KoNote** | Violates the principle that external users don't access the system. Export is file-based, mediated by agency staff. |
| **Container / secure analysis environment** | Every evaluator has different tools and workflows. Adds infrastructure complexity disproportionate to nonprofit budgets. Agencies must manage the evaluator relationship regardless. |
| **Automatic evaluator notification** | KoNote should not email the evaluator or manage the delivery channel. The ED controls how and when data is shared. |
| **Reusing real record IDs as pseudonyms** | Linkable to other KoNote data. Pseudonymous IDs must be random with no derivable relationship to real IDs. |
| **Hashing record IDs as pseudonyms** | Hashes are reversible when the input space is small (sequential integers). Use random UUIDs or random short codes. |
| **Skipping k-anonymity for "trusted" evaluators** | Trust doesn't prevent laptop theft. De-identification protects against all downstream risks, not just the evaluator's intent. |
| **Advisory-only population thresholds** | Funders will pressure agencies to override warnings. System-enforced blocks protect the program manager from having to argue. |
| **Separate consent flag for evaluation** | Creates consent fatigue at intake, introduces selection bias. Broaden existing consent language instead. |
| **Synthetic data as default** | Can distort subgroup patterns that equity analysis aims to detect. Defer until validated. |

## What This DRR Does NOT Restrict

- **Template-driven aggregate reports** — unchanged, still the primary reporting path
- **Ad-hoc exports by PMs** — unchanged, still available for internal program management
- **Individual client exports** — unchanged, still available for PIPEDA requests
- **CIDS JSON-LD aggregate exports** — unchanged, governed by reporting architecture DRR

## Future Considerations

1. **Synthetic data option** — for programs with n < 15 where aggregate reports are insufficient. Requires validation research before implementation.
2. **Longitudinal export format** — one row per participant-per-measurement-point instead of one row per participant. More useful for trajectory analysis but increases re-identification risk (more rows = more combinatorial surface). Design separately.
3. **Cross-program evaluation export** — spanning multiple programs in one export. Raises consent complexity (different programs may have different consent rates). Defer until single-program exports are proven.
4. **Data sharing agreement tracking model** — if many agencies need to track multiple concurrent evaluations, a lightweight `EvaluationAgreement` model could be useful. Not needed for Phase 1 — the audit log metadata is sufficient.

## Related Documents

- `tasks/design-rationale/no-live-api-individual-data.md` — the two-tier export model this extends
- `tasks/design-rationale/reporting-architecture.md` — template-driven reporting (aggregate path)
- `tasks/design-rationale/phipa-consent-enforcement.md` — consent model and enforcement
- `tasks/design-rationale/data-access-residency-policy.md` — data access tiers
- `tasks/design-rationale/multi-tenancy.md` — suppression thresholds, consortium sharing
- `tasks/phase-evaluation-export-prompt.md` — implementation prompt for this feature
