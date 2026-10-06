# Evaluation Export Guide

This guide is for **executive directors and program managers** — the people who approve, generate, and deliver de-identified evaluation data to external evaluators.

The Evaluation Microdata Export (EME) produces a de-identified CSV file that an external evaluator can use for outcome analysis. All identifying information is removed automatically, and the system blocks the export if privacy thresholds cannot be met.

The full technical rationale is in [`tasks/design-rationale/evaluation-microdata-export.md`](../tasks/design-rationale/evaluation-microdata-export.md).

---

## Before you begin

Make sure these are in place:

1. **A signed data-sharing agreement (DSA)** between your agency and the evaluator, specifying what data will be shared, how long the evaluator may keep it, and when they must delete it.
2. **An evaluator with confirmed credentials** — name, organisation, email, and purpose of the evaluation.
3. **A KoNote admin has granted you the Evaluator Export permission** — this is done through **Admin → Evaluator Export Access**. Without the grant, you will see a 403 error. No one, including administrators, can bypass this step.
4. **The program has at least 15 participants** with outcome data in the selected period. Programs below this threshold are blocked because demographic privacy cannot be guaranteed. For smaller programs, see [LTE (small-population evaluation)](lte-privacy-officer-guide.md).

---

## How to generate an export

1. Go to **Reports → Evaluator Export (Confidential)**.
2. Choose the **program**, **start date**, and **end date**.
3. Fill in the **evaluator details**: name, organisation, email, purpose, and agreement expiry date.
4. Select which **demographic columns** (quasi-identifiers) to include. Fewer columns means stronger privacy — only include what the evaluator actually needs.
5. Click **Preview**.

### Understanding the preview

The preview shows you:

- **Participant count** — how many people are included after consent filtering.
- **Suppression report** — how many records were removed or generalised to protect privacy. If more than 15% of records had to be suppressed, the export is blocked entirely.
- **K-anonymity score** — the minimum number of people who share the same combination of demographic values. KoNote requires k ≥ 5 (meaning every person's demographic profile matches at least 4 others).

If the preview passes all checks, click **Confirm and generate**. If it fails, the system will explain why and suggest reducing the number of demographic columns.

### Download and delivery

After confirming, KoNote creates a secure download link that is **available for 24 hours**. Large exports (100+ participants or exports that include clinical notes) have a **10-minute delay** before the download link becomes active — this gives administrators a chance to review the export before it can be downloaded.

**How to deliver the file to the evaluator:**

- Use **encrypted email** or a **secure file transfer service** (e.g., your agency's secure SharePoint, Google Drive with restricted access, or an encrypted ZIP).
- **Do not** send the CSV as a plain email attachment. The data is de-identified, but it still contains sensitive program information.
- Note the **agreement expiry date** you entered — KoNote will display a warning banner on the Export History page when this date passes.

---

## After the evaluation

When the evaluator's work is complete:

1. **Confirm the evaluator has deleted the data** in accordance with your data-sharing agreement.
2. **Check Export History** (Reports → Export History) — look for any exports with an expired agreement. Follow up with evaluators whose agreements have lapsed.
3. If an evaluator should no longer receive data, ask your admin to **revoke their export access** through Admin → Evaluator Export Access.

---

## What the evaluator receives

The CSV file contains one row per participant with:

| Column type | Example | Notes |
|---|---|---|
| **Study ID** | `a3f9c1b2` | Randomly generated per export — cannot be linked back to a real person |
| **Demographic columns** | Age band, gender, geography | Generalised (e.g., "25–29" not exact age, "Urban" not postal code) |
| **Metric scores** | `Confidence: 4.0` | Raw scale values for selected metrics |
| **Enrolment quarter** | `2025-Q3` | When the participant started the program (quarter, not exact date) |

**What is NOT in the file:** names, dates of birth, addresses, phone numbers, email addresses, case notes, worker names, or anything that could identify a specific person.

**Suppression notation:** If a cell has been suppressed for privacy, it appears as an empty value. The suppression report (included separately) tells the evaluator how many records were affected and why.

---

## What to tell the evaluator

Share these points when you deliver the file:

1. **Study IDs are random** — they change with every export and cannot be linked across exports or back to real people.
2. **Demographic values are generalised** — age is in 5-year bands, geography is Urban/Rural, not specific locations.
3. **Some records may be suppressed** — if including a record would make someone identifiable, it is removed. The suppression report explains how many and why.
4. **Data must be deleted** by the date in your agreement. KoNote tracks this date and will flag it if it passes.
5. **Do not attempt to re-identify participants.** This violates PHIPA and your data-sharing agreement.

---

## Quick reference

| Item | Detail |
|---|---|
| Where to find it | Reports → Evaluator Export (Confidential) |
| Permission required | `report.evaluation_export` (granted by admin) |
| Minimum program size | 15 participants with outcome data |
| Privacy standard | k-anonymity ≥ 5, suppression ceiling 15% |
| Download window | 24 hours |
| Smaller programs | Use [LTE](lte-privacy-officer-guide.md) (requires separate permission + REB) |
| Export history | Reports → Export History |
| Agreement expiry tracking | Entered at export time; banner warns when expired |
| Related admin guide | [Reporting admin guide](admin/reporting.md) |
| Evaluation protocol | [CIDS Evaluation Protocol](../tasks/cids-evaluation-protocol.md) (for evaluators) |
| LLM planning prompt | [Evaluation Planning Prompt](../tasks/cids-evaluation-planning-prompt.md) (for evaluators using AI) |
| Literature review template | [Literature Review Brief Template](literature-review-brief-template.md) |
