# Phase: De-Identified Evaluation Microdata Export

## Goal

Build a new export type that produces de-identified, participant-level CSV files for external program evaluators. The CSV contains pseudonymous IDs, generalised demographics, and outcome metric values — with all direct identifiers removed and k-anonymity enforced. This sits between the existing aggregate template reports and PII-containing individual exports.

**Read before starting:** `tasks/design-rationale/evaluation-microdata-export.md` — contains the full rationale, anti-patterns, and decisions. Do not deviate from that DRR without explicit user approval.

## Prerequisites

Before starting, verify:
- You have read and understood the DRR
- You understand how `SecureExportLink` works (see `apps/reports/models.py`)
- You understand the existing export flow in `apps/reports/views.py` (the `generate_report_form` and `export_form` views)
- You understand the permission model in `apps/auth_app/permissions.py` and `apps/reports/utils.py`
- You understand how `AuditLog` works (see `apps/audit/models.py`, uses `.using("audit")`)
- You understand the demographic/age grouping in `apps/reports/demographics.py`
- You understand the suppression logic in `apps/reports/suppression.py`

## Tasks (in dependency order)

### Task 1: EVAL-PERM1 — Add Evaluation Export Permission

**What:** Add a new permission `report.evaluation_export` that is not granted to any role by default. Must be explicitly granted to specific users (typically the Executive Director).

**Changes to `apps/auth_app/permissions.py`:**
- Add `evaluation_export` to the `report` permission group
- Default: DENY for all roles (executive, PM, staff, receptionist)
- Admins (is_admin=True) can always access (consistent with other admin overrides)

**Changes to `apps/auth_app/models.py` or admin views:**
- Ensure there's a way for admins to grant this permission to specific users via the admin UI
- Check how other permissions are granted — follow the same pattern

**Changes to `apps/reports/utils.py`:**
- Add `can_create_evaluation_export(user)` — returns True if user has the `report.evaluation_export` permission or is admin

**Tests (`tests/test_reports.py` or new `tests/test_evaluation_export.py`):**
- Test: user without permission cannot access the evaluation export view (403)
- Test: user with permission can access the view
- Test: admin can always access the view
- Test: PM and executive without explicit permission cannot access (403)

---

### Task 2: EVAL-PIPE1 — De-Identification Pipeline Engine

**What:** Create the core de-identification pipeline as a standalone module. This is the heart of the feature — it transforms raw identified data into de-identified, k-anonymous microdata.

**New file: `apps/reports/deidentify.py`**

This module should contain:

#### Class: `DeidentificationPipeline`

```python
class DeidentificationPipeline:
    """
    10-step pipeline that transforms identified participant data
    into de-identified, k-anonymous microdata for evaluation export.
    
    Each step is a separate method that logs to the audit trail.
    The pipeline is run in preview mode (dry run) first to show
    the user what will happen, then in generate mode to produce output.
    """
    
    def __init__(self, program, period_start, period_end, 
                 qi_columns, evaluator_info, user):
        """
        Args:
            program: Program instance
            period_start: date
            period_end: date
            qi_columns: list of quasi-identifier column names 
                        (e.g., ["age_group", "gender", "geography"])
            evaluator_info: dict with keys: name, email, organisation, 
                           purpose, agreement_expiry
            user: User initiating the export
        """
    
    def run_preview(self):
        """
        Execute steps 1-8 without generating output.
        Returns a PreviewResult with counts, suppression details,
        and whether the export is permitted.
        """
    
    def run_generate(self):
        """
        Execute all 10 steps and produce the CSV + suppression report.
        Returns a GenerateResult with file paths.
        Must only be called after run_preview() has been shown to the user.
        """
```

#### Step Methods (called by run_preview and run_generate)

**Step 1: `_extract_raw_data()`**
- Query ClientFile records for the program within the period
- Query ServiceEpisode for enrollment data
- Query ClientDetailValue for demographic custom fields
- Query MetricValue / ProgressNote for outcome measurements
- Return: list of raw record dicts
- Audit: log job initiation with eligible count

**Step 2: `_decrypt_and_stage()`**
- Decrypt birth_date (for age calculation) and names (for exclusion list only)
- Build working recordset in memory — never write decrypted data to disk
- Return: list of staged record dicts
- Audit: log fields decrypted and record count

**Step 3: `_apply_consent_filter()`**
- Remove records where `ServiceEpisode.consent_to_aggregate_reporting = False`
- Return: filtered list, count of excluded
- Audit: log consent exclusion count

**Step 4: `_strip_direct_identifiers()`**
- Drop: names, phone, email, exact birth_date, real record_id
- Generate pseudonymous study IDs: random short codes (e.g., EVL-001)
  - Use `secrets.token_hex(4)` or similar — NOT sequential, NOT derived from record_id
  - Ensure uniqueness within the export
- Build linkage table: `{study_id: real_record_id}` — encrypt with Fernet, store later on SecureExportLink
- Return: de-identified records, encrypted linkage blob
- Audit: log identifier stripping and pseudonym assignment

**Step 5: `_generalise_quasi_identifiers()`**
- Age (from decrypted birth_date): compute age, map to 5-year bands (18-24, 25-29, 30-34, 35-39, 40-44, 45-49, 50-54, 55-59, 60-64, 65+)
- Geography: if FSA (first 3 of postal code) is available, map to Urban/Rural using Stats Canada classification. If no postal code, set to null.
- Enrolment date: round to quarter/year (Q1-2026, Q2-2026, etc.)
- Exit date: round to quarter/year (null if still enrolled)
- Gender, ethnicity: pass through as-is (already categorical)
- Return: generalised records, list of generalisations applied
- Audit: log generalisation rules applied

**Step 6: `_compute_k_anonymity()`**
- For each record, compute its equivalence class: the set of records sharing identical values across all selected QI columns
- Compute minimum k (smallest equivalence class size)
- Return: dict mapping equivalence class tuple → count, minimum k
- Audit: log QI columns, equivalence class count, minimum k

**Step 7: `_resolve_k_violations(target_k=5)`**
- For each equivalence class where count < target_k:
  1. **Widen** the most granular QI. Priority order for widening: age_group (merge adjacent bands), geography (suppress to null), enrolment_quarter (widen to half-year)
  2. Recompute equivalence classes after widening
  3. If still below k, **suppress** the smallest QI field value (set to null)
  4. If record is still unique after all QI generalisation, **suppress the entire record**
- Track suppressed records and reasons
- If suppression rate > 15%, set `blocked = True` with message recommending fewer QI columns
- Return: resolved records, suppressed records with reasons, final minimum k, blocked flag
- Audit: log resolution actions, suppression count, final k

**Step 8: `_check_population_threshold()`**
- After consent filter + suppression, count remaining records
- Apply tier rules:
  - n < 15: blocked, aggregate only
  - 15 ≤ n < 30: max 3 QI columns (if more were selected, block and advise)
  - n ≥ 30: max 5 QI columns
- Return: pass/block, tier applied, population count
- Audit: log threshold check result

**Step 9: `_generate_csv(records)`**
- Build CSV with metadata header (see DRR for exact format)
- Include: study_id, selected QI columns, enrolment_quarter, exit_quarter, sessions_count, total_hours, metric columns (intake and latest values per metric)
- Apply CSV injection prevention from `apps/reports/csv_utils.py`
- Write to SECURE_EXPORT_DIR (same as existing exports)
- Return: file path
- Audit: log output generation, file path

**Step 10: `_generate_suppression_report()`**
- Build JSON companion file documenting:
  - Total eligible, consented, exported, suppressed
  - Suppression reasons by field
  - Generalisations applied (original → widened)
  - Effective k
  - QI columns used
- Write alongside CSV in SECURE_EXPORT_DIR
- Return: file path
- Audit: log completion with full pipeline summary

#### Data Classes for Results

```python
@dataclass
class PreviewResult:
    eligible_count: int
    consented_count: int
    exportable_count: int
    suppressed_count: int
    suppression_rate: float
    effective_k: int
    qi_columns_used: list[str]
    generalizations_applied: list[dict]  # [{"field": ..., "original": ..., "widened_to": ...}]
    suppression_details: list[dict]  # [{"reason": ..., "count": ...}]
    blocked: bool
    block_reason: str | None  # "population_too_small", "suppression_rate_exceeded", "too_many_qi_columns"
    tier: str  # "aggregate_only", "limited_qi", "full"

@dataclass
class GenerateResult:
    csv_path: str
    suppression_report_path: str
    preview: PreviewResult
    linkage_blob: bytes  # encrypted
    audit_metadata: dict  # the full metadata blob for the audit log
```

**Tests (`tests/test_evaluation_export.py`):**

Use Django's `TestCase` with factory-created test data. You'll need:
- A program with ~30 test participants with varied demographics
- A program with ~10 test participants (to test the n<15 block)
- Participants with and without consent

Test cases:
- Pipeline runs end-to-end on a program with 30+ consented participants
- Consent filter correctly excludes non-consenting participants
- Direct identifiers (names, email, phone, birth_date, record_id) are absent from output
- Pseudonymous IDs are random (not sequential, not derived from record_id)
- Age generalisation produces correct 5-year bands
- Date generalisation produces correct quarter/year
- K-anonymity is computed correctly (create a scenario with a known unique combination)
- K violations are resolved by widening (check that bands were merged)
- K violations are resolved by suppression when widening is insufficient
- Export is blocked when suppression rate exceeds 15%
- Export is blocked when n < 15
- QI column limit is enforced for populations 15-29 (max 3)
- QI column limit is enforced for populations 30+ (max 5)
- CSV output matches the expected format (metadata header, column order, data values)
- Suppression report JSON contains correct counts
- Linkage table is encrypted and contains correct mappings
- Each pipeline step creates an audit log entry

---

### Task 3: EVAL-FORM1 — Export Form and View

**What:** Create the web form and view for the evaluation export. The form has two stages: configuration (program, period, evaluator details, QI columns) and preview/confirm.

**New form: `apps/reports/forms.py`**

```python
class EvaluationExportForm(forms.Form):
    program = forms.ModelChoiceField(...)  # Programs user has access to
    period_start = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    period_end = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    
    # Evaluator details (all required)
    evaluator_name = forms.CharField(max_length=200)
    evaluator_email = forms.EmailField()
    evaluator_organisation = forms.CharField(max_length=200)
    evaluation_purpose = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    agreement_expiry = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="When does the data sharing agreement with this evaluator expire?"
    )
    
    # QI column selection (checkboxes)
    include_age_group = forms.BooleanField(required=False, initial=True)
    include_gender = forms.BooleanField(required=False, initial=True)
    include_ethnicity = forms.BooleanField(required=False)
    include_geography = forms.BooleanField(required=False)
    # Additional custom field groups marked as evaluation-exportable
    # (dynamically populated in __init__)
```

**New view: `apps/reports/views.py`**

Add `evaluation_export_form()`:

1. **GET**: Render the form. Check `can_create_evaluation_export(user)` — 403 if not.
2. **POST with action=preview**: Validate form, run `pipeline.run_preview()`, render preview template showing counts, suppressions, and generalisations. Include a hidden form with all original values plus a confirm button.
3. **POST with action=generate**: Run `pipeline.run_generate()`, create SecureExportLink:
   - `export_type = "evaluation_microdata"`
   - `contains_pii = False`
   - `is_elevated = True` (always — evaluation exports are always elevated)
   - `recipient = evaluator_email`
   - `client_count = exportable_count`
   - Store encrypted linkage blob (add a new field or use `filters_json`)
4. Create AuditLog entry with full metadata blob
5. Redirect to the SecureExportLink download page (existing flow handles the elevated delay)

**URL: `apps/reports/urls.py`**
- `path("evaluation-export/", views.evaluation_export_form, name="evaluation_export")`

**Templates:**

`templates/reports/evaluation_export.html`:
- Standard form layout using `{% include "includes/_form_field.html" %}` for all fields
- Evaluator details section with clear heading: "Evaluator Information (required for audit trail)"
- QI column checkboxes with population-size warning (shown via HTMX after program selection, or as static text)
- Warning banner: "This export contains de-identified individual-level data. All details will be recorded in the audit log."

`templates/reports/evaluation_export_preview.html`:
- Summary table: eligible → consented → exportable → suppressed
- Effective k-anonymity value
- Generalisations applied (list)
- Suppression details (if any records were suppressed, explain why)
- If blocked: red banner explaining why (population too small, too many QI columns, suppression rate too high) with no generate button
- If permitted: confirm button, cancel button
- The evaluator details echoed back for confirmation

**Navigation:**
- Add "Evaluation Export" link to the reports navigation menu
- Only visible to users with `report.evaluation_export` permission

**Tests:**
- Test: GET renders form for authorised user
- Test: GET returns 403 for unauthorised user
- Test: POST with action=preview returns preview with correct counts
- Test: POST with action=preview for blocked export shows block reason, no generate button
- Test: POST with action=generate creates SecureExportLink with correct fields
- Test: POST with action=generate creates AuditLog entry with correct metadata structure
- Test: evaluator fields are all required (form validation)
- Test: email field validates as email

---

### Task 4: EVAL-NAV1 — Navigation and SecureExportLink Integration

**What:** Wire the evaluation export into the existing navigation, reports landing page, and export link management.

**Changes:**

1. **Reports nav** — add "Evaluation Export" link, permission-gated
2. **SecureExportLink** — add `"evaluation_microdata"` to `export_type` choices. If the model uses a choices tuple, add the new value.
3. **Export links management page** (`/reports/export-links/`) — evaluation exports should appear here alongside other exports, with the evaluator email shown in the recipient column
4. **SecureExportLink model** — consider adding a `linkage_key_encrypted` field (TextField, nullable) for storing the encrypted linkage blob. Alternative: store in `filters_json`. Check which is cleaner.

**Translations:**
- Run `python manage.py translate_strings` after template changes
- Add French translations for all new UI strings:
  - "Evaluation Export" → "Exportation pour l'évaluation"
  - "Evaluator Information" → "Information sur l'évaluateur"
  - "Data sharing agreement expiry" → "Expiration de l'entente de partage de données"
  - "This export contains de-identified individual-level data" → "Cette exportation contient des données individuelles dépersonnalisées"
  - etc.

**Tests:**
- Test: navigation link appears for authorised user
- Test: navigation link hidden for unauthorised user
- Test: evaluation export appears in export links management page
- Test: evaluator email shows in recipient column

---

### Task 5: EVAL-ADMIN1 — Admin Configuration for Exportable Custom Fields

**What:** Allow admins to mark which custom field groups are available as quasi-identifiers in evaluation exports.

**Model change: `apps/clients/models.py`**
- Add `is_evaluation_exportable` BooleanField to `CustomFieldGroup` (default=False)
- Help text: "When enabled, fields in this group can be selected as demographic columns in evaluation exports."
- Only non-sensitive field groups should be marked exportable (enforce: if `is_sensitive=True` on any field in the group, block marking the group as exportable)

**Admin change:**
- Add checkbox to CustomFieldGroup admin form
- Validation: warn if group contains sensitive fields

**Pipeline integration:**
- In `EvaluationExportForm.__init__()`, dynamically add checkboxes for custom field groups where `is_evaluation_exportable=True`
- In `DeidentificationPipeline._extract_raw_data()`, include values from selected exportable custom field groups
- In `_generalise_quasi_identifiers()`, pass custom field values through as-is (they're already categorical)
- In `_compute_k_anonymity()`, include custom field values in QI tuple

**Migration:** One new field on CustomFieldGroup.

**Tests:**
- Test: custom field group marked exportable appears as checkbox in evaluation export form
- Test: custom field group not marked does not appear
- Test: sensitive field group cannot be marked exportable
- Test: custom field values included in k-anonymity computation

---

## Implementation Notes

### What to reuse (do not rebuild)

- `SecureExportLink` model and download flow — just add the new export_type
- Elevated export delay and admin notification — works as-is for evaluation exports
- `apps/reports/csv_utils.py` — CSV injection prevention
- `apps/reports/demographics.py` — age grouping logic (may need to adjust band sizes)
- `apps/reports/suppression.py` — small-cell suppression logic (adapt from cell-level to row-level)
- `AuditLog` model — no schema change needed, use the existing `metadata` JSONField
- `apps/reports/utils.py` — permission checking patterns

### What is new

- `apps/reports/deidentify.py` — the pipeline module (Task 2)
- `report.evaluation_export` permission (Task 1)
- `EvaluationExportForm` (Task 3)
- `evaluation_export_form` view (Task 3)
- `evaluation_export.html` and `evaluation_export_preview.html` templates (Task 3)
- `is_evaluation_exportable` field on CustomFieldGroup (Task 5)

### Order matters

Tasks 1 and 2 are independent and can be built in parallel. Task 3 depends on both 1 and 2. Task 4 depends on 3. Task 5 can be built after Task 2 (pipeline) but its integration into the form requires Task 3.

```
Task 1 (permission) ─────┐
                          ├──→ Task 3 (form/view) ──→ Task 4 (nav/integration)
Task 2 (pipeline) ───────┘                                    │
       │                                                       │
       └──→ Task 5 (admin config) ─── integrates into ────────┘
```

### Testing strategy

Run tests for each task as you complete it:
- `pytest tests/test_evaluation_export.py` (new file, covers Tasks 1-5)
- After Task 3, also run `pytest tests/test_reports.py` to ensure existing export tests still pass

Do NOT run the full test suite until all 5 tasks are complete.
