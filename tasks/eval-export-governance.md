# Evaluation Export — Governance, Documentation & Remaining Work

**Created:** 2026-04-08
**Context:** The de-identified microdata export feature (EVAL-EXPORT1) is built and merged. This task file covers the remaining work: governance model, admin documentation, protocol updates, user guide references, and test coverage.

**Related:**
- DRR: `tasks/design-rationale/evaluation-microdata-export.md`
- Implementation prompt: `tasks/phase-evaluation-export-prompt.md`
- Pipeline code: `apps/reports/deidentify.py`
- Admin reporting guide: `docs/admin/reporting.md`
- Deployment protocol: `tasks/deployment-protocol.md`
- Permissions interview: `tasks/agency-permissions-interview.md`

---

## Governance Model (decided by expert panel, 2026-04-08)

### Who can generate evaluation exports?

Anyone with the `report.evaluation_export` permission. This permission is DENY for all roles by default — it must be explicitly granted per-user.

**Program Managers can hold this permission** when the ED has approved an evaluation engagement. The ED governs; the PM executes. Restricting to ED-only would push de-identification out of the system (PMs would export PII reports and strip names in Excel, which is worse).

### How is the permission granted?

The Admin grants `report.evaluation_export` in the KoNote admin panel. When granting, they must enter a **reason** (free-text field) that links the technical act to the governance authority — e.g., "Approved by ED for Youth Employment evaluation with Llewelyn Consulting, agreement signed 2026-03-15."

This is the two-person control: **ED approves the evaluation engagement → Admin grants the permission.** No two-person approval is required per export.

### What safeguards exist per-export?

Each export already requires:
- Evaluator details (name, email, organisation, purpose, agreement expiry) — all mandatory
- Preview step showing population counts, suppression, effective k-anonymity
- 10-minute elevated export delay before download is available
- Admin notification email when an export is created (admin can revoke before download)
- Immutable audit trail recording every step of the de-identification pipeline

### What prevents permission creep?

Visibility, not automatic expiry:
- **Admin dashboard card** showing how many users have the permission and when the last export was generated
- **Permission audit list** — dedicated page showing: user, granted by, date, reason, last export date, revoke button
- **Agreement expiry warnings** — banner on export history when an evaluator's agreement expiry date has passed

The panel explicitly rejected automatic permission expiry (creates admin burden in small orgs) and two-person approval per export (kills evaluation practice when the ED is travelling).

### Anti-patterns (do not build)

| Anti-pattern | Why rejected |
|---|---|
| Two-person approval per export | ED is often unavailable; delays break evaluation timelines; existing safeguards sufficient |
| Automatic permission expiry | Admin burden; forced re-approval cycles annoy small orgs; visibility is the better safeguard |
| Hard block on expired agreements | Agreements sometimes get verbally extended while paperwork catches up; warning is sufficient |
| ED-only permission restriction | PMs are the legitimate operators; restricting to ED pushes de-identification outside the system |
| Approval workflow model | Adds a model, a queue, notification logic — overkill for a decision that happens verbally in a 10-person org |

---

## Tasks

### EVAL-GOV1: Add reason field to permission grant

When an admin grants `report.evaluation_export`, require a free-text reason that's logged. This links the technical action to the governance decision (e.g., "Board-approved evaluation with University of Ottawa, MOU signed Jan 2026").

**Where:** The permission grant mechanism in the admin panel. Check how `report.evaluation_export` is currently granted and add the reason field there.

### EVAL-GOV2: Admin dashboard card for evaluation export

Add a card to the admin dashboard showing:
- Number of users with `report.evaluation_export` permission
- Date of the most recent evaluation export
- Click-through to the permission audit list (EVAL-GOV3)

**Where:** `templates/admin_settings/` — the existing admin dashboard template.

### EVAL-GOV3: Permission audit list page

A dedicated page (not buried in general permissions) showing:
- Each user with `report.evaluation_export`: name, role, granted by, grant date, reason, last export date
- Revoke button per user (with confirmation)
- Link from admin dashboard card (EVAL-GOV2)

**Where:** New view in `apps/admin_settings/` or `apps/reports/`. URL: `/admin/evaluation-export-permissions/` or similar.

### EVAL-GOV4: Export history view

List of past evaluation exports showing:
- Date generated
- Program name
- Evaluator name and organisation
- Participant counts (eligible / exported / suppressed)
- Effective k-anonymity
- Status (active / expired / revoked)
- Download link (if still active)

**Where:** New view accessible from the Reports menu, visible to users with `report.evaluation_export`. URL: `/reports/evaluation-export-history/`.

### EVAL-GOV5: Agreement expiry warning

On the export history page (EVAL-GOV4), show a warning banner when any evaluator's data sharing agreement expiry date has passed. Warning, not block — agencies may have verbal renewals in progress.

Example: "The agreement with Dr. Martinez (Llewelyn Consulting) expired 30 days ago. Confirm the evaluator has deleted the data, or update the agreement."

### EVAL-GOV6: Wire up `is_evaluation_exportable` on custom field groups

The `EvaluationExportForm` currently hardcodes four QI column checkboxes (age, gender, ethnicity, geography). The `CustomFieldGroup.is_evaluation_exportable` field already exists (migration 0043) but the form doesn't use it.

Update the form to dynamically show checkboxes for custom field groups marked `is_evaluation_exportable=True`, in addition to the built-in QI columns (age from DOB, geography from postal code).

### EVAL-GOV7: Pipeline test suite

The de-identification pipeline (`apps/reports/deidentify.py`) has no test coverage. This is safety-critical code. Write tests covering:

- Consent filtering (only consented participants included)
- Direct identifier stripping (no names, emails, phone, exact DOB, real IDs in output)
- Pseudonymous ID randomness (not sequential, not derived from real ID)
- Age band generalisation
- Geography derivation (urban/rural from postal code FSA)
- K-anonymity computation (equivalence classes computed correctly)
- K-anonymity violation resolution (widening, suppression, record removal)
- Population threshold blocking (n < 15 blocked, 15-30 limited QI, 30+ full)
- Suppression ceiling (> 15% suppression blocks export)
- CSV output format (correct columns, no PII leakage)
- Suppression report accuracy

**Where:** `tests/test_evaluation_export.py`

### EVAL-DOC1: Update admin reporting guide

Add a new section to `docs/admin/reporting.md` covering:

1. **What evaluation exports are** — plain language: "De-identified participant-level data for external program evaluators. Names are removed. Demographics are generalised so no individual can be identified."
2. **What k-anonymity means** — "Every person in the export is indistinguishable from at least 4 others based on their demographic information."
3. **How to grant the permission** — step-by-step: navigate to admin panel, find the user, grant `report.evaluation_export`, enter the reason
4. **How to revoke the permission** — when an evaluation ends, when staff leave, when an agreement expires without renewal
5. **How to review who has access** — link to the permission audit list (EVAL-GOV3)
6. **How to review export history** — link to the export history view (EVAL-GOV4)
7. **What the weekly export summary shows** — evaluation exports appear in the weekly digest alongside other export types
8. **Marking demographic fields as exportable** — how to set `is_evaluation_exportable` on custom field groups, and why only non-sensitive groups should be marked

### EVAL-DOC2: Update deployment protocol — evaluation export decisions

Add to the **permissions interview** (Section 7: Features to Turn On) in `tasks/agency-permissions-interview.md`:

**New feature row in the features table:**

| Feature | What It Does | Default | Your Choice |
|---|---|---|---|
| **Evaluation Export** | De-identified participant data for external evaluators | Off | |

**New interview questions (after 7.3, as 7.4):**

**7.4** "Does your organisation work with external program evaluators — for example, a university researcher or a consulting firm doing an outcome evaluation for a funder?"

*If yes:*
- "Who authorises sharing de-identified data with an evaluator — your Executive Director, your board, or someone else?"
- "Would the person doing the actual export be the same person who authorises it, or would they delegate to a Program Manager?"
- Record the answers in the configuration summary.
- Explain: "KoNote can export de-identified data — no names, no contact info — with privacy safeguards that prevent re-identification. The permission to do this is granted per-person and logged. We'll set this up when you have an evaluation engagement."

*If no:*
- Note the decision. The feature can be enabled later when needed.

**Also update `tasks/deployment-protocol.md`** Phase 1 section (line ~202) to add "Evaluation Export" to the summary table of what the permissions interview covers.

### EVAL-DOC3: Add evaluation export section to user guide

Add a section to `docs/help.md` (and corresponding content in `docs/using-konote.md` if appropriate) covering:

**For users with the evaluation export permission:**
1. Where to find it: Reports → Evaluation Export
2. What information you need before starting: evaluator name/email/organisation, evaluation purpose, data sharing agreement expiry date, which program and date range
3. What happens: preview shows you how many participants will be included, what demographics are generalised, and whether any records are suppressed
4. After generating: download within 24 hours via the secure link
5. Your responsibility: deliver the file securely (not via regular email), confirm the evaluator deletes the data when the evaluation is complete

**For users without the permission:**
- "If you need to export data for a program evaluation, ask your administrator to grant you the Evaluation Export permission. Your Executive Director must approve this."

### EVAL-DOC4: ED-facing one-page reference

Create a one-page reference document (markdown, convertible to PDF) that an ED can print:

- "How to generate an evaluation export" — 5-step walkthrough
- "What to check before you send it" — verify evaluator details match the agreement, review suppression report
- "How to deliver it securely" — encrypted email, secure file transfer, NOT regular email or USB
- "After the evaluation" — confirm evaluator deleted the data, revoke the permission if the engagement is complete
- "What to tell the evaluator" — what the CSV columns mean, what the suppression report means, data handling expectations

**Where:** `docs/evaluation-export-guide.md`
