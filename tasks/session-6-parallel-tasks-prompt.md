# Session 6: Verify + Build — Parallel Tasks

## Pre-flight (do first, sequentially)

```bash
git pull origin develop
git branch --show-current
```

If on `main` or `develop`, create a feature branch:
```bash
git checkout -b feat/session-6-verify-build-design
```

---

## Overview — What's Actually Needed

Research found that several items the user listed are **already built** but not marked done in TODO.md. Also found that DQ1 (plausibility warnings) and OPS3 (email) are already built — removing false blockers.

| Tier | Tasks | Work Type |
|------|-------|-----------|
| **Verify & mark done** | DOC-PERM1/2/3, DOC-DEMO1, QA-PA-TEST1/2, QA-R7-PRIVACY2 | Read code, spot-check, update TODO.md |
| **Build** | QA-R7-EXEC-COMPLIANCE1, SRE1, DQ1-TUNE | New code — views, templates, models, tests |

**Session 7 queue** (approved, deferred due to file conflicts with DQ1-TUNE on `apps/admin_settings/`):
- DEPLOY-CONFIG-UI1 — read-only configuration dashboard
- ADMIN-UX1 — better admin UI guidance

---

## Parallel agents (launch all at once — no file conflicts between them)

### Agent A: Verify & Mark Done — 7 tasks (housekeeping)

**Branch:** main session branch (`feat/session-6-verify-build-design`)
**Files touched:** `TODO.md` only (reading many files, writing only TODO.md)
**Estimated time:** 30 minutes

This agent verifies already-built items and updates TODO.md. **Only this agent touches TODO.md.** No other agent should modify it.

#### A1: Verify DOC-PERM1 — DV-safe mode & GATED access doc

1. Read `docs/admin/dv-safe-mode-and-gated-access.md`
2. Spot-check 3 claims against code:
   - Does `apps/clients/dv_views.py` implement the DV-safe mode toggle as described?
   - Does `apps/auth_app/permissions.py` have the GATED access check?
   - Is DV-safe mode Tier 2+ as the doc states?
3. If accurate → mark `[x]` with today's date, move to Recently Done

#### A2: Verify DOC-PERM2 — Per-field front desk access doc

1. Read `docs/admin/per-field-front-desk-access.md`
2. Spot-check 3 claims against code:
   - Does `apps/admin_settings/field_access_views.py` exist and handle the access levels?
   - Are the three access levels (Hidden / View only / View and edit) implemented?
   - Is this Tier 2+ only?
3. If accurate → mark `[x]` with today's date, move to Recently Done

#### A3: Verify DOC-PERM3 — Access tiers doc

1. Read `docs/admin/access-tiers.md`
2. Spot-check 3 claims against code:
   - Do `apps/admin_settings/models.py` and `apps/auth_app/` implement the 3-tier model?
   - Are the tier capabilities correct (compare doc table vs. actual permission checks)?
   - Does the front desk defaults table match the code?
3. If accurate → mark `[x]` with today's date, move to Recently Done

#### A4: Verify DOC-DEMO1 — Demo data engine guide

1. Read `docs/demo-data-guide.md`
2. Spot-check against code:
   - Does the CLI command `python manage.py generate_demo_data` accept the flags listed in the guide? Check `apps/admin_settings/management/commands/generate_demo_data.py`
   - Does the admin UI flow match `templates/admin_settings/demo_data.html`?
   - Does the profile JSON schema match `seeds/demo_data_profile_example.json`?
   - Are the demo user accounts and passwords correct?
3. If accurate → mark `[x]` with today's date, move to Recently Done

#### A5: Verify QA-PA-TEST1 — Groups attendance seed data

1. Check `tests/scenario_eval/scenario_runner.py` for `seed_group_attendance_data()` or similar
2. Check `tests/integration/test_page_capture.py` for matching seeding logic
3. Verify the seeding creates: 1 Group, 8+ GroupMemberships, 12+ GroupSessions, 96+ GroupSessionAttendance records
4. Check `apps/groups/models.py` — verify no new required fields have been added since the seeding code was written
5. If seeding code exists and matches the `page-inventory.yaml` requirements → mark `[x]` with today's date, move to Recently Done
6. If broken or missing → fix it, then mark done

#### A6: Verify QA-PA-TEST2 — Staff messages seed data

1. Check `tests/scenario_eval/scenario_runner.py` for `seed_staff_messages()` or similar
2. Check `tests/integration/test_page_capture.py` for matching seeding logic
3. Verify seeding creates 5+ `StaffMessage` objects for personas DS1, DS1b, DS2, PM1
4. Check `apps/communications/models.py` — verify no new required fields have been added
5. If seeding code exists and is correct → mark `[x]` with today's date, move to Recently Done
6. If broken or missing → fix it, then mark done

#### A7: Verify QA-R7-PRIVACY2 — Note sharing toggle

The toggle already appears to exist in the codebase:
- `templates/clients/_tab_info.html` lines 162-204: toggle section with POST form, gated on `features.cross_program_note_sharing`, PM/admin gets form, staff gets read-only
- `apps/clients/views.py`: `client_sharing_toggle` view
- `apps/clients/models.py` line 211: `cross_program_sharing` field with `default`/`consent`/`restrict` choices

**Verify against the approved design** (`tasks/note-sharing-toggle.md`):

1. Read the toggle view — does it set the field to `consent` (ON) and `restrict` (OFF) as designed?
2. Does the UI show a **computed binary** (ON when effective sharing is enabled, OFF when disabled)?
3. When agency-level `cross_program_note_sharing` is OFF, is the toggle hidden entirely?
4. Is there a confirmation step when turning sharing OFF?
5. Is the toggle restricted to PM/Admin only (workers cannot change it)?
6. Is the state change logged to the audit database?
7. Do tests exist in `tests/test_cross_program_security.py` for the toggle?

If 5+ of 7 checks pass → mark `[x]` with today's date, move to Recently Done, move from Parking Lot to Recently Done.
If gaps exist → list them for the main session to fix (small fixes, not a full rebuild).

#### A-Final: Update TODO.md

After all verifications, update TODO.md:
- Mark verified items as `[x]` with today's date
- Move them to Recently Done section
- For items that were in Parking Lot (QA-R7-PRIVACY2), also remove from Parking Lot
- Also move QA-R7-EXEC-COMPLIANCE1, SRE1, and DQ1-TUNE from Parking Lot to Active Work (user has approved building them)
- Move DEPLOY-CONFIG-UI1 and ADMIN-UX1 from Parking Lot: Needs Review to Coming Up (approved for Session 7, false blockers cleared)
- If Recently Done exceeds ~15 items, move oldest batch (Wave 1 Sprint items) to `tasks/ARCHIVE.md`

Commit after updating TODO.md.

---

### Agent B: QA-R7-EXEC-COMPLIANCE1 — Verify Banner + Build Compliance Summary Helper

**Branch:** worktree (`feat/exec-compliance-banner`)
**Design file:** `tasks/compliance-banner.md` (read this first — it is the canonical design, GK-approved)
**Estimated time:** 1-2 hours (reduced — banner already exists on develop)

The privacy compliance banner was already built and merged to develop. It includes:
- View logic: `apps/clients/dashboard_views.py` lines ~1244-1308 (queries pending erasure + data access requests, scoped to user's programs)
- Template: `templates/clients/executive_dashboard.html` lines ~175-200 (conditional banner, hidden when nothing pending)

Agent B **verifies** the existing banner and **builds only the missing piece**: the annual compliance summary helper for board reports.

#### Step 1: Verify the existing banner

Read these files and confirm:
- `apps/clients/dashboard_views.py` — find the privacy compliance banner section (~line 1244). Verify:
  - Erasure requests are scoped to `accessible_client_ids` (not unscoped — unscoped would be a PHIPA violation)
  - Both erasure and data access request types are handled
  - Banner data is only computed for executive/admin roles
- `templates/clients/executive_dashboard.html` — find the `privacy_banner_items` section (~line 176). Verify:
  - Banner is hidden when `privacy_banner_items` is empty
  - Erasure items show count and days-ago
  - Data access items show days remaining and overdue highlighting
  - Translation tags (`{% trans %}`, `{% blocktrans %}`) are present

If any issues found, fix them. If the banner is working correctly, move on.

#### Step 2: Build annual compliance summary helper

**File:** `apps/reports/export_engine.py`

Add a helper function that generates a privacy compliance summary for board reports:

```python
def get_compliance_summary(start_date, end_date):
    """
    Generate a privacy compliance summary for board reports.
    Returns a dict with aggregate counts — no PII.
    """
    from apps.clients.models import ErasureRequest

    # Completed erasure requests in the period
    completed = ErasureRequest.objects.filter(
        status="anonymised",
        completed_at__range=(start_date, end_date),
    )
    completed_count = completed.count()

    # Still pending at period end
    pending_at_end = ErasureRequest.objects.filter(
        status="pending",
        requested_at__lte=end_date,
    ).count()

    if completed_count == 0 and pending_at_end == 0:
        return {"summary_text": _("No privacy requests were received this period.")}

    # Average processing time for completed requests
    from django.db.models import Avg, F
    avg_days = None
    if completed_count > 0:
        avg_result = completed.annotate(
            processing_time=F("completed_at") - F("requested_at")
        ).aggregate(avg=Avg("processing_time"))["avg"]
        avg_days = avg_result.days if avg_result else 0

    # Check if all completed within 30-day statutory deadline
    from datetime import timedelta
    overdue_count = 0
    if completed_count > 0:
        overdue_count = completed.filter(
            completed_at__gt=F("requested_at") + timedelta(days=30)
        ).count()

    return {
        "completed_count": completed_count,
        "pending_at_end": pending_at_end,
        "avg_processing_days": avg_days,
        "overdue_count": overdue_count,
        "all_within_deadline": overdue_count == 0,
        "summary_text": _(
            "Privacy requests processed: %(count)d "
            "(average %(days)d days, %(deadline)s)"
        ) % {
            "count": completed_count,
            "days": avg_days or 0,
            "deadline": (
                _("all within statutory deadline")
                if overdue_count == 0
                else _("%(overdue)d exceeded 30-day statutory deadline") % {"overdue": overdue_count}
            ),
        } + (
            _(" — %(pending)d still pending at period end") % {"pending": pending_at_end}
            if pending_at_end > 0 else ""
        ),
    }
```

#### Step 3: Wire into compliance summary page

Check if a compliance summary view exists in `apps/reports/views.py` (it was built earlier — look for `compliance_summary` or similar). If it exists, add the privacy summary to its context:

```python
from apps.reports.export_engine import get_compliance_summary
# ... in the view:
context["privacy_summary"] = get_compliance_summary(start_date, end_date)
```

If the compliance summary view doesn't exist on develop, skip this step — the helper function will be available when the view is added later.

#### Step 4: Tests

**File:** `tests/test_exports.py` (add to existing report tests)

Tests to write:
1. `get_compliance_summary()` returns "No privacy requests" when count is 0
2. `get_compliance_summary()` returns correct completed count and average days
3. `get_compliance_summary()` flags overdue requests correctly
4. `get_compliance_summary()` includes pending-at-period-end count
5. Existing banner shows correctly when pending erasure requests exist (integration test)
6. Existing banner is hidden when nothing is pending (integration test)

Run: `pytest tests/test_exports.py -v -k "compliance_summary"`

#### Step 5: Translations

Run `python manage.py translate_strings`. Add French translations for new strings only:
- "No privacy requests were received this period." → "Aucune demande de confidentialité n'a été reçue durant cette période."
- "Privacy requests processed:" → "Demandes de confidentialité traitées :"
- "all within statutory deadline" → "toutes dans les délais légaux"
- "exceeded 30-day statutory deadline" → "ont dépassé le délai légal de 30 jours"
- "still pending at period end" → "toujours en attente à la fin de la période"

Commit after translations compile.

---

### Agent C: SRE1 — Serious Reportable Events

**Branch:** worktree (`feat/serious-reportable-events`)
**Design file:** `tasks/serious-reportable-events.md` (read this first — it is the requirements doc)
**Estimated time:** 4-5 hours (largest task in this session)

Build the serious reportable events (SRE) system by extending the existing events app.

#### Step 1: Understand the existing events system

Read these files before writing any code:
- `apps/events/models.py` — EventType, Event, Alert models
- `apps/events/views.py` — event CRUD views
- `apps/events/forms.py` — event forms
- `apps/events/urls.py` — URL patterns
- `apps/events/manage_urls.py` — admin URL patterns
- `templates/events/` — all event templates
- `apps/events/management/commands/seed_event_types.py` — how event types are seeded

#### Step 2: Add SRE category model

**File:** `apps/events/models.py`

Add a new model for SRE categories (configurable per agency):

```python
class SRECategory(models.Model):
    """Serious Reportable Event category — predefined list, configurable per agency."""
    name = models.CharField(max_length=100)
    name_fr = models.CharField(
        max_length=100, blank=True, default="",
        help_text=_("French name (displayed when language is French)"),
    )
    description = models.TextField(blank=True)
    description_fr = models.TextField(
        blank=True, default="",
        help_text=_("French description (displayed when language is French)"),
    )
    severity = models.IntegerField(
        choices=[(1, _("Level 1 — Immediate")), (2, _("Level 2 — Within 24 hours")), (3, _("Level 3 — Within 7 days"))],
        default=2,
        help_text=_("Reporting urgency level"),
    )
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = _("SRE category")
        verbose_name_plural = _("SRE categories")

    def get_translated_name(self):
        """Return French name when active language is French, else English."""
        from django.utils.translation import get_language
        if get_language() == "fr" and self.name_fr:
            return self.name_fr
        return self.name

    def __str__(self):
        return self.get_translated_name()
```

**Important:** Use `category.get_translated_name()` in templates, not `category.name`, so French-speaking staff see French category names.

#### Step 3: Add SRE fields to Event model

**File:** `apps/events/models.py` — `Event` model

Add fields to the existing Event model:

```python
# Serious Reportable Event fields
is_sre = models.BooleanField(
    default=False,
    help_text=_("Flag this event as a Serious Reportable Event"),
)
sre_category = models.ForeignKey(
    "SRECategory",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="events",
    help_text=_("SRE category — required when is_sre is True"),
)
sre_flagged_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="sre_flagged_events",
)
sre_flagged_at = models.DateTimeField(null=True, blank=True)
sre_notifications_sent = models.BooleanField(default=False)
```

Add validation in `Event.clean()`:
```python
if self.is_sre and not self.sre_category:
    raise ValidationError({"sre_category": _("SRE category is required when flagging as a Serious Reportable Event.")})
```

#### Step 4: Seed default SRE categories

**File:** `apps/events/management/commands/seed_sre_categories.py` (new)

Create a management command that seeds the 12 default categories from the design doc:

```python
DEFAULT_SRE_CATEGORIES = [
    {"name": "Death of a participant", "name_fr": "Décès d'un participant", "severity": 1, "display_order": 1},
    {"name": "Serious injury requiring emergency medical care", "name_fr": "Blessure grave nécessitant des soins médicaux d'urgence", "severity": 1, "display_order": 2},
    {"name": "Allegation or disclosure of abuse or neglect", "name_fr": "Allégation ou divulgation de mauvais traitements ou de négligence", "severity": 1, "display_order": 3},
    {"name": "Use of physical restraint or seclusion", "name_fr": "Utilisation de contention physique ou d'isolement", "severity": 2, "display_order": 4},
    {"name": "Missing person / elopement", "name_fr": "Personne disparue / fugue", "severity": 1, "display_order": 5},
    {"name": "Suicide attempt or self-harm requiring intervention", "name_fr": "Tentative de suicide ou automutilation nécessitant une intervention", "severity": 1, "display_order": 6},
    {"name": "Medication error with adverse outcome", "name_fr": "Erreur de médication avec effet indésirable", "severity": 2, "display_order": 7},
    {"name": "Property damage or fire", "name_fr": "Dommages matériels ou incendie", "severity": 2, "display_order": 8},
    {"name": "Threat or assault involving participants or staff", "name_fr": "Menace ou agression impliquant des participants ou du personnel", "severity": 1, "display_order": 9},
    {"name": "Police involvement or criminal incident", "name_fr": "Intervention policière ou incident criminel", "severity": 2, "display_order": 10},
    {"name": "Communicable disease outbreak", "name_fr": "Éclosion de maladie transmissible", "severity": 2, "display_order": 11},
    {"name": "Client rights violation", "name_fr": "Violation des droits du client", "severity": 3, "display_order": 12},
]
```

Use `get_or_create` to be idempotent.

#### Step 5: Migrations

Run `python manage.py makemigrations events` to create:
1. Schema migration for `SRECategory` model
2. Schema migration for new `Event` fields (`is_sre`, `sre_category`, `sre_flagged_by`, `sre_flagged_at`, `sre_notifications_sent`)

Then run `python manage.py migrate`.

#### Step 6: Update event forms

**File:** `apps/events/forms.py`

Add SRE fields to the event form. The SRE section should:
- Show a checkbox "Flag as Serious Reportable Event"
- When checked, show a dropdown of active `SRECategory` choices
- Use JavaScript to show/hide the category dropdown based on the checkbox state

```python
class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [...existing fields..., "is_sre", "sre_category"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_sre") and not cleaned.get("sre_category"):
            self.add_error("sre_category", _("Please select an SRE category."))
        return cleaned
```

#### Step 7: Update event create/edit views

**File:** `apps/events/views.py`

In the event create and edit views, after saving an event that has `is_sre=True`:

1. Set `sre_flagged_by` to the current user
2. Set `sre_flagged_at` to `timezone.now()`
3. Log to audit database: `AuditLog.objects.using("audit").create(...)` with action "SRE_FLAGGED"
4. **Send email notification** — email infrastructure IS available (`apps/communications/services.py` has `send_email_message()` and `send_staff_email()`). Create a function `send_sre_notification(event)` that:
   - Identifies **program-relevant** recipients — not all admins globally. Query `UserProgramRole` for users with admin or executive roles in the event's program. Also include any users where `is_admin=True` (site-wide admins always notified). Pattern from existing code: `User.objects.filter(is_admin=True, is_active=True)` for site admins.
   - Uses `send_email_message()` from `apps/communications/services.py`
   - Includes: event summary, SRE category name (bilingual — use `get_translated_name()`), severity level, date, and a link to the event detail page
   - If email sending fails, **log the failure but don't block the save** — the SRE should still be recorded even if notification fails
   - For Level 1 (Immediate) severity, add "[URGENT]" to the email subject line

For un-flagging (setting `is_sre` from True to False):
- Require Admin role — PMs and workers cannot un-flag an SRE
- Log to audit database with action "SRE_UNFLAGGED" including who did it and why

#### Step 8: Update event templates

**File:** `templates/events/event_form.html` (or the relevant form template)

Add the SRE section to the form. Use a `<fieldset>` with a legend:

```html
<fieldset>
    <legend>{% trans "Serious Reportable Event" %}</legend>
    <label>
        {{ form.is_sre }}
        {% trans "Flag as Serious Reportable Event (SRE)" %}
    </label>
    <div id="sre-category-section" style="display: none;">
        <label for="{{ form.sre_category.id_for_label }}">
            {% trans "SRE Category" %}
        </label>
        {{ form.sre_category }}
    </div>
</fieldset>
```

Add JavaScript to show/hide the category dropdown:
```javascript
document.getElementById("id_is_sre").addEventListener("change", function() {
    document.getElementById("sre-category-section").style.display =
        this.checked ? "block" : "none";
});
```

**File:** `templates/events/event_detail.html` (or the relevant detail template)

Show an SRE badge when `event.is_sre`:
```html
{% if event.is_sre %}
<span class="badge sre-badge">{% trans "SRE" %}: {{ event.sre_category.get_translated_name }}</span>
<small>{% blocktrans with user=event.sre_flagged_by.get_display_name date=event.sre_flagged_at %}Flagged by {{ user }} on {{ date }}{% endblocktrans %}</small>
{% endif %}
```

#### Step 9: SRE admin management views

**File:** `apps/events/manage_urls.py` and `apps/events/views.py`

Add admin views for SRE category management:
- List all SRE categories (active and archived)
- Create new SRE category
- Edit SRE category
- Archive/unarchive SRE category

Follow the same pattern as `EventType` admin views (already in the codebase). These are simple CRUD views gated on Admin role.

#### Step 10: SRE report view

**File:** `apps/events/views.py`

Add a report view that shows:
- All SRE events in a date range, filterable by program and category
- Aggregate counts by category (e.g., "3 restraint events, 1 missing person")
- Date range picker (reuse the existing report date range pattern)
- Access: Admin and Executive roles only

**Template:** `templates/events/sre_report.html`

This is a read-only report page — no data modification.

#### Step 11: Tests

**File:** `tests/test_events.py` (create if it doesn't exist, or add to existing)

Tests to write:
1. SRECategory creation with valid data
2. Event with `is_sre=True` requires `sre_category`
3. Event with `is_sre=False` does not require `sre_category`
4. SRE flagging sets `sre_flagged_by` and `sre_flagged_at`
5. SRE flagging creates audit log entry
6. Un-flagging requires Admin role (PM gets 403)
7. Un-flagging creates audit log entry
8. SRE report shows correct counts by category
9. SRE report is accessible to Admin/Executive, not to Staff
10. Seed command creates all 12 default categories
11. Seed command is idempotent (running twice doesn't duplicate)

Run: `pytest tests/test_events.py -v`

#### Step 12: Translations

Run `python manage.py translate_strings`. Key strings to translate:
- "Serious Reportable Event" → "Événement grave à signaler"
- "Flag as Serious Reportable Event (SRE)" → "Signaler comme événement grave à signaler (ÉGS)"
- "SRE Category" → "Catégorie d'ÉGS"
- All 12 category names (e.g., "Death of a participant" → "Décès d'un participant")
- Severity levels
- "SRE Report" → "Rapport d'ÉGS"

Commit after each major step.

#### Step 13: QA scenario consideration

Check if `konote-qa-scenarios/pages/page-inventory.yaml` needs new entries for:
- The SRE report page
- The SRE category admin pages

If so, add them to the page inventory with appropriate page names, URLs, and prerequisites.

---

### Agent D: DQ1-TUNE — Plausibility Threshold Tuning Dashboard

**Branch:** worktree (`feat/dq1-tune-threshold-tuning`)
**Prerequisite confirmed:** DQ1 base system IS built — `warn_min`/`warn_max` fields exist on `MetricDefinition` (migration 0017), `checkPlausibility()` JS function exists in `app.js`, seed thresholds set for 7 financial metrics (migration 0018).
**Files touched:** `apps/notes/models.py`, `apps/notes/forms.py`, `apps/admin_settings/views.py`, `apps/admin_settings/urls.py`, `templates/admin_settings/dq_tuning.html`, tests
**Estimated time:** 3-4 hours

Build the override tracking + threshold tuning dashboard so admins can see which plausibility thresholds are too tight or too loose.

#### Step 1: Understand the existing DQ1 system

Read these files before writing any code:
- `tasks/data-validation-design.md` — overall DQ design (DQ1 + DQ2)
- `apps/plans/models.py` — `MetricDefinition` model, look at `warn_min`/`warn_max` fields (lines ~50-57)
- `apps/notes/forms.py` — `MetricValueForm`, look for `plausibility_confirmed` hidden field
- `static/js/app.js` — `checkPlausibility()` function (look at how it stores confirmation state)
- `apps/plans/migrations/0017_plausibility_warnings.py` — schema migration
- `apps/plans/migrations/0018_set_financial_warn_thresholds.py` — seed data

#### Step 2: Add PlausibilityOverrideLog model

**File:** `apps/notes/models.py`

```python
class PlausibilityOverrideLog(models.Model):
    """Tracks when plausibility warnings are triggered and whether staff override or correct them.
    Used to tune warn_min/warn_max thresholds over time."""
    metric_definition = models.ForeignKey(
        "plans.MetricDefinition",
        on_delete=models.CASCADE,
        related_name="plausibility_overrides",
    )
    progress_note = models.ForeignKey(
        "ProgressNote",
        on_delete=models.CASCADE,
        related_name="plausibility_overrides",
        null=True, blank=True,
    )
    entered_value = models.FloatField(
        help_text=_("The value that triggered the plausibility warning"),
    )
    threshold_type = models.CharField(
        max_length=20,
        choices=[("warn_min", _("Below minimum")), ("warn_max", _("Above maximum"))],
    )
    threshold_value = models.FloatField(
        help_text=_("The warn_min or warn_max value that was breached"),
    )
    action = models.CharField(
        max_length=20,
        choices=[("confirmed", _("Staff confirmed the value")), ("corrected", _("Staff corrected the value"))],
    )
    corrected_value = models.FloatField(
        null=True, blank=True,
        help_text=_("The corrected value, if staff chose to change it"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("plausibility override log")
        verbose_name_plural = _("plausibility override logs")
```

This writes to the **main database** (not audit) — it's operational data used for threshold tuning, not a security audit trail.

#### Step 3: Migrations

Run `python manage.py makemigrations notes` then `python manage.py migrate`.

#### Step 4: Hook override logging into MetricValueForm

**File:** `apps/notes/forms.py`

In `MetricValueForm`, after save:
- Check if `plausibility_confirmed` was set to True
- If so, determine which threshold was breached (compare entered value against `warn_min`/`warn_max` from the metric definition)
- Create a `PlausibilityOverrideLog` entry with action="confirmed"
- If the user changed the value after the warning (submitted a different value than what triggered the warning), log as action="corrected" and record both values

This requires the form to track the original flagged value. Check if the JS `checkPlausibility()` stores the original value that triggered the warning. If not, the form needs a hidden field `plausibility_original_value` that the JS sets when a warning fires.

#### Step 5: Build the admin tuning dashboard view

**File:** `apps/admin_settings/views.py`

Add a view `plausibility_tuning_dashboard` accessible to Admin role only.

The view queries `PlausibilityOverrideLog` and groups by metric definition:

```python
from apps.notes.models import PlausibilityOverrideLog
from django.db.models import Count, Q, Avg

def plausibility_tuning_dashboard(request):
    # Per-metric statistics
    metrics_with_overrides = PlausibilityOverrideLog.objects.values(
        "metric_definition__id",
        "metric_definition__name",
        "metric_definition__warn_min",
        "metric_definition__warn_max",
    ).annotate(
        total_warnings=Count("id"),
        confirmed_count=Count("id", filter=Q(action="confirmed")),
        corrected_count=Count("id", filter=Q(action="corrected")),
        avg_confirmed_value=Avg("entered_value", filter=Q(action="confirmed")),
    ).order_by("-total_warnings")

    # Calculate override rate for each metric
    for m in metrics_with_overrides:
        total = m["total_warnings"]
        m["override_rate"] = round(m["confirmed_count"] / total * 100) if total > 0 else 0
        # Colour coding: green (<30%), yellow (30-80%), red (>80%)
        if m["override_rate"] < 30:
            m["status"] = "good"  # threshold working well
        elif m["override_rate"] < 80:
            m["status"] = "review"  # might need adjustment
        else:
            m["status"] = "tight"  # threshold likely too tight

    context = {
        "metrics": metrics_with_overrides,
        "page_title": _("Plausibility Threshold Tuning"),
    }
    return render(request, "admin_settings/dq_tuning.html", context)
```

Support optional date range filter (last 30/90/365 days) and program filter via query parameters.

#### Step 6: Add URL pattern

**File:** `apps/admin_settings/urls.py`

Add: `path("plausibility-tuning/", views.plausibility_tuning_dashboard, name="plausibility_tuning"),`

Ensure it's within the admin-only URL group.

#### Step 7: Build the template

**File:** `templates/admin_settings/dq_tuning.html` (new)

Display a table with columns:
- Metric name
- Current thresholds (warn_min — warn_max)
- Total warnings (with date range filter)
- Override rate (% confirmed vs. corrected)
- Average confirmed value
- Status indicator (colour-coded: green/yellow/red)
- Recommendation text:
  - Green (<30%): "Threshold working well"
  - Yellow (30-80%): "Consider reviewing threshold"
  - Red (>80%): "Threshold likely too tight — staff override most warnings"

Add a date range filter at the top (30 days / 90 days / 1 year / All time) using simple `<select>` + form submit.

**Empty state:** When no `PlausibilityOverrideLog` entries exist (which will be the case initially, since override logging is new), show an explanatory message instead of an empty table:

```html
{% if not metrics %}
<p>{% trans "No plausibility warnings have been recorded yet." %}</p>
<p>{% trans "This dashboard will show threshold tuning recommendations after staff begin recording metric values that trigger plausibility warnings." %}</p>
{% endif %}
```

Use Pico CSS classes. No external dependencies.

#### Step 8: Tests

**File:** `tests/test_notes.py` (add to existing)

Tests to write:
1. `PlausibilityOverrideLog` creation with valid data
2. Override logging triggers when form saves with `plausibility_confirmed=True`
3. Corrected value is logged when staff changes the value after warning
4. Tuning dashboard is accessible to Admin role
5. Tuning dashboard returns 403 for Staff role
6. Tuning dashboard shows correct override rate calculation
7. Date range filter correctly limits results
8. Metric with 0 overrides doesn't appear in the dashboard (no noise)

Run: `pytest tests/test_notes.py -v -k "plausibility"`

#### Step 9: Translations

Run `python manage.py translate_strings`. Key strings:
- "Plausibility Threshold Tuning" → "Ajustement des seuils de plausibilité"
- "Below minimum" / "Above maximum" → "En dessous du minimum" / "Au-dessus du maximum"
- "Staff confirmed the value" → "Le personnel a confirmé la valeur"
- "Staff corrected the value" → "Le personnel a corrigé la valeur"
- "Threshold working well" → "Seuil fonctionnel"
- "Consider reviewing threshold" → "Envisager de réviser le seuil"
- "Threshold likely too tight" → "Seuil probablement trop strict"
- "No plausibility warnings have been recorded yet." → "Aucun avertissement de plausibilité n'a encore été enregistré."
- "This dashboard will show threshold tuning recommendations after staff begin recording metric values that trigger plausibility warnings." → "Ce tableau de bord affichera des recommandations d'ajustement des seuils une fois que le personnel commencera à enregistrer des valeurs déclenchant des avertissements de plausibilité."

Commit after each major step.

---

## After all agents finish

1. Review each agent's work — check for consistency, correct spelling, no file conflicts
2. For Agent B (compliance banner): run `pytest tests/test_clients.py -v -k "compliance or erasure"` to verify tests pass
3. For Agent C (SRE): run `pytest tests/test_events.py -v` to verify tests pass
4. For Agent D (DQ1-TUNE): run `pytest tests/test_notes.py -v -k "plausibility"` to verify tests pass
5. Run `python manage.py translate_strings` if any templates were modified (Agents B, C, D)
6. Verify TODO.md is consistent and accurate (Agent A should have updated it)
7. Push each worktree branch and create PRs to `develop`:
   - PR for Agent A (verify + TODO update — main branch)
   - PR for Agent B (compliance banner — worktree)
   - PR for Agent C (SRE — worktree)
   - PR for Agent D (DQ1-TUNE — worktree)
8. After merging PRs, pull develop into the main repo directory

## File conflict matrix (why these are safe in parallel)

| Agent | Files touched | Conflicts with |
|-------|--------------|----------------|
| A (Verify) | `TODO.md`, reads many files (no edits outside TODO) | None — only agent touching TODO.md |
| B (Compliance banner) | `apps/clients/dashboard_views.py`, `templates/clients/_dashboard_executive_summary.html`, `apps/reports/export_engine.py`, `static/css/main.css`, `tests/test_clients.py`, `locale/` | None |
| C (SRE) | `apps/events/models.py`, `apps/events/views.py`, `apps/events/forms.py`, `apps/events/urls.py`, `apps/events/manage_urls.py`, `templates/events/`, `tests/test_events.py`, `locale/` | Potential locale conflict with B and D — resolve by having C commit locale changes last |
| D (DQ1-TUNE) | `apps/notes/models.py`, `apps/notes/forms.py`, `apps/admin_settings/views.py`, `apps/admin_settings/urls.py`, `templates/admin_settings/dq_tuning.html`, `tests/test_notes.py`, `locale/` | Potential locale conflict with B and C — resolve by committing locale changes last |

**Translation strategy:** Each agent (B, C, D) runs `python manage.py translate_strings` and adds French translations within its own worktree. This ensures each PR ships with complete translations (no untranslated strings in production). When PRs merge sequentially to develop, the second and third merges will have merge conflicts on `django.po` — these are easy additive conflicts (both sides add new entries). Resolve by accepting both sets of additions. After all PRs merge, run `python manage.py translate_strings` once more on develop as a safety net to verify all strings are compiled.

---

## Session 7 Queue (approved, build next)

These tasks were approved by the user but conflict with DQ1-TUNE on `apps/admin_settings/` files, so they run after Session 6 merges:

1. **DEPLOY-CONFIG-UI1** — Read-only configuration dashboard showing all active settings at a glance. NOT blocked by SETUP1-UI (false dependency — all settings models are populated). ~4-5 hours.

2. **ADMIN-UX1** — Better admin UI guidance for terminology, metrics, templates. UX enhancement to existing admin pages. NOT blocked by anything. ~3-4 hours.
