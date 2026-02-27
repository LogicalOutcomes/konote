"""Tests for suggestion theme CRUD and linking (UX-INSIGHT6 Phase 1)."""
from datetime import datetime, timezone as tz
from cryptography.fernet import Fernet

from django.contrib.auth import get_user_model
from django.test import Client as TestClient, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

import konote.encryption as enc_module
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import (
    THEME_PRIORITY_RANK, ProgressNote, SuggestionLink, SuggestionTheme,
    deduplicate_themes, recalculate_theme_priority,
)
from apps.programs.models import Program, UserProgramRole

User = get_user_model()

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SuggestionThemePermissionTests(TestCase):
    """Test role-based access control for suggestion theme views."""

    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program")
        self.test_client = TestClient()

        # PM user
        self.pm = User.objects.create_user(username="pm", password="pass")
        UserProgramRole.objects.create(
            user=self.pm, program=self.program,
            role="program_manager", status="active",
        )

        # Staff user
        self.staff = User.objects.create_user(username="staff", password="pass")
        UserProgramRole.objects.create(
            user=self.staff, program=self.program,
            role="staff", status="active",
        )

        # Receptionist user
        self.recep = User.objects.create_user(username="recep", password="pass")
        UserProgramRole.objects.create(
            user=self.recep, program=self.program,
            role="receptionist", status="active",
        )

        # Admin user
        self.admin = User.objects.create_user(username="admin", password="pass")
        self.admin.is_admin = True
        self.admin.save()
        UserProgramRole.objects.create(
            user=self.admin, program=self.program,
            role="staff", status="active",
        )

        # Create a theme for testing
        self.theme = SuggestionTheme.objects.create(
            program=self.program, name="Evening hours",
            created_by=self.pm,
        )

    def test_pm_can_view_list(self):
        self.test_client.login(username="pm", password="pass")
        response = self.test_client.get(reverse("suggestion_themes:theme_list"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_view_list(self):
        self.test_client.login(username="staff", password="pass")
        response = self.test_client.get(reverse("suggestion_themes:theme_list"))
        self.assertEqual(response.status_code, 200)

    def test_receptionist_cannot_view_list(self):
        self.test_client.login(username="recep", password="pass")
        response = self.test_client.get(reverse("suggestion_themes:theme_list"))
        self.assertEqual(response.status_code, 403)

    def test_pm_can_create_theme(self):
        self.test_client.login(username="pm", password="pass")
        response = self.test_client.post(
            reverse("suggestion_themes:theme_create"),
            {"name": "Childcare support", "program": self.program.pk, "status": "open"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SuggestionTheme.objects.filter(name="Childcare support").exists())

    def test_staff_cannot_create_theme(self):
        self.test_client.login(username="staff", password="pass")
        response = self.test_client.post(
            reverse("suggestion_themes:theme_create"),
            {"name": "Staff theme", "program": self.program.pk, "status": "open"},
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_theme(self):
        self.test_client.login(username="admin", password="pass")
        response = self.test_client.post(
            reverse("suggestion_themes:theme_create"),
            {"name": "Admin theme", "program": self.program.pk, "status": "open"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SuggestionTheme.objects.filter(name="Admin theme").exists())

    def test_pm_can_view_detail(self):
        self.test_client.login(username="pm", password="pass")
        response = self.test_client.get(
            reverse("suggestion_themes:theme_detail", kwargs={"pk": self.theme.pk}),
        )
        self.assertEqual(response.status_code, 200)

    def test_cross_program_pm_cannot_view_detail(self):
        other_program = Program.objects.create(name="Other Program")
        other_pm = User.objects.create_user(username="other_pm", password="pass")
        UserProgramRole.objects.create(
            user=other_pm, program=other_program,
            role="program_manager", status="active",
        )
        self.test_client.login(username="other_pm", password="pass")
        response = self.test_client.get(
            reverse("suggestion_themes:theme_detail", kwargs={"pk": self.theme.pk}),
        )
        self.assertEqual(response.status_code, 403)

    def test_pm_can_edit_theme(self):
        self.test_client.login(username="pm", password="pass")
        response = self.test_client.post(
            reverse("suggestion_themes:theme_edit", kwargs={"pk": self.theme.pk}),
            {"name": "Updated name", "program": self.program.pk, "status": "open"},
        )
        self.assertEqual(response.status_code, 302)
        self.theme.refresh_from_db()
        self.assertEqual(self.theme.name, "Updated name")

    def test_staff_cannot_edit_theme(self):
        self.test_client.login(username="staff", password="pass")
        response = self.test_client.post(
            reverse("suggestion_themes:theme_edit", kwargs={"pk": self.theme.pk}),
            {"name": "Should fail", "program": self.program.pk, "status": "open"},
        )
        self.assertEqual(response.status_code, 403)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SuggestionThemeLinkingTests(TestCase):
    """Test linking and unlinking suggestions to themes."""

    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program")
        self.pm = User.objects.create_user(username="pm", password="pass")
        UserProgramRole.objects.create(
            user=self.pm, program=self.program,
            role="program_manager", status="active",
        )
        self.test_client = TestClient()
        self.test_client.login(username="pm", password="pass")

        self.theme = SuggestionTheme.objects.create(
            program=self.program, name="Evening hours",
            created_by=self.pm,
        )

        # Create some notes with suggestions
        self.client_file = ClientFile.objects.create(record_id="LINK-001")
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="active",
        )
        self.note1 = ProgressNote.objects.create(
            client_file=self.client_file, author=self.pm,
            author_program=self.program, note_type="quick",
            suggestion_priority="noted",
        )
        self.note2 = ProgressNote.objects.create(
            client_file=self.client_file, author=self.pm,
            author_program=self.program, note_type="quick",
            suggestion_priority="urgent",
        )

    def test_link_creates_record(self):
        response = self.test_client.post(
            reverse("suggestion_themes:theme_detail", kwargs={"pk": self.theme.pk}),
            {"action": "link_notes", "note_ids": [self.note1.pk]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            SuggestionLink.objects.filter(theme=self.theme, progress_note=self.note1).exists()
        )

    def test_duplicate_link_does_not_error(self):
        SuggestionLink.objects.create(
            theme=self.theme, progress_note=self.note1, linked_by=self.pm,
        )
        response = self.test_client.post(
            reverse("suggestion_themes:theme_detail", kwargs={"pk": self.theme.pk}),
            {"action": "link_notes", "note_ids": [self.note1.pk]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            SuggestionLink.objects.filter(theme=self.theme, progress_note=self.note1).count(),
            1,
        )

    def test_unlink_removes_record(self):
        link = SuggestionLink.objects.create(
            theme=self.theme, progress_note=self.note1, linked_by=self.pm,
        )
        response = self.test_client.post(
            reverse("suggestion_themes:theme_detail", kwargs={"pk": self.theme.pk}),
            {"action": "unlink", "link_id": link.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SuggestionLink.objects.filter(pk=link.pk).exists())

    def test_priority_updates_after_link(self):
        self.test_client.post(
            reverse("suggestion_themes:theme_detail", kwargs={"pk": self.theme.pk}),
            {"action": "link_notes", "note_ids": [self.note2.pk]},
        )
        self.theme.refresh_from_db()
        self.assertEqual(self.theme.priority, "urgent")

    def test_priority_recalculates_after_unlink(self):
        SuggestionLink.objects.create(
            theme=self.theme, progress_note=self.note1, linked_by=self.pm,
        )
        link2 = SuggestionLink.objects.create(
            theme=self.theme, progress_note=self.note2, linked_by=self.pm,
        )
        recalculate_theme_priority(self.theme)
        self.theme.refresh_from_db()
        self.assertEqual(self.theme.priority, "urgent")

        # Unlink the urgent note
        link2.delete()  # post_delete signal fires
        self.theme.refresh_from_db()
        self.assertEqual(self.theme.priority, "noted")

    def test_staff_cannot_link(self):
        staff = User.objects.create_user(username="staff", password="pass")
        UserProgramRole.objects.create(
            user=staff, program=self.program, role="staff", status="active",
        )
        staff_client = TestClient()
        staff_client.login(username="staff", password="pass")
        response = staff_client.post(
            reverse("suggestion_themes:theme_detail", kwargs={"pk": self.theme.pk}),
            {"action": "link_notes", "note_ids": [self.note1.pk]},
        )
        # Staff can view detail (200) but POST actions won't execute (no can_manage)
        # The view redirects without creating a link
        self.assertFalse(
            SuggestionLink.objects.filter(theme=self.theme, progress_note=self.note1).exists()
        )


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SuggestionThemeStatusTests(TestCase):
    """Test status transitions via action buttons."""

    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program")
        self.pm = User.objects.create_user(username="pm", password="pass")
        UserProgramRole.objects.create(
            user=self.pm, program=self.program,
            role="program_manager", status="active",
        )
        self.test_client = TestClient()
        self.test_client.login(username="pm", password="pass")

        self.theme = SuggestionTheme.objects.create(
            program=self.program, name="Evening hours",
            created_by=self.pm, status="open",
        )

    def test_open_to_in_progress(self):
        response = self.test_client.post(
            reverse("suggestion_themes:theme_detail", kwargs={"pk": self.theme.pk}),
            {"action": "status_update", "new_status": "in_progress"},
        )
        self.assertEqual(response.status_code, 302)
        self.theme.refresh_from_db()
        self.assertEqual(self.theme.status, "in_progress")

    def test_in_progress_to_addressed(self):
        self.theme.status = "in_progress"
        self.theme.save()
        response = self.test_client.post(
            reverse("suggestion_themes:theme_detail", kwargs={"pk": self.theme.pk}),
            {
                "action": "status_update",
                "new_status": "addressed",
                "addressed_note": "Added evening sessions on Tuesdays.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.theme.refresh_from_db()
        self.assertEqual(self.theme.status, "addressed")
        self.assertEqual(self.theme.addressed_note, "Added evening sessions on Tuesdays.")

    def test_addressed_to_reopen(self):
        self.theme.status = "addressed"
        self.theme.save()
        response = self.test_client.post(
            reverse("suggestion_themes:theme_detail", kwargs={"pk": self.theme.pk}),
            {"action": "status_update", "new_status": "open"},
        )
        self.assertEqual(response.status_code, 302)
        self.theme.refresh_from_db()
        self.assertEqual(self.theme.status, "open")

    def test_invalid_status_rejected(self):
        response = self.test_client.post(
            reverse("suggestion_themes:theme_detail", kwargs={"pk": self.theme.pk}),
            {"action": "status_update", "new_status": "invalid"},
        )
        self.assertEqual(response.status_code, 302)
        self.theme.refresh_from_db()
        self.assertEqual(self.theme.status, "open")  # Unchanged


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SuggestionThemeFormTests(TestCase):
    """Test SuggestionThemeForm validation."""

    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program")

    def test_valid_form(self):
        from apps.notes.forms import SuggestionThemeForm
        form = SuggestionThemeForm(data={
            "name": "Evening availability",
            "program": self.program.pk,
            "description": "Participants want evening sessions",
            "status": "open",
            "addressed_note": "",
        })
        self.assertTrue(form.is_valid())

    def test_blank_name_invalid(self):
        from apps.notes.forms import SuggestionThemeForm
        form = SuggestionThemeForm(data={
            "name": "",
            "program": self.program.pk,
            "status": "open",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SuggestionThemeManagerTests(TestCase):
    """Test the custom manager's .active() queryset."""

    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program")
        self.user = User.objects.create_user(username="pm", password="pass")

        SuggestionTheme.objects.create(
            program=self.program, name="Open theme",
            created_by=self.user, status="open",
        )
        SuggestionTheme.objects.create(
            program=self.program, name="In progress theme",
            created_by=self.user, status="in_progress",
        )
        SuggestionTheme.objects.create(
            program=self.program, name="Addressed theme",
            created_by=self.user, status="addressed",
        )
        SuggestionTheme.objects.create(
            program=self.program, name="Wont do theme",
            created_by=self.user, status="wont_do",
        )

    def test_active_returns_open_and_in_progress(self):
        active = SuggestionTheme.objects.active()
        self.assertEqual(active.count(), 2)
        names = set(active.values_list("name", flat=True))
        self.assertEqual(names, {"Open theme", "In progress theme"})


class DeduplicateThemesUnitTest(SimpleTestCase):
    """Test deduplicate_themes() helper without database."""

    def _make_theme(self, pk, name, program_id=1, link_count=0, priority="noted"):
        return {
            "pk": pk,
            "name": name,
            "status": "open",
            "priority": priority,
            "program_id": program_id,
            "updated_at": datetime(2026, 1, 1, tzinfo=tz.utc),
            "link_count": link_count,
        }

    def test_no_duplicates_unchanged(self):
        themes = [
            self._make_theme(1, "Alpha"),
            self._make_theme(2, "Beta"),
        ]
        result = deduplicate_themes(themes)
        self.assertEqual(len(result), 2)

    def test_same_name_merged(self):
        themes = [
            self._make_theme(1, "Recipe variety", link_count=2, priority="important"),
            self._make_theme(2, "Recipe variety", link_count=0, priority="noted"),
        ]
        result = deduplicate_themes(themes)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["link_count"], 2)
        self.assertEqual(result[0]["priority"], "important")

    def test_case_insensitive_merge(self):
        themes = [
            self._make_theme(1, "Take-home portions"),
            self._make_theme(2, "take-home portions"),
        ]
        result = deduplicate_themes(themes)
        self.assertEqual(len(result), 1)

    def test_whitespace_normalised(self):
        themes = [
            self._make_theme(1, "  Recipe variety  ", link_count=1),
            self._make_theme(2, "Recipe variety", link_count=1),
        ]
        result = deduplicate_themes(themes)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["link_count"], 2)

    def test_different_programs_not_merged(self):
        themes = [
            self._make_theme(1, "Same name", program_id=1),
            self._make_theme(2, "Same name", program_id=2),
        ]
        result = deduplicate_themes(themes)
        self.assertEqual(len(result), 2)

    def test_highest_priority_kept(self):
        themes = [
            self._make_theme(1, "Theme", priority="noted"),
            self._make_theme(2, "Theme", priority="urgent"),
        ]
        result = deduplicate_themes(themes)
        self.assertEqual(result[0]["priority"], "urgent")

    def test_empty_list(self):
        self.assertEqual(deduplicate_themes([]), [])


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SuggestionThemeFormDuplicateTests(TestCase):
    """Test SuggestionThemeForm rejects duplicate names."""

    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program")
        SuggestionTheme.objects.create(
            program=self.program, name="Evening hours", status="open",
        )

    def test_duplicate_name_rejected(self):
        from apps.notes.forms import SuggestionThemeForm
        form = SuggestionThemeForm(data={
            "name": "Evening hours",
            "program": self.program.pk,
            "status": "open",
            "addressed_note": "",
        })
        self.assertFalse(form.is_valid())

    def test_duplicate_name_case_insensitive(self):
        from apps.notes.forms import SuggestionThemeForm
        form = SuggestionThemeForm(data={
            "name": "evening HOURS",
            "program": self.program.pk,
            "status": "open",
            "addressed_note": "",
        })
        self.assertFalse(form.is_valid())

    def test_whitespace_normalised_before_check(self):
        from apps.notes.forms import SuggestionThemeForm
        form = SuggestionThemeForm(data={
            "name": "  Evening   hours  ",
            "program": self.program.pk,
            "status": "open",
            "addressed_note": "",
        })
        self.assertFalse(form.is_valid())

    def test_editing_same_theme_allowed(self):
        """Editing a theme should not flag itself as a duplicate."""
        from apps.notes.forms import SuggestionThemeForm
        theme = SuggestionTheme.objects.get(name="Evening hours")
        form = SuggestionThemeForm(
            data={
                "name": "Evening hours",
                "program": self.program.pk,
                "status": "in_progress",
                "addressed_note": "",
            },
            instance=theme,
        )
        self.assertTrue(form.is_valid())

    def test_different_program_allowed(self):
        from apps.notes.forms import SuggestionThemeForm
        other_program = Program.objects.create(name="Other Program")
        form = SuggestionThemeForm(data={
            "name": "Evening hours",
            "program": other_program.pk,
            "status": "open",
            "addressed_note": "",
        })
        self.assertTrue(form.is_valid())
