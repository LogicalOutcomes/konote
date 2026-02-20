# PHIPA Consent Enforcement + Role-Based Dashboard — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enforce cross-program sharing consent in views (PHIPA-ENFORCE1) and build role-based dashboard views (DASH-ROLES1).

**Architecture:** Agency-level feature toggle (default ON = share) with per-client tri-state override controls note visibility across programs. Dashboard home page detects user role and renders different content: staff sees caseload, PM sees program health, executive sees inline aggregate metrics.

**Tech Stack:** Django 5, Django ORM querysets, HTMX, Pico CSS, existing FeatureToggle and UserProgramRole models.

**Branch:** `feat/portal-q1-implementation` (already checked out in worktree)

---

## Part A: PHIPA Consent Enforcement (PHIPA-ENFORCE1)

### Task A1: Add feature toggle for cross-program note sharing

**Files:**
- Modify: `apps/admin_settings/views.py:123-138`

**Step 1: Add the feature toggle**

In `apps/admin_settings/views.py`, add `cross_program_note_sharing` to `DEFAULT_FEATURES` dict and to `FEATURES_DEFAULT_ENABLED` set:

```python
# In DEFAULT_FEATURES dict (line 123), add after "surveys" entry:
    "cross_program_note_sharing": _lazy("Share clinical notes across programs for shared participants"),

# In FEATURES_DEFAULT_ENABLED set (line 138), add:
FEATURES_DEFAULT_ENABLED = {"require_client_consent", "portal_journal", "portal_messaging", "cross_program_note_sharing"}
```

**Step 2: Commit**

```bash
git add apps/admin_settings/views.py
git commit -m "feat: add cross_program_note_sharing feature toggle (PHIPA-ENFORCE1)"
```

---

### Task A2: Change client model field from Boolean to tri-state CharField

**Files:**
- Modify: `apps/clients/models.py:172-183`
- Create: `apps/clients/migrations/0023_cross_program_sharing_tristate.py` (via makemigrations)

**Step 1: Update the model field**

Replace the existing BooleanField block (lines 172-183) in `apps/clients/models.py`:

```python
    # Cross-program sharing (PHIPA compliance)
    # Controls whether clinical notes from other programs are visible for this
    # client. "default" follows the agency-level feature toggle. "consent"
    # always shares. "restrict" never shares across programs.
    SHARING_CHOICES = [
        ("default", _("Follow agency setting")),
        ("consent", _("Share across programs")),
        ("restrict", _("Restrict to one program")),
    ]
    cross_program_sharing = models.CharField(
        max_length=20,
        choices=SHARING_CHOICES,
        default="default",
        help_text=_(
            "Controls whether clinical notes are visible across programs "
            "for this participant. Most participants use the agency default."
        ),
    )
```

**Step 2: Create the migration**

Run: `python manage.py makemigrations clients --name cross_program_sharing_tristate`

This will generate `0023_cross_program_sharing_tristate.py`. The auto-generated migration will handle removing the old BooleanField and adding the new CharField. However, we need a data migration to preserve existing consent=True values.

**Step 3: Edit the generated migration to include data migration**

The auto-migration will likely be a `RemoveField` + `AddField` (since the name changed from `cross_program_sharing_consent` to `cross_program_sharing`). We need to ensure data is preserved. Edit the generated migration to use `RenameField` first, then `AlterField`:

Replace the generated operations with:

```python
from django.db import migrations, models


def migrate_boolean_to_tristate(apps, schema_editor):
    """Convert old Boolean (True/False) to new tri-state (consent/default)."""
    ClientFile = apps.get_model("clients", "ClientFile")
    # True → "consent" (explicit opt-in), False → "default" (follow agency)
    ClientFile.objects.filter(cross_program_sharing_consent=True).update(
        cross_program_sharing_consent="consent"
    )
    ClientFile.objects.filter(cross_program_sharing_consent=False).update(
        cross_program_sharing_consent="default"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("clients", "0022_fix_contact_field_ordering"),
    ]

    operations = [
        # Step 1: Change field type from BooleanField to CharField (keeps old name)
        migrations.AlterField(
            model_name="clientfile",
            name="cross_program_sharing_consent",
            field=models.CharField(
                max_length=20,
                default="default",
                help_text="Controls whether clinical notes are visible across programs for this participant. Most participants use the agency default.",
            ),
        ),
        # Step 2: Migrate data (True→"consent", False→"default")
        migrations.RunPython(migrate_boolean_to_tristate, migrations.RunPython.noop),
        # Step 3: Rename field
        migrations.RenameField(
            model_name="clientfile",
            old_name="cross_program_sharing_consent",
            new_name="cross_program_sharing",
        ),
    ]
```

**Step 4: Run migration**

Run: `python manage.py migrate clients`

**Step 5: Commit**

```bash
git add apps/clients/models.py apps/clients/migrations/0023_cross_program_sharing_tristate.py
git commit -m "feat: change cross_program_sharing to tri-state CharField (PHIPA-ENFORCE1)"
```

---

### Task A3: Update forms and views for new field

**Files:**
- Modify: `apps/clients/forms.py:148-155`
- Modify: `apps/clients/views.py:472-474` and `509`

**Step 1: Update the form field**

In `apps/clients/forms.py`, replace the BooleanField (lines 148-155):

```python
    cross_program_sharing = forms.ChoiceField(
        required=False,
        choices=[
            ("default", _("Follow agency setting")),
            ("consent", _("Share across programs")),
            ("restrict", _("Restrict to one program")),
        ],
        initial="default",
        label=_("Cross-program note sharing"),
        help_text=_(
            "Controls whether clinical notes from other programs are visible "
            "for this participant. Most participants should use the agency default."
        ),
        widget=forms.Select,
    )
```

**Step 2: Update the transfer view**

In `apps/clients/views.py`, update the save logic (lines 472-474):

```python
            # Update cross-program sharing preference
            client.cross_program_sharing = form.cleaned_data.get(
                "cross_program_sharing", "default"
            )
```

And update the form initial data (line 509):

```python
                "cross_program_sharing": client.cross_program_sharing,
```

**Step 3: Commit**

```bash
git add apps/clients/forms.py apps/clients/views.py
git commit -m "feat: update forms and views for tri-state sharing field (PHIPA-ENFORCE1)"
```

---

### Task A4: Add consent filter helper functions

**Files:**
- Modify: `apps/programs/access.py` (add after `build_program_display_context`, line 180)

**Step 1: Write the failing tests first**

Add to `tests/test_cross_program_security.py` — new test class after `CrossProgramSecurityTest`:

```python
from apps.admin_settings.models import FeatureToggle
from apps.notes.models import ProgressNote


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CrossProgramConsentTest(TestCase):
    """Verify PHIPA consent enforcement filters notes correctly."""

    databases = {"default", "audit"}

    @classmethod
    def setUpTestData(cls):
        enc_module._fernet = None

        # Two programs
        cls.program_a = Program.objects.create(name="Housing Support", status="active")
        cls.program_b = Program.objects.create(name="Mental Health", status="active")

        # Multi-program staff — access to both programs
        cls.multi_staff = User.objects.create_user(
            username="multi", password="testpass123", display_name="Multi Worker",
        )
        UserProgramRole.objects.create(
            user=cls.multi_staff, program=cls.program_a, role="staff",
        )
        UserProgramRole.objects.create(
            user=cls.multi_staff, program=cls.program_b, role="staff",
        )

        # Client enrolled in both programs
        cls.shared_client = ClientFile.objects.create(
            is_demo=False, status="active",
        )
        ClientProgramEnrolment.objects.create(
            client_file=cls.shared_client, program=cls.program_a, status="enrolled",
        )
        ClientProgramEnrolment.objects.create(
            client_file=cls.shared_client, program=cls.program_b, status="enrolled",
        )

        # Notes in each program
        cls.note_a = ProgressNote.objects.create(
            client_file=cls.shared_client, author=cls.multi_staff,
            author_program=cls.program_a, note_type="quick",
            notes_text="Housing note",
        )
        cls.note_b = ProgressNote.objects.create(
            client_file=cls.shared_client, author=cls.multi_staff,
            author_program=cls.program_b, note_type="quick",
            notes_text="Mental health note",
        )
        # Legacy note with no program
        cls.note_null = ProgressNote.objects.create(
            client_file=cls.shared_client, author=cls.multi_staff,
            author_program=None, note_type="quick",
            notes_text="Legacy note",
        )

    def setUp(self):
        enc_module._fernet = None
        self.client.login(username="multi", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None

    def _set_agency_sharing(self, enabled):
        """Set the agency-level cross_program_note_sharing toggle."""
        from django.core.cache import cache
        cache.clear()
        FeatureToggle.objects.update_or_create(
            feature_key="cross_program_note_sharing",
            defaults={"is_enabled": enabled},
        )

    def test_agency_on_client_default_sees_all_notes(self):
        """Agency sharing ON + client default → all notes visible."""
        self._set_agency_sharing(True)
        self.shared_client.cross_program_sharing = "default"
        self.shared_client.save()
        resp = self.client.get(f"/participants/{self.shared_client.pk}/notes/")
        self.assertEqual(resp.status_code, 200)
        note_ids = {n.pk for n in resp.context["page"].object_list}
        self.assertIn(self.note_a.pk, note_ids)
        self.assertIn(self.note_b.pk, note_ids)
        self.assertIn(self.note_null.pk, note_ids)

    def test_agency_on_client_restrict_sees_one_program(self):
        """Agency sharing ON + client restrict → only viewing program notes."""
        self._set_agency_sharing(True)
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()
        resp = self.client.get(f"/participants/{self.shared_client.pk}/notes/")
        self.assertEqual(resp.status_code, 200)
        note_ids = {n.pk for n in resp.context["page"].object_list}
        # Should see one program's note + null note, but NOT both programs
        self.assertIn(self.note_null.pk, note_ids)
        # Exactly one of note_a or note_b visible (depends on get_author_program)
        has_a = self.note_a.pk in note_ids
        has_b = self.note_b.pk in note_ids
        self.assertTrue(has_a != has_b, "Should see exactly one program's notes")

    def test_agency_off_client_default_sees_one_program(self):
        """Agency sharing OFF + client default → only viewing program notes."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "default"
        self.shared_client.save()
        resp = self.client.get(f"/participants/{self.shared_client.pk}/notes/")
        self.assertEqual(resp.status_code, 200)
        note_ids = {n.pk for n in resp.context["page"].object_list}
        self.assertIn(self.note_null.pk, note_ids)
        has_a = self.note_a.pk in note_ids
        has_b = self.note_b.pk in note_ids
        self.assertTrue(has_a != has_b, "Should see exactly one program's notes")

    def test_agency_off_client_consent_sees_all_notes(self):
        """Agency sharing OFF + client consent → all notes visible."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "consent"
        self.shared_client.save()
        resp = self.client.get(f"/participants/{self.shared_client.pk}/notes/")
        self.assertEqual(resp.status_code, 200)
        note_ids = {n.pk for n in resp.context["page"].object_list}
        self.assertIn(self.note_a.pk, note_ids)
        self.assertIn(self.note_b.pk, note_ids)

    def test_single_shared_program_no_op(self):
        """Single shared program → filter is a no-op regardless of settings."""
        # Create single-program staff
        single_staff = User.objects.create_user(
            username="single", password="testpass123", display_name="Single Worker",
        )
        UserProgramRole.objects.create(
            user=single_staff, program=self.program_a, role="staff",
        )
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "default"
        self.shared_client.save()
        self.client.login(username="single", password="testpass123")
        resp = self.client.get(f"/participants/{self.shared_client.pk}/notes/")
        self.assertEqual(resp.status_code, 200)
        note_ids = {n.pk for n in resp.context["page"].object_list}
        # Single-program user always sees their program's notes + null
        self.assertIn(self.note_a.pk, note_ids)
        self.assertIn(self.note_null.pk, note_ids)
        self.assertNotIn(self.note_b.pk, note_ids)

    def test_null_author_program_always_visible(self):
        """Notes with author_program=None always visible regardless of consent."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()
        resp = self.client.get(f"/participants/{self.shared_client.pk}/notes/")
        self.assertEqual(resp.status_code, 200)
        note_ids = {n.pk for n in resp.context["page"].object_list}
        self.assertIn(self.note_null.pk, note_ids)

    def test_template_indicator_shown_when_filtering(self):
        """Template shows indicator when consent filtering is active."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "default"
        self.shared_client.save()
        resp = self.client.get(f"/participants/{self.shared_client.pk}/notes/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context.get("consent_viewing_program"))

    def test_template_indicator_hidden_when_sharing(self):
        """Template does NOT show indicator when sharing is enabled."""
        self._set_agency_sharing(True)
        self.shared_client.cross_program_sharing = "default"
        self.shared_client.save()
        resp = self.client.get(f"/participants/{self.shared_client.pk}/notes/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context.get("consent_viewing_program"))
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cross_program_security.py::CrossProgramConsentTest -v`

Expected: All 8 tests FAIL (helper functions don't exist yet, field doesn't match).

**Step 3: Add helper functions to access.py**

In `apps/programs/access.py`, add after `build_program_display_context()` (after line 180):

```python
def should_share_across_programs(client, agency_shares_by_default):
    """Determine if cross-program notes should be visible for this client.

    Combines the agency-level feature toggle with the per-client override.
    Returns True if notes from all shared programs should be visible.

    Logic:
    - client.cross_program_sharing == "consent" → always share
    - client.cross_program_sharing == "restrict" → never share
    - client.cross_program_sharing == "default" → follow agency toggle
    """
    sharing = getattr(client, "cross_program_sharing", "default")
    if sharing == "consent":
        return True
    if sharing == "restrict":
        return False
    return agency_shares_by_default


def apply_consent_filter(notes_qs, client, user, user_program_ids):
    """Apply PHIPA cross-program consent filtering to a notes queryset.

    PHIPA: Clinical notes should only be visible across programs when
    the agency or client has enabled sharing. This is the ONLY function
    that should apply consent-based filtering to note querysets.

    Returns (filtered_queryset, viewing_program_name_or_None).
    viewing_program_name is set when filtering is active (for template indicator).
    """
    from apps.clients.dashboard_views import _get_feature_flags

    flags = _get_feature_flags()
    agency_shares = flags.get("cross_program_note_sharing", True)

    if should_share_across_programs(client, agency_shares):
        return notes_qs, None  # No additional filtering needed

    # Determine the viewing program for this user+client pair
    viewing_program = get_author_program(user, client)
    if viewing_program:
        filtered = notes_qs.filter(
            Q(author_program=viewing_program) | Q(author_program__isnull=True)
        )
        return filtered, viewing_program.name

    # No shared program found — shouldn't happen (user passed access check)
    return notes_qs, None
```

**Step 4: Commit**

```bash
git add apps/programs/access.py tests/test_cross_program_security.py
git commit -m "feat: add consent filter helpers and 8 tests (PHIPA-ENFORCE1)"
```

---

### Task A5: Apply consent filter in note_list view

**Files:**
- Modify: `apps/notes/views.py:195-219` (note_list function)
- Modify: `apps/notes/views.py:279-298` (context dict + render)

**Step 1: Add import at top of note_list and apply filter**

After line 212 (the existing program filter), add:

```python
    # PHIPA: Apply cross-program consent filtering.
    # This is mandatory for all note querysets displaying clinical content.
    from apps.programs.access import apply_consent_filter
    notes, consent_viewing_program = apply_consent_filter(
        notes, client, request.user, user_program_ids,
    )
```

This goes right after the existing `.filter(Q(author_program_id__in=...))` line (line 212) and before the `.annotate(...)` call. Actually, since the existing queryset is chained, insert the consent filter call AFTER the full queryset is built (after line 218, before line 221):

In practice, after line 219 (the closing paren of the queryset), add:

```python
    # PHIPA: consent filter narrows to viewing program if sharing is off
    from apps.programs.access import apply_consent_filter
    notes, consent_viewing_program = apply_consent_filter(
        notes, client, request.user, user_program_ids,
    )
```

**Step 2: Pass indicator to template context**

In the context dict (around line 279-295), add `consent_viewing_program`:

```python
        "consent_viewing_program": consent_viewing_program,
```

**Step 3: Commit**

```bash
git add apps/notes/views.py
git commit -m "feat: apply consent filter in note_list view (PHIPA-ENFORCE1)"
```

---

### Task A6: Add template indicator banner

**Files:**
- Modify: `templates/notes/note_list.html` or `templates/notes/_tab_notes.html` (whichever renders the notes list)

**Step 1: Find the right template**

Check which template renders the note list content. The view returns either `notes/note_list.html` (full page) or `notes/_tab_notes.html` (HTMX partial). The indicator should appear in both — add it to `_tab_notes.html` since note_list.html likely includes it.

If `_tab_notes.html` is included from `note_list.html`, add the banner at the top of `_tab_notes.html`:

```html
{% load i18n %}
{% if consent_viewing_program %}
<div class="notice" role="status">
    <p>
        {% blocktrans with program=consent_viewing_program %}
        Showing notes from {{ program }} only. Cross-program sharing is not enabled for this participant.
        {% endblocktrans %}
    </p>
</div>
{% endif %}
```

If `_tab_notes.html` is NOT included from `note_list.html`, add it to `note_list.html` just before the notes list section.

**Step 2: Add the blocktrans msgid to .po file**

Since this uses `{% blocktrans %}`, manually add the msgid to `locale/fr/LC_MESSAGES/django.po`:

```
#. PHIPA consent indicator on notes timeline
#: templates/notes/_tab_notes.html
msgid "Showing notes from %(program)s only. Cross-program sharing is not enabled for this participant."
msgstr "Affichage des notes de %(program)s uniquement. Le partage entre programmes n\u2019est pas activ\u00e9 pour ce participant."
```

**Step 3: Run translate_strings to compile**

Run: `python manage.py translate_strings`

**Step 4: Commit**

```bash
git add templates/notes/ locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo
git commit -m "feat: add consent filtering indicator to notes timeline (PHIPA-ENFORCE1)"
```

---

### Task A7: Run PHIPA tests and verify

**Step 1: Run the consent tests**

Run: `pytest tests/test_cross_program_security.py -v`

Expected: All tests PASS (both existing CrossProgramSecurityTest and new CrossProgramConsentTest).

**Step 2: Run related test files**

Run: `pytest tests/test_home_dashboard.py -v`

Expected: All 4 existing tests PASS (consent filter doesn't affect dashboard).

**Step 3: Commit if any fixes were needed**

---

## Part B: Role-Based Dashboard Views (DASH-ROLES1)

### Task B1: Add role detection to home view

**Files:**
- Modify: `apps/clients/urls_home.py:10` (import) and `47-48` (role detection) and `127-145` (context)

**Step 1: Write failing tests**

Add to `tests/test_home_dashboard.py`, in a new class or extending `HomeDashboardPermissionsTest`. Add new users in setUp:

```python
class DashboardRoleDetectionTest(TestCase):
    """Verify role detection in home dashboard for PM and executive."""

    def setUp(self):
        self.program = Program.objects.create(name="Test Program", status="active")
        self.program_b = Program.objects.create(name="Other Program", status="active")

        # PM user
        self.pm = User.objects.create_user(
            username="pm", password="testpass123", is_demo=False
        )
        UserProgramRole.objects.create(
            user=self.pm, program=self.program, role="program_manager"
        )

        # Executive user (only executive role, no client-access roles)
        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123", is_demo=False
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program, role="executive"
        )

        # Staff user
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_demo=False
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff"
        )

        # PM with two programs (for scoping test)
        self.pm_multi = User.objects.create_user(
            username="pm_multi", password="testpass123", is_demo=False
        )
        UserProgramRole.objects.create(
            user=self.pm_multi, program=self.program, role="program_manager"
        )
        # Note: pm_multi does NOT have a role in program_b

        # Create a client for context
        self.client_file = ClientFile.objects.create(
            first_name="Test", last_name="Client", status="active", is_demo=False,
        )
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="enrolled"
        )

    def test_pm_sees_program_summary(self):
        """PM gets is_pm=True in context."""
        self.client.login(username="pm", password="testpass123")
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["is_pm"])
        self.assertFalse(resp.context["is_executive"])

    def test_executive_sees_aggregate_metrics(self):
        """Executive gets is_executive=True in context."""
        self.client.login(username="exec", password="testpass123")
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["is_executive"])

    def test_executive_only_user_detected(self):
        """User with ONLY executive role (no staff/PM) is correctly identified."""
        self.client.login(username="exec", password="testpass123")
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["is_executive"])
        # Should still render (not crash or redirect)
        self.assertContains(resp, "Executive Overview")

    def test_staff_does_not_see_pm_section(self):
        """Staff user does not get PM or executive content."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context.get("is_pm", False))
        self.assertFalse(resp.context.get("is_executive", False))

    def test_pm_gets_only_assigned_programs(self):
        """PM only sees stats for programs they manage."""
        self.client.login(username="pm_multi", password="testpass123")
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)
        # PM should only see program stats for programs they have roles in
        if "pm_program_stats" in resp.context:
            pm_program_ids = {s["program"].pk for s in resp.context["pm_program_stats"]}
            self.assertIn(self.program.pk, pm_program_ids)
            self.assertNotIn(self.program_b.pk, pm_program_ids)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_home_dashboard.py::DashboardRoleDetectionTest -v`

Expected: FAIL — `is_pm` and `is_executive` not in context yet.

**Step 3: Add role detection to home view**

In `apps/clients/urls_home.py`:

Add import (line 10):
```python
from apps.auth_app.decorators import _get_user_highest_role, _get_user_highest_role_any
```

After `is_receptionist` assignment (line 48), add:
```python
    # Role detection for dashboard view selection
    # IMPORTANT: use _get_user_highest_role_any() — the original helper
    # excludes executives (returns None for executive-only users)
    highest_role_any = _get_user_highest_role_any(request.user)
    is_executive = highest_role_any == "executive"
    is_pm = highest_role_any == "program_manager" and not is_executive
```

In the context dict (lines 127-145), add three new keys:
```python
        "is_pm": is_pm,
        "is_executive": is_executive,
        "highest_role": highest_role_any,
```

**Step 4: Run tests**

Run: `pytest tests/test_home_dashboard.py::DashboardRoleDetectionTest::test_pm_sees_program_summary tests/test_home_dashboard.py::DashboardRoleDetectionTest::test_staff_does_not_see_pm_section -v`

Expected: `test_pm_sees_program_summary` PASS, `test_staff_does_not_see_pm_section` PASS.

**Step 5: Commit**

```bash
git add apps/clients/urls_home.py tests/test_home_dashboard.py
git commit -m "feat: add role detection to home dashboard (DASH-ROLES1)"
```

---

### Task B2: Extract executive data helper and add PM helper

**Files:**
- Modify: `apps/clients/dashboard_views.py` (add helpers after `_get_feature_flags`, before `executive_dashboard`)

**Step 1: Add _get_executive_inline_data helper**

After `_get_feature_flags()` (line 506), add:

```python
def _get_executive_inline_data(user):
    """Fetch executive summary metrics for inline display on home page.

    Reuses the same batch queries as executive_dashboard() but returns
    a dict suitable for the home page partial template.
    """
    from apps.clients.models import ClientProgramEnrolment
    from apps.programs.models import Program, UserProgramRole
    from .views import get_client_queryset

    flags = _get_feature_flags()

    user_program_ids = list(
        UserProgramRole.objects.filter(
            user=user, status="active"
        ).values_list("program_id", flat=True)
    )
    programs = Program.objects.filter(pk__in=user_program_ids, status="active")

    if not user_program_ids:
        return {"program_stats": [], "total_active": 0, "flags": flags}

    base_clients = get_client_queryset(user)
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())

    all_enrolled_ids = set(
        ClientProgramEnrolment.objects.filter(
            program__in=programs, status="enrolled"
        ).values_list("client_file_id", flat=True)
    )
    all_active_ids = set(
        base_clients.filter(
            pk__in=all_enrolled_ids, status="active"
        ).values_list("pk", flat=True)
    )
    all_client_ids = set(
        base_clients.filter(pk__in=all_enrolled_ids).values_list("pk", flat=True)
    )
    filtered_program_ids = list(programs.values_list("pk", flat=True))
    base_client_ids = set(base_clients.values_list("pk", flat=True))

    total_active = len(all_active_ids)
    without_notes = _count_without_notes(all_active_ids, filtered_program_ids, month_start)
    overdue_followups = _count_overdue_followups(all_client_ids, now.date())

    show_alerts = flags.get("alerts", False)
    active_alerts = _count_active_alerts(all_client_ids) if show_alerts else None
    show_events = flags.get("events", False)
    show_portal = flags.get("portal_journal", False) or flags.get("portal_messaging", False)

    enrolment_stats = _batch_enrolment_stats(filtered_program_ids, base_client_ids, month_start)
    notes_week_map = _batch_notes_this_week(filtered_program_ids, week_start)
    engagement_map = _batch_engagement_quality(filtered_program_ids, month_start)
    goal_map = _batch_goal_completion(filtered_program_ids)
    suggestion_map = _batch_suggestion_counts(filtered_program_ids)

    program_stats = []
    for program in programs:
        pid = program.pk
        es = enrolment_stats.get(pid, {})
        stat = {
            "program": program,
            "active": es.get("active", 0),
            "new_this_month": es.get("new_this_month", 0),
            "notes_this_week": notes_week_map.get(pid, 0),
            "engagement_quality": engagement_map.get(pid),
            "goal_completion": goal_map.get(pid),
        }
        sugg = suggestion_map.get(pid, {})
        stat["suggestion_important"] = sugg.get("important", 0) + sugg.get("urgent", 0)
        program_stats.append(stat)

    total_suggestions_important = sum(
        s.get("important", 0) + s.get("urgent", 0) for s in suggestion_map.values()
    )

    return {
        "program_stats": program_stats,
        "total_active": total_active,
        "without_notes": without_notes,
        "overdue_followups": overdue_followups,
        "active_alerts": active_alerts,
        "show_alerts": show_alerts,
        "total_suggestions_important": total_suggestions_important,
        "flags": flags,
    }
```

**Step 2: Add _get_pm_summary_data helper**

After `_get_executive_inline_data`, add:

```python
def _get_pm_summary_data(user):
    """Fetch PM program health metrics for inline display on home page.

    Shows per-program stats for programs the PM manages: client counts,
    notes this week, overdue follow-ups, staff activity.
    """
    from apps.clients.models import ClientProgramEnrolment
    from apps.programs.models import Program, UserProgramRole
    from apps.notes.models import ProgressNote
    from .views import get_client_queryset

    user_program_ids = list(
        UserProgramRole.objects.filter(
            user=user, status="active"
        ).values_list("program_id", flat=True)
    )
    programs = Program.objects.filter(pk__in=user_program_ids, status="active")

    if not user_program_ids:
        return {"pm_program_stats": []}

    base_clients = get_client_queryset(user)
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    thirty_days_ago = now - timedelta(days=30)

    filtered_program_ids = list(programs.values_list("pk", flat=True))
    base_client_ids = set(base_clients.values_list("pk", flat=True))

    enrolment_stats = _batch_enrolment_stats(filtered_program_ids, base_client_ids, month_start)
    notes_week_map = _batch_notes_this_week(filtered_program_ids, week_start)

    # Overdue follow-ups per program
    overdue_by_program = {}
    overdue_notes = ProgressNote.objects.filter(
        author_program_id__in=filtered_program_ids,
        follow_up_date__lte=now.date(),
        follow_up_completed_at__isnull=True,
        status="default",
    ).values("author_program_id").annotate(count=models.Count("id"))
    for row in overdue_notes:
        overdue_by_program[row["author_program_id"]] = row["count"]

    # Staff activity: notes per staff member this month
    staff_activity = {}
    activity_qs = (
        ProgressNote.objects.filter(
            author_program_id__in=filtered_program_ids,
            created_at__gte=month_start,
            status="default",
        )
        .values("author_program_id", "author__display_name")
        .annotate(count=models.Count("id"))
        .order_by("author_program_id", "-count")
    )
    for row in activity_qs:
        pid = row["author_program_id"]
        if pid not in staff_activity:
            staff_activity[pid] = []
        staff_activity[pid].append({
            "name": row["author__display_name"] or "Unknown",
            "notes": row["count"],
        })

    # Clients with no recent note per program
    no_recent_by_program = {}
    for pid in filtered_program_ids:
        es = enrolment_stats.get(pid, {})
        active_ids = es.get("active_ids", set())
        if active_ids:
            with_recent = set(
                ProgressNote.objects.filter(
                    client_file_id__in=active_ids,
                    author_program_id=pid,
                    created_at__gte=thirty_days_ago,
                ).values_list("client_file_id", flat=True)
            )
            no_recent_by_program[pid] = len(active_ids - with_recent)
        else:
            no_recent_by_program[pid] = 0

    pm_program_stats = []
    for program in programs:
        pid = program.pk
        es = enrolment_stats.get(pid, {})
        pm_program_stats.append({
            "program": program,
            "active": es.get("active", 0),
            "new_this_month": es.get("new_this_month", 0),
            "notes_this_week": notes_week_map.get(pid, 0),
            "overdue_followups": overdue_by_program.get(pid, 0),
            "no_recent_notes": no_recent_by_program.get(pid, 0),
            "staff_activity": staff_activity.get(pid, []),
        })

    return {"pm_program_stats": pm_program_stats}
```

**Step 3: Commit**

```bash
git add apps/clients/dashboard_views.py
git commit -m "feat: add PM and executive inline data helpers (DASH-ROLES1)"
```

---

### Task B3: Wire helpers into home view

**Files:**
- Modify: `apps/clients/urls_home.py` (add conditional data fetching)

**Step 1: Add conditional data fetching after role detection**

After the `is_pm` / `is_executive` assignment, add:

```python
    # Role-specific dashboard data
    pm_data = {}
    exec_data = {}
    if is_executive and not is_receptionist:
        from apps.clients.dashboard_views import _get_executive_inline_data
        exec_data = _get_executive_inline_data(request.user)
    elif is_pm and not is_receptionist:
        from apps.clients.dashboard_views import _get_pm_summary_data
        pm_data = _get_pm_summary_data(request.user)
```

In the context dict, spread the role data:

```python
        **pm_data,
        **exec_data,
```

**Step 2: Run role detection tests**

Run: `pytest tests/test_home_dashboard.py -v`

Expected: All tests PASS.

**Step 3: Commit**

```bash
git add apps/clients/urls_home.py
git commit -m "feat: wire PM and executive data into home view (DASH-ROLES1)"
```

---

### Task B4: Create dashboard partial templates

**Files:**
- Create: `templates/clients/_dashboard_executive_summary.html`
- Create: `templates/clients/_dashboard_pm_summary.html`
- Modify: `templates/clients/home.html` (add conditional includes)

**Step 1: Create executive summary partial**

```html
{% load i18n %}
{# Executive inline summary — de-identified aggregate metrics #}
<section class="executive-summary" aria-label="{% trans 'Executive Overview' %}">
    <h2>{% trans "Executive Overview" %}</h2>
    <p class="section-subtitle">{% trans "De-identified program metrics — individual participant records are kept private." %}</p>

    <div class="stats-grid">
        <article class="stat-card">
            <div class="stat-value">{{ total_active }}</div>
            <div class="stat-label">{% trans "Active" %} {{ term.client_plural|default:"Participants" }}</div>
        </article>
        <article class="stat-card {% if without_notes > 0 %}stat-card-warning{% endif %}">
            <div class="stat-value">{{ without_notes }}</div>
            <div class="stat-label">{% trans "Without Notes This Month" %}</div>
        </article>
        <article class="stat-card {% if overdue_followups > 0 %}stat-card-warning{% endif %}">
            <div class="stat-value">{{ overdue_followups }}</div>
            <div class="stat-label">{% trans "Overdue Follow-ups" %}</div>
        </article>
        {% if show_alerts and active_alerts is not None %}
        <article class="stat-card {% if active_alerts > 0 %}stat-card-alert{% endif %}">
            <div class="stat-value">{{ active_alerts }}</div>
            <div class="stat-label">{% trans "Active Alerts" %}</div>
        </article>
        {% endif %}
    </div>

    {% if program_stats %}
    <h3>{{ term.program_plural|default:"Programs" }}</h3>
    <div class="program-cards">
        {% for stat in program_stats %}
        <article class="program-card">
            <header><strong>{{ stat.program.translated_name }}</strong></header>
            <dl class="program-metrics">
                <div>
                    <dt>{% trans "Active" %}</dt>
                    <dd>{{ stat.active }}</dd>
                </div>
                <div>
                    <dt>{% trans "New this month" %}</dt>
                    <dd>{{ stat.new_this_month }}</dd>
                </div>
                <div>
                    <dt>{% trans "Notes this week" %}</dt>
                    <dd>{{ stat.notes_this_week }}</dd>
                </div>
                {% if stat.engagement_quality is not None %}
                <div>
                    <dt>{% trans "Engagement quality" %}</dt>
                    <dd>{{ stat.engagement_quality }}%</dd>
                </div>
                {% endif %}
                {% if stat.goal_completion is not None %}
                <div>
                    <dt>{% trans "Goal completion" %}</dt>
                    <dd>{{ stat.goal_completion }}%</dd>
                </div>
                {% endif %}
            </dl>
        </article>
        {% endfor %}
    </div>
    {% endif %}

    <footer>
        <a href="{% url 'clients:executive_dashboard' %}" role="button" class="outline">{% trans "View full executive dashboard" %} &rarr;</a>
    </footer>
</section>
```

**Step 2: Create PM summary partial**

```html
{% load i18n %}
{# PM program health summary #}
<section class="pm-summary" aria-label="{% trans 'Program Health' %}">
    <h2>{% trans "Program Health" %}</h2>

    {% if pm_program_stats %}
    <div class="program-cards">
        {% for stat in pm_program_stats %}
        <article class="program-card">
            <header><strong>{{ stat.program.translated_name }}</strong></header>
            <dl class="program-metrics">
                <div>
                    <dt>{% trans "Active" %} {{ term.client_plural|default:"participants" }}</dt>
                    <dd>{{ stat.active }}</dd>
                </div>
                <div>
                    <dt>{% trans "New this month" %}</dt>
                    <dd>{{ stat.new_this_month }}</dd>
                </div>
                <div>
                    <dt>{% trans "Notes this week" %}</dt>
                    <dd>{{ stat.notes_this_week }}</dd>
                </div>
                <div class="{% if stat.overdue_followups > 0 %}metric-warning{% endif %}">
                    <dt>{% trans "Overdue follow-ups" %}</dt>
                    <dd>{{ stat.overdue_followups }}</dd>
                </div>
                <div class="{% if stat.no_recent_notes > 0 %}metric-warning{% endif %}">
                    <dt>{% trans "No notes in 30 days" %}</dt>
                    <dd>{{ stat.no_recent_notes }}</dd>
                </div>
            </dl>

            {% if stat.staff_activity %}
            <details>
                <summary>{% trans "Staff activity this month" %}</summary>
                <ul class="staff-activity-list">
                    {% for member in stat.staff_activity %}
                    <li>{{ member.name }} — {{ member.notes }} {% trans "notes" %}</li>
                    {% endfor %}
                </ul>
            </details>
            {% endif %}
        </article>
        {% endfor %}
    </div>
    {% else %}
    <p class="empty-message"><em>{% trans "No programs assigned." %}</em></p>
    {% endif %}
</section>
```

**Step 3: Update home.html with conditional blocks**

In `templates/clients/home.html`, replace the section from line 110 (`{% if not is_receptionist %}`) through line 201 (the closing `{% endif %}` of the Priority Items article) with:

```html
{% if is_executive %}
    {% include "clients/_dashboard_executive_summary.html" %}
{% elif is_pm %}
    {% include "clients/_dashboard_pm_summary.html" %}
    {# PM also sees the staff dashboard below for their own caseload #}
    {% if not is_receptionist %}
    <div class="stats-row">
        {# ... existing stats row content (lines 112-138) ... #}
    </div>
    {# ... existing Priority Items article (lines 142-201) ... #}
    {% endif %}
{% else %}
    {# Staff and receptionist views — existing code unchanged #}
    {% if not is_receptionist %}
    {# ... existing stats row + priority items ... #}
    {% endif %}
{% endif %}
```

The exact edit: wrap the existing `{% if not is_receptionist %}` stats-row block AND the Priority Items block inside the conditional.

**Step 4: Run tests**

Run: `pytest tests/test_home_dashboard.py -v`

Expected: All tests PASS including new role detection tests.

**Step 5: Commit**

```bash
git add templates/clients/_dashboard_executive_summary.html templates/clients/_dashboard_pm_summary.html templates/clients/home.html
git commit -m "feat: add role-based dashboard templates (DASH-ROLES1)"
```

---

### Task B5: Translations

**Step 1: Check for new translatable strings**

The new partials use several `{% trans %}` strings. Many are already in the executive_dashboard.html (e.g., "Active", "Notes this week", "Executive Overview"). Check which are new.

New strings likely needing translation:
- "Program Health"
- "No notes in 30 days"
- "Staff activity this month"
- "No programs assigned."
- "View full executive dashboard"
- "De-identified program metrics — individual participant records are kept private."
- "Overdue follow-ups" (may already exist)
- The blocktrans string from Task A6 (consent indicator)

**Step 2: Run translate_strings**

Run: `python manage.py translate_strings`

**Step 3: Fill in any empty French translations**

Check `locale/fr/LC_MESSAGES/django.po` for empty msgstr entries and fill them in.

**Step 4: Run translate_strings again to compile**

Run: `python manage.py translate_strings`

**Step 5: Commit**

```bash
git add locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo
git commit -m "i18n: add French translations for dashboard role and consent strings"
```

---

### Task B6: Final verification

**Step 1: Run all related tests**

Run: `pytest tests/test_home_dashboard.py tests/test_cross_program_security.py -v`

Expected: All tests PASS.

**Step 2: Run existing receptionist tests to verify no regression**

The 4 existing tests in `HomeDashboardPermissionsTest` must still pass.

**Step 3: Update TODO.md**

Mark both tasks as complete and move to Recently Done.

**Step 4: Final commit if needed**

---

## Task Dependencies

```
A1 (feature toggle) ─────────────────────┐
A2 (model field change) ──┐               │
A3 (forms/views update) ──┤               │
                          ├→ A4 (helpers + tests) → A5 (apply in view) → A6 (template) → A7 (verify)
B1 (role detection) ──────┤
B2 (data helpers) ────────┤
                          ├→ B3 (wire into view) → B4 (templates) → B5 (translations) → B6 (verify)
```

A1-A3 and B1-B2 can run in parallel. A4-A7 and B3-B6 are sequential within each track.

---

## Files Changed Summary

| File | Task | Change |
|------|------|--------|
| `apps/admin_settings/views.py` | A1 | Add feature toggle |
| `apps/clients/models.py` | A2 | Tri-state sharing field |
| `apps/clients/migrations/0023_*.py` | A2 | Schema + data migration |
| `apps/clients/forms.py` | A3 | Update form field |
| `apps/clients/views.py` | A3 | Update transfer view |
| `apps/programs/access.py` | A4 | Add consent filter helpers |
| `apps/notes/views.py` | A5 | Apply consent filter |
| `templates/notes/_tab_notes.html` | A6 | Consent indicator banner |
| `apps/clients/urls_home.py` | B1, B3 | Role detection + data wiring |
| `apps/clients/dashboard_views.py` | B2 | PM + executive helpers |
| `templates/clients/home.html` | B4 | Conditional role blocks |
| `templates/clients/_dashboard_pm_summary.html` | B4 | New PM partial |
| `templates/clients/_dashboard_executive_summary.html` | B4 | New executive partial |
| `tests/test_cross_program_security.py` | A4 | 8 consent tests |
| `tests/test_home_dashboard.py` | B1 | 5 role detection tests |
| `locale/fr/LC_MESSAGES/django.po` | A6, B5 | French translations |
