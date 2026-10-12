# LTE — Longitudinal Trajectory Export (Small-Population Evaluation Tier)

**Status:** Ready to build
**DRR:** [tasks/design-rationale/evaluation-microdata-export.md](design-rationale/evaluation-microdata-export.md)
**Approved by:** GK after two expert panel rounds (2026-04-09)
**Depends on:** Existing EME implementation (PR #617, #622, #623, #624), `DeidentificationPipeline` base class
**Scope owner (implementation):** new session can pick this up cold
**Scope reviewer (before merge):** GK reviews completed LTE for demographic suppression correctness, metric fuzzing, and community governance gating

## Stop and read this first

This is **not** a quick task. LTE is a second, structurally separate export tier with its own permission, its own form, its own pipeline class, its own audit category, its own review lifecycle, and its own tests. Before writing any code, read the following in full — do not skim:

1. **[tasks/design-rationale/evaluation-microdata-export.md](design-rationale/evaluation-microdata-export.md)** — the DRR in full. Pay special attention to:
   - Section **"Longitudinal Trajectory Export (LTE) — Small-Population Tier"** — the complete specification
   - Subsection **"The Core Reframe"** — the design principle (trade data richness for data safety; the analytical value comes from trajectories, not demographics)
   - Subsection **"What LTE Does NOT Export"** — the hard rules. No demographic fields. Ever. Not even "just age band."
   - Subsection **"Review and Cancel Window"** — the 5-business-day lifecycle, withdrawal rules, population snapshot, cancellation
   - Subsection **"What LTE Is NOT"** — the guardrails against bundling, trust-based carve-outs, research-grade use
   - **"Anti-Patterns — Do Not Build"** — at least four of these apply directly to this implementation. Know them cold before you touch the code.
2. **[apps/reports/deidentify.py](../apps/reports/deidentify.py)** — the existing `DeidentificationPipeline` class. Your LTE pipeline should **compose or subclass** this, not fork it. Read the 10-step structure and the dataclass definitions (`PreviewResult`, `GenerateResult`).
3. **[apps/reports/forms.py](../apps/reports/forms.py)** — find `EvaluationExportForm` (search for `class EvaluationExportForm`). Your LTE form is distinct but should follow the same patterns for program selection and validation.
4. **[apps/reports/views.py](../apps/reports/views.py)** — find `evaluation_export_form` (search for `def evaluation_export_form`). The LTE views will mirror but not share this one.
5. **[apps/reports/urls.py](../apps/reports/urls.py)** — understand where the existing `evaluation-export/` route is. Add LTE routes under a **distinct prefix** (suggestion: `longitudinal-trajectory-export/`), not as children of the existing route.
6. **[tests/test_export_permissions.py](../tests/test_export_permissions.py)** — read `EvaluatorExportPermissionTest` to understand the existing permission test patterns. Your LTE tests should live in a new class in the same file or a new file.
7. **[apps/reports/utils.py](../apps/reports/utils.py)** — find `can_create_evaluation_export`. You will add a sibling `can_create_lte_export` with stricter preconditions.

## The problem LTE solves

The existing Evaluation Microdata Export (EME) blocks programs with fewer than 15 participants entirely — `n < 15 → aggregate reports only`. This is correct for the EME's design (demographic microdata needs a large enough equivalence class population for k-anonymity to work) but it denies small programs the ability to evaluate outcomes they have already consented to. Small programs are precisely where rigorous evaluation matters most because aggregate averages cannot demonstrate impact at low n. They are also frequently the programs serving Indigenous, Black, newcomer, 2SLGBTQ+, disability, and other equity-deserving communities.

LTE is the answer. It is not a relaxation of EME. It is a different data product with different trade-offs:

- **Drops demographic fields entirely.** No age, no gender, no ethnicity, no geography. k-anonymity is trivially satisfied because there are no demographic columns to group on.
- **Keeps longitudinal individual rows** — pseudonymous study_id, enrolment quarter, exit quarter, session count, total hours, metric values at each measurement point.
- **Fuzzes trajectory values** to prevent re-identification by shape — metric values rounded to the scale unit, session count banded to 5, total hours banded to half-hour.
- **Is gated by REB approval, community governance, a 5-business-day review window, distributed admin oversight, and post-hoc privacy officer review** — not by a signed DSA alone.

The DRR is clear: "separate path, separate door, separate key." Everything about LTE must be structurally distinct from EME — different permission, different form, different URL prefix, different audit category, different UI labelling. Do not bundle it as a checkbox on the EME form. Do not reuse the EME permission.

## What to build

### 1. Data models + migration

Create `apps/reports/models.py` additions (or a new module `apps/reports/lte_models.py` if you prefer):

```python
class LTEExportRequest(models.Model):
    """A request to generate a Longitudinal Trajectory Export.

    One row per request. The lifecycle is:
      submitted -> review_and_cancel_window -> active -> downloaded -> expired
      (or at any point: cancelled, flagged, auto_cancelled)

    The record lives forever for audit purposes; the generated file
    lives on the SecureExportLink for the 24-hour download window
    after activation.
    """
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("flagged", "Flagged — privacy officer action required"),
        ("cancelled", "Cancelled"),
        ("auto_cancelled", "Auto-cancelled — population dropped below floor"),
        ("invalidated_by_withdrawal", "Invalidated — participant withdrew consent"),
        ("active", "Download link active"),
        ("downloaded", "Downloaded"),
        ("expired", "Expired without download"),
    ]

    submitted_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="lte_requests_submitted")
    submitted_at = models.DateTimeField(auto_now_add=True)
    program = models.ForeignKey("programs.Program", on_delete=models.PROTECT)
    period_start = models.DateField()
    period_end = models.DateField()

    # Preconditions (all required)
    reb_name = models.CharField(max_length=200)
    reb_approval_number = models.CharField(max_length=100)
    reb_approval_date = models.DateField()
    data_sharing_agreement_expiry = models.DateField()
    evaluator_name = models.CharField(max_length=200)
    evaluator_email = models.EmailField()
    evaluator_organisation = models.CharField(max_length=200)
    evaluator_degree = models.CharField(max_length=300)
    evaluator_years_experience = models.PositiveSmallIntegerField()
    evaluator_prior_programs = models.TextField()  # min 50 chars at form layer
    destruction_window_days = models.PositiveSmallIntegerField(
        choices=[(30, "30 days"), (60, "60 days"), (90, "90 days")]
    )
    purpose_statement = models.TextField()
    # Community governance signoff (nullable — only required if program flag is set)
    community_reviewer_name = models.CharField(max_length=200, blank=True)
    community_reviewer_affiliation = models.CharField(max_length=300, blank=True)
    community_framework_description = models.TextField(blank=True)  # for "other" flag
    community_signoff_date = models.DateField(null=True, blank=True)
    acknowledgement_confirmed = models.BooleanField()  # must be True to submit

    # Lifecycle state
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="submitted")
    window_activates_at = models.DateTimeField()  # 5 business days after submission
    population_snapshot = models.PositiveIntegerField()  # at submission time
    secure_export_link = models.OneToOneField(
        "SecureExportLink", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lte_request",
    )
    cancelled_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="lte_requests_cancelled")
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=500, blank=True)

    # Destruction attestation (updated after download, manual agency entry in v1)
    destruction_confirmed_at = models.DateTimeField(null=True, blank=True)
    destruction_confirmed_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="lte_destruction_confirmations")


class LTELifecycleEvent(models.Model):
    """Append-only log of state transitions on an LTEExportRequest.

    Lives alongside the request for quick reference; the canonical
    audit record also goes to the audit DB (separate from this).
    """
    request = models.ForeignKey(LTEExportRequest, on_delete=models.CASCADE, related_name="lifecycle_events")
    timestamp = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    event_type = models.CharField(max_length=50)  # "submitted", "flagged", "cancelled", "activated", "downloaded", "withdrawal_invalidation", "floor_auto_cancel"
    notes = models.TextField(blank=True)
```

Add **community governance fields to Program**:

```python
# apps/programs/models.py — additions to Program model
COMMUNITY_GOVERNANCE_NONE = ""
COMMUNITY_GOVERNANCE_OCAP = "ocap"
COMMUNITY_GOVERNANCE_EGAP = "egap"
COMMUNITY_GOVERNANCE_OTHER = "other"
COMMUNITY_GOVERNANCE_CHOICES = [
    (COMMUNITY_GOVERNANCE_NONE, "No specific framework"),
    (COMMUNITY_GOVERNANCE_OCAP, "OCAP (First Nations, Inuit, Métis)"),
    (COMMUNITY_GOVERNANCE_EGAP, "EGAP (Black communities)"),
    (COMMUNITY_GOVERNANCE_OTHER, "Other small-population community review"),
]

community_governance_framework = models.CharField(
    max_length=10, choices=COMMUNITY_GOVERNANCE_CHOICES, default=COMMUNITY_GOVERNANCE_NONE,
    help_text="If set, LTE exports on this program require community reviewer signoff.",
)
```

**Migrations:** run `makemigrations reports programs` and commit the migration files in the same commit as the model changes. Use a descriptive migration name: `add_lte_export_request` and `add_community_governance_framework_to_program`.

### 2. Permission + "no privacy officer designated = no LTE" enforcement

Add the permission to `apps/auth_app/permissions.py`:

```python
REPORT_EVALUATION_EXPORT_SMALL_POPULATION = "report.evaluation_export_small_population"
```

Register it in the permission map. **Do not grant it to any default role.** Do not infer it from any other role or flag. Explicit grant only.

Follow the existing EVAL-GOV1 pattern for the grant workflow if EVAL-GOV1 is merged by the time you build this. If EVAL-GOV1 is not yet merged, use the same per-user cache field pattern (`lte_export_granted` BooleanField on User, backed by an `LTEExportGrant` model if you want full audit parity). **Coordinate with whoever is building EVAL-GOV1 to avoid conflicting migration numbers on `apps/auth_app/`.**

Add a helper in `apps/reports/utils.py`:

```python
def can_create_lte_export(user) -> bool:
    """LTE has stricter preconditions than EME.

    Returns True if and only if:
      1. The user has report.evaluation_export_small_population permission
      2. The agency has at least one user with this permission (role is designated)

    Admin bypass does NOT apply — LTE is not available to admins by default.
    """
    if not user.is_authenticated:
        return False
    if not user.has_permission("report.evaluation_export_small_population"):
        return False
    return True


def lte_available_in_agency() -> bool:
    """Returns True iff the current tenant has at least one designated privacy officer."""
    from apps.auth_app.models import User
    return User.objects.filter(lte_export_granted=True).exists()
```

The form view must check `lte_available_in_agency()` before rendering. If no privacy officer is designated, the form is not reachable — return a helpful 403 or 404 with a message directing the admin to designate a privacy officer first.

### 3. Pipeline — `LTESmallPopulationPipeline` class

In `apps/reports/deidentify.py` (or a new file `apps/reports/lte_pipeline.py`), create a new class that composes or subclasses `DeidentificationPipeline`. Do not fork the code — reuse the base pipeline's extract, decrypt, consent filter, and output steps.

Key differences from `DeidentificationPipeline`:

1. **Skip the generalisation step entirely** — LTE has no QI columns to generalise.
2. **Strip ALL demographic fields at Step 4** — not just direct identifiers. Age, gender, ethnicity, geography, postal code, FSA, urban/rural, and anything derived from demographics must be dropped. This is a hard schema guarantee.
3. **Skip the k-anonymity check** — k is trivially `n` because there are no QI columns. Log the effective k as "trivially k=n (no QI columns)" in the audit metadata.
4. **Fuzz trajectory values before writing**:
   - Metric values: round to the natural unit of the scale (0-10 ordinal → nearest integer; 0-100 percentage → nearest 5; continuous → one decimal place or nearest unit)
   - Session count: round to nearest 5
   - Total hours: round to nearest 0.5
5. **Enforce the population floor**: default `n >= 10`, `n >= 15` for programs with `community_governance_framework in ("ocap", "egap")`. If below floor, block with a clear error — no override.
6. **Generate pseudonymous study_id** as a random UUID (not derived from record ID, not hashed from anything linkable).

Write a new `LTEPreviewResult` dataclass if the existing `PreviewResult` doesn't fit (it probably won't — LTE has no QI columns, no suppression rate, no equivalence class math).

### 4. Form — `LTEExportRequestForm`

In `apps/reports/forms.py`, add a new form class:

```python
class LTEExportRequestForm(ProgramSelectionMixin, forms.Form):
    """Longitudinal Trajectory Export request form.

    Strict validation — every field is required. Form rejects
    any submission where preconditions are missing or invalid.
    """
    # Period
    period_start = forms.DateField(...)
    period_end = forms.DateField(...)

    # REB
    reb_name = forms.CharField(max_length=200)
    reb_approval_number = forms.CharField(min_length=5, max_length=100)
    reb_approval_date = forms.DateField()

    # DSA
    data_sharing_agreement_expiry = forms.DateField()

    # Evaluator
    evaluator_name = forms.CharField(max_length=200)
    evaluator_email = forms.EmailField()
    evaluator_organisation = forms.CharField(max_length=200)
    evaluator_degree = forms.CharField(max_length=300, label=_("Evaluator degree or certification"))
    evaluator_years_experience = forms.IntegerField(min_value=0, max_value=60)
    evaluator_prior_programs = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        min_length=50,
        help_text=_("Describe at least two prior program evaluations this evaluator has conducted. Minimum 50 characters."),
    )

    # Destruction
    destruction_window_days = forms.ChoiceField(choices=[(30, "30 days"), (60, "60 days"), (90, "90 days")])

    # Community governance (conditionally required)
    community_reviewer_name = forms.CharField(max_length=200, required=False)
    community_reviewer_affiliation = forms.CharField(max_length=300, required=False)
    community_framework_description = forms.CharField(widget=forms.Textarea, required=False)
    community_signoff_date = forms.DateField(required=False)

    # Purpose
    purpose_statement = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), min_length=30)

    # Acknowledgement
    acknowledgement_confirmed = forms.BooleanField(
        label=_("I have read the re-identification risk notice and confirm this export is for program evaluation, not research. Research-grade data access is handled through a separate workflow and is not available through this form."),
    )

    def clean(self):
        cleaned = super().clean()
        program = cleaned.get("program")
        if program and program.community_governance_framework in ("ocap", "egap", "other"):
            required_fields = ["community_reviewer_name", "community_reviewer_affiliation", "community_signoff_date"]
            if program.community_governance_framework == "other":
                required_fields.append("community_framework_description")
            for f in required_fields:
                if not cleaned.get(f):
                    self.add_error(f, _("Required for programs with community governance framework."))
        return cleaned
```

### 5. Views + URLs

Add a new URL prefix in `apps/reports/urls.py`:

```python
# Longitudinal Trajectory Export (DRR: evaluation-microdata-export.md, LTE section)
path("longitudinal-trajectory-export/", views.lte_list, name="lte_list"),
path("longitudinal-trajectory-export/new/", views.lte_submit, name="lte_submit"),
path("longitudinal-trajectory-export/<int:request_id>/", views.lte_detail, name="lte_detail"),
path("longitudinal-trajectory-export/<int:request_id>/cancel/", views.lte_cancel, name="lte_cancel"),
path("longitudinal-trajectory-export/<int:request_id>/flag/", views.lte_flag_concerns, name="lte_flag_concerns"),
path("longitudinal-trajectory-export/<int:request_id>/download/", views.lte_download, name="lte_download"),
```

Add the corresponding view functions in `apps/reports/views.py`:

- `lte_list` — shows all LTE requests in the agency with status, countdown, actions (cancel, flag, download)
- `lte_submit` — GET renders form; POST validates, runs pipeline in preview mode, then creates `LTEExportRequest`, sends admin notifications, starts the review-and-cancel window
- `lte_detail` — shows the request metadata, lifecycle events, and actions available based on status
- `lte_cancel` — POST only, accepts cancellation reason, marks status `cancelled`, logs lifecycle event
- `lte_flag_concerns` — POST only (from the "Flag concerns" email link), marks status `flagged`, notifies privacy officer, freezes countdown
- `lte_download` — only accessible while status is `active`, proxies through the SecureExportLink

All views must check `can_create_lte_export` OR `has_permission("report.evaluation_export_small_population")` as appropriate. All views must check `lte_available_in_agency()` at the top.

### 6. Review-and-cancel window lifecycle

Write a helper module `apps/reports/lte_lifecycle.py` (or put these as methods on the model — your call):

```python
def calculate_window_end(submitted_at: datetime, business_days: int = 5) -> datetime:
    """Return the datetime at which the review-and-cancel window ends.

    Counts 5 business days (Mon-Fri) in the agency's configured timezone,
    excluding any configured holidays. See settings.LTE_EXCLUDED_HOLIDAYS
    for the holiday list (may be empty in v1).
    """
    ...


def check_population_snapshot_for_lte(request: LTEExportRequest) -> None:
    """Re-run the consent query and compare to the snapshot.

    If a participant has withdrawn consent since submission,
    invalidate the request and re-run the pipeline.

    If the effective population drops below the floor,
    auto-cancel the request.

    Call this from:
      - a daily background task
      - the pre-download hook
      - the post-withdrawal signal on ClientFile consent change
    """
    ...


def activate_window_if_elapsed(request: LTEExportRequest) -> None:
    """If the window has elapsed and status is 'submitted', activate it.

    Creates the SecureExportLink and transitions status -> 'active'.
    """
    ...
```

The window lifecycle requires a scheduled job or signal-driven checks. Options:

- **Preferred**: Django management command `check_lte_window_lifecycle` run every 15 minutes by cron (or once daily if that's enough)
- **Alternative**: check lifecycle at view time — every time `lte_list` or `lte_detail` is accessed, re-evaluate window state for all pending requests. Simpler but slower.

Document your choice in a comment at the top of the lifecycle module.

### 7. Distributed oversight — admin notification + flag-concerns flow

At submission time, send an email to **all agency admins** with:

- Program name, evaluator, purpose
- Review-and-cancel window countdown (expressed as "5 business days, activates at <datetime>")
- A **"Flag concerns"** link containing a signed token that lands on `lte_flag_concerns` and marks the request flagged without requiring admin login (the token is scoped to the specific request and expires when the window closes)
- A **"View in KoNote"** link for admins who want to cancel or see details

Follow the existing email template patterns in `templates/emails/` or wherever the EME notifications live. Respect bilingual requirements: EN/FR translations for all email strings.

Flagging freezes the window countdown. The privacy officer resolves the flag either by dismissing it (window resumes) or cancelling the request. Dismissal restarts the remaining countdown from the time of dismissal — do not fast-forward.

### 8. Post-hoc review task + agency-wide rate limit

At submission time, create an admin task: `"Review LTE export for <program> submitted <date>"`, assigned to the agency's designated privacy officer (the first user with `lte_export_granted=True`).

The task must be marked resolved (or flagged as a concern) **before the same agency can generate another LTE**. The rate limit is agency-wide, not per-program. Enforce at submission time:

```python
def can_submit_new_lte(agency) -> tuple[bool, str | None]:
    pending_reviews = LTEExportRequest.objects.filter(
        status__in=["submitted", "active", "downloaded"],
        post_hoc_review_task__status="pending",
    ).exists()
    if pending_reviews:
        return False, "A prior LTE export is pending privacy officer review. Resolve it before submitting a new request."
    return True, None
```

Use whatever admin-task model KoNote has for this. If there isn't one, add a simple `LTEReviewTask` model alongside `LTEExportRequest`.

### 9. Audit log integration — distinct category

Write a single audit log entry at each lifecycle transition to the audit DB:

```python
AuditLog.objects.using("audit").create(
    event_type="longitudinal_trajectory_export.submitted",  # or .activated, .cancelled, .downloaded, .flagged, etc.
    actor_id=user.pk,
    metadata={
        "export_category": "longitudinal_trajectory_export",
        "lte_request_id": request.pk,
        # ... all the fields from the DRR's "Enhanced Audit Metadata" section
    },
)
```

The `export_category` field must be `longitudinal_trajectory_export`, **not** a flag or subtype of `evaluation_microdata`. Alerts and reports should be able to filter on this category independently.

Do NOT reuse the `SecureExportLink.agency_notes` field for LTE metadata — that field serves EME and will get confusing. Store the full lifecycle metadata on the `LTEExportRequest` row itself.

### 10. Templates + navigation + translations

- `templates/reports/lte_list.html` — table showing all LTE requests with status, countdown, actions
- `templates/reports/lte_submit.html` — the submission form with conditional community governance section (shown only when the selected program has a governance flag)
- `templates/reports/lte_detail.html` — request detail view with lifecycle events and status-dependent actions
- `templates/emails/lte_submitted.html` + `.txt` — admin notification at submission time (EN and FR)
- `templates/emails/lte_flagged.html` + `.txt` — privacy officer notification when an admin flags concerns
- `templates/emails/lte_destruction_reminder.html` + `.txt` — sent at end of destruction window if no acknowledgement recorded

Navigation: add an **"Evaluation Export (Small Population)"** entry to the admin reports menu, distinct from the existing Evaluation Export entry. Visibility conditional on `can_create_lte_export(user)` AND `lte_available_in_agency()`. Use Pico CSS patterns consistent with the rest of the admin UI.

After any template with `{% trans %}` strings is added or modified, run `python manage.py translate_strings` and fill in any empty French translations before committing.

### 11. Tests — new test file or class

Create `tests/test_lte.py` (or add to `tests/test_exports.py` — your call based on what's there) with coverage for:

- **Permission gating**: only users with `report.evaluation_export_small_population` can reach LTE views; admin bypass does NOT grant LTE access
- **"No privacy officer = no LTE"**: if no user in the agency has the permission, the form is unreachable
- **Form validation**: each precondition rejects invalid/missing input with a clear error (REB number too short, evaluator prior programs under 50 chars, acknowledgement unchecked, etc.)
- **Community governance gating**: program with OCAP flag requires community reviewer signoff; submission without it fails
- **Population floor**: n < 10 blocks; n ≥ 10 allows (unless OCAP/EGAP and n < 15); n < 15 on OCAP program blocks
- **Pipeline correctness**: output rows contain NO demographic fields; metric values are rounded; session counts are banded; study_ids are random UUIDs
- **Review-and-cancel window**: business days calculation (Friday submission activates 5 business days later, not 5 calendar days); cancellation during window discards; re-submission starts fresh window
- **Withdrawal invalidation**: mid-window withdrawal invalidates and re-runs the pipeline
- **Population snapshot**: new enrolments during the window do NOT enter the file; withdrawals DO remove rows
- **Auto-cancel on floor drop**: if withdrawals drop population below floor, status → `auto_cancelled`
- **Distributed oversight**: admin notification email sent; flag-concerns link works; flagged status freezes the window
- **Post-hoc review rate limit**: pending prior LTE blocks new LTE submission agency-wide
- **Audit category**: every lifecycle transition writes an audit entry with `export_category=longitudinal_trajectory_export`
- **CSV output**: metadata header includes the "for program evaluation, not research" warning; no demographic columns present

Test approach: **prefer integration tests over unit tests** for the pipeline and form — use the existing `seed_eval_export_demo` patterns to build a realistic test fixture, then run the LTE pipeline end-to-end and assert on outputs.

### 12. QA scenarios, documentation, final checks

1. Add new pages to `konote-qa-scenarios/pages/page-inventory.yaml`:
   - `/reports/longitudinal-trajectory-export/`
   - `/reports/longitudinal-trajectory-export/new/`
   - `/reports/longitudinal-trajectory-export/<id>/`
   - `/reports/longitudinal-trajectory-export/<id>/cancel/`
   - `/reports/longitudinal-trajectory-export/<id>/flag/`
2. Write at least one QA scenario in `konote-qa-scenarios/scenarios/admin/` for the LTE happy path: submit → window countdown visible → admin notification received → privacy officer review task created → window elapses → download link active → file contains no demographics
3. Write a second scenario for the small-population block: submit with n < 10 → blocked with clear error → directed to aggregate reports
4. Write a third scenario for OCAP-flagged program with missing community signoff → form rejects submission
5. Update `docs/admin/reporting.md` with an LTE section (separate from EME section) explaining when to use LTE, the preconditions, and the review window
6. Update `docs/evaluation-export-guide.md` (the ED-facing guide) to mention LTE as an option for small-population evaluation
7. Create `docs/lte-privacy-officer-guide.md` — a short guide for the designated privacy officer on their responsibilities (review requests, resolve flags, confirm destruction)

## Out of scope for LTE v1 (leave for later tasks)

- **Long-format longitudinal export** — the DRR uses wide format (one row per participant, multiple metric columns for each time point). Long format (one row per measurement point) is a deferred consideration.
- **Synthetic data option** — deferred pending validation research
- **REB registry verification** — v1 captures the REB approval number as a string, no external verification
- **Automated evaluator-facing destruction attestation UI** — v1 uses manual agency entry
- **Fast-path early approval** — explicitly deferred as an anti-pattern. Do not add a "privacy officer approves early" button.
- **Secure delivery channel from agency to evaluator** — v1 assumes the agency has its own secure channel
- **Cross-program LTE** — v1 is single-program only

## Anti-patterns — do not build these

Read **[tasks/design-rationale/evaluation-microdata-export.md](design-rationale/evaluation-microdata-export.md)** "Anti-Patterns" section in full before starting. The following apply directly to LTE and must not be built under any circumstances:

| Do NOT build | Why |
|---|---|
| **Any demographic field in LTE output**, including "just age band" or "just urban/rural" | The LTE's re-identification defence IS the absence of these fields. Adding any of them re-opens the full re-identification surface. |
| **Bundling LTE as a toggle or checkbox on the EME form** | Separate path, separate door, separate key. The LTE must have its own permission, its own form, its own URL prefix, its own audit category. |
| **"DSA as an unlock" framing** | A signed DSA does not justify LTE access. REB + community governance + compensating controls are the gates. The DSA is captured for the audit record but does not bypass anything. |
| **Fast-path early approval to shorten the window** | Rubber-stamp risk. Do not add a "privacy officer approves early" button or any mechanism that lets someone activate the download link before the 5-business-day window elapses. |
| **Lowering the k floor below 5** | k = 5 is fixed across all KoNote tiers. LTE satisfies it trivially because it has no QI columns — do not add a lower "k = 3" mode for any reason. |
| **LTE without REB approval** | REB is mandatory. Do not add a "REB not required" checkbox or override. |
| **LTE bypass for OCAP/EGAP programs without community signoff** | Agency ED authorisation is not a substitute for community review. |
| **Making LTE available to agencies without a designated privacy officer** | The form must be unreachable until the permission is explicitly granted to at least one user. |
| **Reusing the existing `report.evaluation_export` permission** | Bundling erodes the structural separation. Create a new permission. |
| **Storing the linkage table (study_id ↔ real record_id) indefinitely** | The linkage blob should be encrypted, stored on the LTEExportRequest, and destroyed when the export is cancelled or expires. It exists only to support participant withdrawal requests ("remove my data"). |

## Acceptance criteria

Before marking LTE done:

1. [ ] `LTEExportRequest`, `LTELifecycleEvent` models exist with migrations committed
2. [ ] Program model has `community_governance_framework` field with migration
3. [ ] New permission `report.evaluation_export_small_population` registered and NOT granted by default
4. [ ] `can_create_lte_export` and `lte_available_in_agency` helpers in place
5. [ ] `LTEExportRequestForm` validates all preconditions strictly; community governance fields are conditionally required
6. [ ] `LTESmallPopulationPipeline` runs end-to-end on a test fixture and produces CSV with NO demographic columns
7. [ ] Metric values, session counts, and total hours are correctly fuzzed per the DRR rules
8. [ ] Population floor enforced: n < 10 blocks; n < 15 blocks for OCAP/EGAP programs
9. [ ] Review-and-cancel window correctly calculates 5 business days; countdown visible on submitter and privacy officer dashboards
10. [ ] Submission sends admin notification email with working "Flag concerns" link
11. [ ] Flagging freezes the window; resolving unflags it; cancellation discards the file
12. [ ] Withdrawal during the window invalidates and re-runs the pipeline
13. [ ] Population snapshot: new enrolments do not enter the file, withdrawals remove rows
14. [ ] Auto-cancel works when withdrawals drop population below floor
15. [ ] Post-hoc privacy officer review task is auto-created; a pending task blocks new LTE submission agency-wide
16. [ ] Audit log entries use `export_category=longitudinal_trajectory_export`, distinct from EME
17. [ ] LTE is reachable via Admin → Reports → Evaluation Export (Small Population), only when permission is granted and privacy officer is designated
18. [ ] All user-facing strings are translated (EN + FR)
19. [ ] All tests pass: pipeline, form, views, lifecycle, rate limit, audit, templates
20. [ ] `konote-qa-scenarios/pages/page-inventory.yaml` updated with 6 new LTE pages
21. [ ] At least 3 new QA scenarios (happy path, floor block, OCAP without signoff)
22. [ ] Documentation updated: admin guide, ED guide, privacy officer guide
23. [ ] TODO.md LTE tasks marked complete and moved to Recently Done
24. [ ] **GK reviews completed LTE implementation before merge to develop** — verifies demographic suppression, metric fuzzing, community governance gating, and overall alignment with the DRR. Add a comment to the PR tagging GK for review.

## Development notes

- **Branch naming**: `feat/lte-small-population-export`
- **Commit discipline**: commit after each of the 12 numbered steps above. The PR will be large — reviewers need the logical chunks to track the build.
- **Pipeline reuse**: do not copy-paste the 10-step EME pipeline. Subclass or compose. If you find yourself duplicating more than 20 lines from `DeidentificationPipeline`, stop and refactor into shared helpers.
- **Run locally**: Django commands run on the VPS, not locally. Use `/deploy-to-vps` or `ssh konote-vps` to run migrations and tests. See the global `CLAUDE.md` notes on VPS workflow.
- **Run these before merging**: `/simplify` (checks for reuse and over-engineering), `/review-session` (final audit against the DRR), and GK review.
- **Consultation gate**: LTE is explicitly a GK consultation gate (evaluation methodology, data modelling). **Do not merge to develop without GK sign-off.**
- **Two worktrees risk**: if EVAL-GOV1 is still in flight, coordinate migration numbers on `apps/auth_app/` and `apps/reports/`. Check `git log --oneline develop` for recent migration files before running `makemigrations`.

## What success looks like

A privacy officer at a small agency opens **Admin → Reports → Evaluation Export (Small Population)**. They see an empty list and a "New request" button. They click it. The form shows: program selector (listing their 11-participant peer support program with an OCAP flag indicator), period selector, REB section, evaluator credentials (structured, not free text), destruction window, purpose statement, and a community governance section that appears because the program is OCAP-flagged, asking for the community reviewer name, affiliation, and signoff date. They fill everything in, check the acknowledgement, click submit.

The form validates. They see a preview page: "11 eligible, 11 consented, 11 will be exported. No demographic fields. Metric values rounded to nearest integer. Session counts banded to nearest 5. Total hours banded to nearest half-hour. Review and cancel window: 5 business days, activates 2026-04-16 at 17:00."

They confirm. The submission is recorded. Every admin in the agency receives an email with a "Flag concerns" link and a "View in KoNote" link. The privacy officer's dashboard now shows a review task. The submitter's export history shows a new row with a visible countdown.

Four business days later, one admin clicks "Flag concerns" because they noticed the REB approval is from the evaluator's own institution and want to double-check it. The window countdown freezes. The privacy officer gets a flag notification. They check with the evaluator, confirm the REB is legitimate, and dismiss the flag. The countdown resumes from where it froze.

One more business day. The window elapses. The status transitions to `active`. The submitter's dashboard now shows a download button. They download the file once — a CSV with a warning header (`This file is for PROGRAM EVALUATION, not research`), no demographic columns, 11 pseudonymous rows with longitudinal metric trajectories. The link expires 24 hours later. The agency delivers the file to the evaluator through their own secure channel.

Ninety days after download, the destruction reminder email arrives. The agency contacts the evaluator, records the destruction acknowledgement manually in the detail view, and the LTE lifecycle completes.

That's the LTE working as designed: rigorous evaluation of a small program, with safeguards matched to the risk profile, and no demographic detail anywhere in the file.
