"""Tests for UX-PLAN discoverability features.

Covers:
- Editable-plans filter on the participant list (?editable=1)
- can_edit_plan flag is computed correctly per participant
- Empty-state message when editable filter has no results
- Disabled "Edit Plan" button visible to non-editors on plan view
- HtmxVaryMiddleware adds Vary: HX-Request to every response
"""
from cryptography.fernet import Fernet
from django.test import TestCase, Client, override_settings, RequestFactory
from django.urls import reverse

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.models import Program, UserProgramRole
from konote.middleware.htmx_vary import HtmxVaryMiddleware
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _make_client_in_program(first, last, program):
    """Helper: create a ClientFile enrolled in a program."""
    cf = ClientFile()
    cf.first_name = first
    cf.last_name = last
    cf.status = "active"
    cf.save()
    ClientProgramEnrolment.objects.create(client_file=cf, program=program, status="enrolled")
    return cf


# ── Section 1: Editable filter on the participant list ─────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EditableFilterTest(TestCase):
    """?editable=1 filters participants to only those the user can edit plans for."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        # Two programs — user is staff in prog_a (plan.edit=PROGRAM), PM in prog_b (plan.edit=DENY)
        self.prog_a = Program.objects.create(name="Housing Support", status="active")
        self.prog_b = Program.objects.create(name="Youth Services", status="active")

        self.user = User.objects.create_user(
            username="staffuser", password="testpass123", display_name="Staff User"
        )
        UserProgramRole.objects.create(
            user=self.user, program=self.prog_a, role="staff", status="active"
        )
        UserProgramRole.objects.create(
            user=self.user, program=self.prog_b, role="program_manager", status="active"
        )

        # editable_client is enrolled in prog_a (staff can edit plans there)
        self.editable_client = _make_client_in_program("Alice", "Smith", self.prog_a)
        # non_editable_client is enrolled only in prog_b (PM cannot edit plans there)
        self.non_editable_client = _make_client_in_program("Bob", "Jones", self.prog_b)

    def tearDown(self):
        enc_module._fernet = None

    def test_without_filter_both_clients_visible(self):
        """Without any filter, both participants appear in the list."""
        self.http.login(username="staffuser", password="testpass123")
        resp = self.http.get("/participants/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice")
        self.assertContains(resp, "Bob")

    def test_editable_filter_shows_only_editable_participants(self):
        """?editable=1 returns only participants whose plans the user can edit."""
        self.http.login(username="staffuser", password="testpass123")
        resp = self.http.get("/participants/?editable=1")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice")
        self.assertNotContains(resp, "Bob")

    def test_can_edit_plan_flag_set_for_editable_participant(self):
        """The page context includes can_edit_plan=True for editable participants."""
        self.http.login(username="staffuser", password="testpass123")
        resp = self.http.get("/participants/")
        self.assertEqual(resp.status_code, 200)
        page_items = resp.context["page"].object_list
        alice_item = next((i for i in page_items if "Alice" in i["name"]), None)
        self.assertIsNotNone(alice_item, "Alice should appear in the list")
        self.assertTrue(alice_item["can_edit_plan"], "Alice should have can_edit_plan=True")

    def test_can_edit_plan_false_for_pm_only_participant(self):
        """Participants in a program where the user is PM have can_edit_plan=False."""
        self.http.login(username="staffuser", password="testpass123")
        resp = self.http.get("/participants/")
        page_items = resp.context["page"].object_list
        bob_item = next((i for i in page_items if "Bob" in i["name"]), None)
        self.assertIsNotNone(bob_item, "Bob should appear in the list")
        self.assertFalse(bob_item["can_edit_plan"], "Bob should have can_edit_plan=False (user is PM, not staff)")

    def test_editable_filter_empty_state_message(self):
        """When ?editable=1 returns no results, the page shows the filter empty-state message."""
        # Create a user with only a PM role — no editable participants
        pm_only = User.objects.create_user(
            username="pmonly", password="testpass123", display_name="PM Only"
        )
        UserProgramRole.objects.create(
            user=pm_only, program=self.prog_a, role="program_manager", status="active"
        )
        self.http.login(username="pmonly", password="testpass123")
        resp = self.http.get("/participants/?editable=1")
        self.assertEqual(resp.status_code, 200)
        # Should show filter empty state, not "No X files yet"
        self.assertContains(resp, "Clear filters")
        self.assertNotContains(resp, "files yet")


# ── Section 2: Disabled Edit Plan button on plan view ──────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PlanViewDisabledButtonTest(TestCase):
    """Non-editors see a disabled Edit Plan button and a view-only notice."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        self.program = Program.objects.create(name="Housing Support", status="active")

        # Staff user (plan.edit=PROGRAM — can edit)
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", display_name="Staff"
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff", status="active"
        )

        # Program manager (plan.edit=DENY — cannot edit)
        self.pm = User.objects.create_user(
            username="pm", password="testpass123", display_name="PM"
        )
        UserProgramRole.objects.create(
            user=self.pm, program=self.program, role="program_manager", status="active"
        )

        self.client_file = _make_client_in_program("Jane", "Doe", self.program)

    def tearDown(self):
        enc_module._fernet = None

    def _plan_url(self):
        return reverse("plans:plan_view", args=[self.client_file.pk])

    def test_editor_does_not_see_disabled_button(self):
        """Staff user (can edit) sees no disabled button on the plan tab."""
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(self._plan_url())
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "aria-disabled")

    def test_non_editor_sees_disabled_button(self):
        """PM user (cannot edit) sees the aria-disabled Edit Plan button."""
        self.http.login(username="pm", password="testpass123")
        resp = self.http.get(self._plan_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'aria-disabled="true"')

    def test_non_editor_disabled_button_has_describedby(self):
        """The disabled button references an explanation span via aria-describedby."""
        self.http.login(username="pm", password="testpass123")
        resp = self.http.get(self._plan_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'aria-describedby="edit-plan-disabled-reason"')
        self.assertContains(resp, 'id="edit-plan-disabled-reason"')

    def test_non_editor_sees_view_only_notice(self):
        """The plan tab shows a 'View only' notice explaining the permission requirement."""
        self.http.login(username="pm", password="testpass123")
        resp = self.http.get(self._plan_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "View only")


# ── Section 3: HtmxVaryMiddleware ─────────────────────────────────


class HtmxVaryMiddlewareTest(TestCase):
    """HtmxVaryMiddleware adds Vary: HX-Request to every response."""

    def _get_response_with_header(self, vary_value=None):
        """Return a mock response with an optional existing Vary header."""
        from django.http import HttpResponse
        response = HttpResponse("ok")
        if vary_value:
            response["Vary"] = vary_value
        return response

    def test_vary_header_added_to_plain_response(self):
        """Middleware adds HX-Request to the Vary header on a plain response."""
        factory = RequestFactory()
        request = factory.get("/")

        def get_response(req):
            return self._get_response_with_header()

        middleware = HtmxVaryMiddleware(get_response)
        response = middleware(request)
        self.assertIn("HX-Request", response.get("Vary", ""))

    def test_vary_header_preserved_alongside_existing_value(self):
        """Middleware does not clobber an existing Vary header — it appends."""
        factory = RequestFactory()
        request = factory.get("/")

        def get_response(req):
            return self._get_response_with_header(vary_value="Cookie")

        middleware = HtmxVaryMiddleware(get_response)
        response = middleware(request)
        vary = response.get("Vary", "")
        self.assertIn("HX-Request", vary)
        self.assertIn("Cookie", vary)

    def test_vary_header_present_on_htmx_request(self):
        """Middleware adds the header on HTMX requests too (not just plain requests)."""
        factory = RequestFactory()
        request = factory.get("/", HTTP_HX_REQUEST="true")

        def get_response(req):
            return self._get_response_with_header()

        middleware = HtmxVaryMiddleware(get_response)
        response = middleware(request)
        self.assertIn("HX-Request", response.get("Vary", ""))
