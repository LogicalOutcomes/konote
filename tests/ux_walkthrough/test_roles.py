"""UX walkthrough tests — one test class per user role.

Run all roles:
    pytest tests/ux_walkthrough/ -v

Run a single role:
    pytest tests/ux_walkthrough/test_roles.py::StaffWalkthroughTest -v
"""
from django.test import override_settings
from django.utils import timezone

from .base import TEST_KEY, UxWalkthroughBase


# =====================================================================
# Front Desk (Receptionist)
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ReceptionistWalkthroughTest(UxWalkthroughBase):
    """Walk through every workflow available to a front desk user."""

    def test_walkthrough(self):
        self.client.login(username="frontdesk", password="testpass123")
        role = "Front Desk"
        cid = self.client_a.pk

        # 1. Home page
        self.visit(role, "Home page", "/")

        # 2. Client list
        self.visit(role, "Client list", "/clients/")

        # 3. Search
        self.visit(role, "Search for client", f"/clients/search/?q=Jane")

        # 4. Client detail — should NOT see note/plan edit buttons
        self.visit(
            role,
            "Client detail",
            f"/clients/{cid}/",
            role_should_not_see=["Create Note", "Quick Note", "Edit Plan"],
        )

        # 5. Custom fields display (HTMX)
        self.visit_htmx(role, "Custom fields display", f"/clients/{cid}/custom-fields/display/")

        # 6. Custom fields edit (HTMX) — editable fields only
        self.visit_htmx(role, "Custom fields edit", f"/clients/{cid}/custom-fields/edit/")

        # 7. Consent display (HTMX)
        self.visit_htmx(role, "Consent display", f"/clients/{cid}/consent/display/")

        # 8. BLOCKED: create client
        self.visit_forbidden(role, "Create client (403)", "/clients/create/")

        # 9. BLOCKED: notes
        self.visit_forbidden(role, "Notes list (403)", f"/notes/client/{cid}/")

        # 10. BLOCKED: plan editing
        self.visit_forbidden(
            role, "Plan section create (403)", f"/plans/client/{cid}/sections/create/"
        )

        # 11. Programs list (accessible to all)
        self.visit(role, "Programs list", "/programs/")

    def test_french_walkthrough(self):
        """Repeat key pages in French to verify i18n."""
        self.client.login(username="frontdesk", password="testpass123")
        role = "Front Desk (FR)"

        # Switch to French
        self.client.post("/i18n/switch/", {"language": "fr"})
        self.client.cookies["django_language"] = "fr"

        # Home page in French
        self.visit(role, "Home page (FR)", "/", expected_lang="fr")

        # Client detail in French
        self.visit(
            role,
            "Client detail (FR)",
            f"/clients/{self.client_a.pk}/",
            expected_lang="fr",
        )

        # Programs list in French
        self.visit(role, "Programs list (FR)", "/programs/", expected_lang="fr")

        # Reset to English
        self.client.post("/i18n/switch/", {"language": "en"})


# =====================================================================
# Direct Service (Staff)
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class StaffWalkthroughTest(UxWalkthroughBase):
    """Walk through every workflow available to a direct service worker."""

    def test_walkthrough(self):
        self.client.login(username="staff", password="testpass123")
        role = "Direct Service"
        cid = self.client_a.pk

        # 1. Home page
        self.visit(role, "Home page", "/")

        # 2. Client list
        self.visit(role, "Client list", "/clients/")

        # 3. Create client form (GET)
        self.visit(role, "Create client form", "/clients/create/")

        # 4. Submit create client
        self.visit_and_follow(
            role,
            "Create client submit",
            "/clients/create/",
            data={
                "first_name": "New",
                "last_name": "Client",
                "middle_name": "",
                "birth_date": "",
                "record_id": "",
                "status": "active",
                "programs": [self.program_a.pk],
            },
            expected_redirect="/clients/",
        )

        # 5. Client detail — should see Create Note, NOT Edit Plan
        self.visit(
            role,
            "Client detail",
            f"/clients/{cid}/",
            role_should_see=["Note"],
            role_should_not_see=["Edit Plan", "Add Section"],
        )

        # 6. Edit client form (GET)
        self.visit(role, "Edit client form", f"/clients/{cid}/edit/")

        # 7. Submit edit client
        self.visit_and_follow(
            role,
            "Edit client submit",
            f"/clients/{cid}/edit/",
            data={
                "first_name": "Jane",
                "last_name": "Doe-Updated",
                "middle_name": "",
                "birth_date": "",
                "record_id": "",
                "status": "active",
                "programs": [self.program_a.pk],
            },
            expected_redirect=f"/clients/{cid}/",
        )

        # 8. Consent edit (HTMX partial)
        self.visit_htmx(role, "Consent edit form", f"/clients/{cid}/consent/edit/")

        # 9. Submit consent
        today = timezone.now().strftime("%Y-%m-%d")
        self.visit_and_follow(
            role,
            "Consent submit",
            f"/clients/{cid}/consent/",
            data={
                "consent_type": "written",
                "consent_date": today,
                "notes": "Consent obtained in person.",
            },
        )

        # 10. Custom fields edit (HTMX)
        self.visit_htmx(role, "Custom fields edit", f"/clients/{cid}/custom-fields/edit/")

        # 11. Quick note form (GET)
        self.visit(role, "Quick note form", f"/notes/client/{cid}/quick/")

        # 12. Submit quick note
        self.visit_and_follow(
            role,
            "Quick note submit",
            f"/notes/client/{cid}/quick/",
            data={
                "interaction_type": "session",
                "notes_text": "Test quick note from UX walkthrough.",
                "consent_confirmed": "on",
            },
            expected_redirect=f"/notes/client/{cid}/",
        )

        # 13. Full note form (GET)
        self.visit(role, "Full note form", f"/notes/client/{cid}/new/")

        # 14. Notes timeline
        self.visit(role, "Notes timeline", f"/notes/client/{cid}/")

        # 15. Note detail (HTMX)
        self.visit_htmx(role, "Note detail", f"/notes/{self.note.pk}/")

        # 16. Plan view (read-only)
        self.visit(
            role,
            "Plan view (read-only)",
            f"/plans/client/{cid}/",
            role_should_not_see=["Add Section", "Add Target"],
        )

        # 17. BLOCKED: plan editing
        self.visit_forbidden(
            role, "Section create (403)", f"/plans/client/{cid}/sections/create/"
        )

        # 18. Events tab
        self.visit(role, "Events tab", f"/events/client/{cid}/")

        # 19. Event create form
        self.visit(role, "Event create form", f"/events/client/{cid}/create/")

        # 20. Alert create form
        self.visit(role, "Alert create form", f"/events/client/{cid}/alerts/create/")

        # 21. Client analysis
        self.visit(role, "Client analysis", f"/reports/client/{cid}/analysis/")

        # 22. Programs list
        self.visit(role, "Programs list", "/programs/")

    def test_form_validation(self):
        """Submit empty quick note — verify error messages display."""
        self.client.login(username="staff", password="testpass123")
        role = "Direct Service"
        cid = self.client_a.pk

        response = self.client.post(
            f"/notes/client/{cid}/quick/",
            {"interaction_type": "", "notes_text": "", "consent_confirmed": ""},
        )
        from .checker import UxChecker

        checker = UxChecker(
            response,
            f"/notes/client/{cid}/quick/",
            role,
            "Form validation — empty quick note",
        )
        checker.check_form_errors()
        checker.run_all_checks()
        self.report.record_step(
            role,
            "Form validation errors",
            f"/notes/client/{cid}/quick/",
            response.status_code,
            checker.issues,
        )


# =====================================================================
# Program Manager
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ManagerWalkthroughTest(UxWalkthroughBase):
    """Walk through workflows available to a program manager."""

    def test_walkthrough(self):
        self.client.login(username="manager", password="testpass123")
        role = "Program Manager"
        cid = self.client_a.pk

        # Core pages (same as staff)
        self.visit(role, "Home page", "/")
        self.visit(role, "Client list", "/clients/")
        self.visit(role, "Client detail", f"/clients/{cid}/")
        self.visit(role, "Notes timeline", f"/notes/client/{cid}/")
        self.visit(role, "Quick note form", f"/notes/client/{cid}/quick/")
        self.visit(role, "Full note form", f"/notes/client/{cid}/new/")

        # Plan view — manager should see edit buttons
        self.visit(
            role,
            "Plan view (editable)",
            f"/plans/client/{cid}/",
            role_should_see=["Add Section"],
        )

        # Section create form (GET)
        self.visit(role, "Section create form", f"/plans/client/{cid}/sections/create/")

        # Submit section create
        self.visit_and_follow(
            role,
            "Section create submit",
            f"/plans/client/{cid}/sections/create/",
            data={
                "name": "New Section from Walkthrough",
                "program": self.program_a.pk,
                "sort_order": 2,
            },
            expected_redirect=f"/plans/client/{cid}/",
        )

        # Target create form
        self.visit(
            role,
            "Target create form",
            f"/plans/sections/{self.plan_section.pk}/targets/create/",
        )

        # Submit target create
        self.visit_and_follow(
            role,
            "Target create submit",
            f"/plans/sections/{self.plan_section.pk}/targets/create/",
            data={
                "name": "New Target from Walkthrough",
                "description": "Test target",
            },
            expected_redirect=f"/plans/client/{cid}/",
        )

        # Target metrics (HTMX)
        self.visit_htmx(
            role, "Target metrics", f"/plans/targets/{self.plan_target.pk}/metrics/"
        )

        # Section status (HTMX)
        self.visit_htmx(
            role, "Section status", f"/plans/sections/{self.plan_section.pk}/status/"
        )

        # Target status (HTMX)
        self.visit_htmx(
            role, "Target status", f"/plans/targets/{self.plan_target.pk}/status/"
        )

        # Target history (HTMX)
        self.visit_htmx(
            role, "Target history", f"/plans/targets/{self.plan_target.pk}/history/"
        )

        # Export forms
        self.visit(role, "Metrics export form", "/reports/export/")
        self.visit(role, "Funder report form", "/reports/funder-report/")

        # Events
        self.visit(role, "Events tab", f"/events/client/{cid}/")
        self.visit(role, "Event create form", f"/events/client/{cid}/create/")

        # Client analysis
        self.visit(role, "Client analysis", f"/reports/client/{cid}/analysis/")


# =====================================================================
# Executive
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ExecutiveWalkthroughTest(UxWalkthroughBase):
    """Walk through the executive dashboard experience."""

    def test_walkthrough(self):
        self.client.login(username="executive", password="testpass123")
        role = "Executive"

        # 1. Executive dashboard
        self.visit(role, "Executive dashboard", "/clients/executive/")

        # 2. Client list → should redirect to exec dashboard
        self.visit_redirect(role, "Client list redirect", "/clients/")

        # 3. Client detail → should redirect to exec dashboard
        self.visit_redirect(
            role, "Client detail redirect", f"/clients/{self.client_a.pk}/"
        )

        # 4. Programs list (should be accessible)
        self.visit(role, "Programs list", "/programs/")

        # 5. Notes → should redirect
        self.visit_redirect(
            role, "Notes redirect", f"/notes/client/{self.client_a.pk}/"
        )


# =====================================================================
# Admin (no program role)
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminWalkthroughTest(UxWalkthroughBase):
    """Walk through all admin pages."""

    def test_walkthrough(self):
        self.client.login(username="admin", password="testpass123")
        role = "Admin"

        # Settings
        self.visit(role, "Admin settings dashboard", "/admin/settings/")
        self.visit(role, "Terminology settings", "/admin/settings/terminology/")
        self.visit(role, "Feature toggles", "/admin/settings/features/")
        self.visit(role, "Instance settings", "/admin/settings/instance/")

        # Metrics library
        self.visit(role, "Metrics library", "/plans/admin/metrics/")
        self.visit(role, "Create metric form", "/plans/admin/metrics/create/")

        # Programs
        self.visit(role, "Programs list", "/programs/")
        self.visit(role, "Create program form", "/programs/create/")
        self.visit(
            role, "Program detail", f"/programs/{self.program_a.pk}/"
        )

        # Users
        self.visit(role, "User list", "/admin/users/")
        self.visit(role, "Create user form", "/admin/users/new/")

        # Invites
        self.visit(role, "Invite list", "/auth/invites/")
        self.visit(role, "Create invite form", "/auth/invites/new/")

        # Audit
        self.visit(role, "Audit log", "/admin/audit/")

        # Registration
        self.visit(role, "Registration links", "/admin/registration/")
        self.visit(role, "Create registration link", "/admin/registration/create/")

        # Custom fields
        self.visit(role, "Custom field admin", "/clients/admin/fields/")
        self.visit(
            role, "Create field group", "/clients/admin/fields/groups/create/"
        )
        self.visit(role, "Create field definition", "/clients/admin/fields/create/")

        # Event types
        self.visit(role, "Event types list", "/events/admin/types/")
        self.visit(role, "Create event type", "/events/admin/types/create/")

        # Note templates
        self.visit(role, "Note templates", "/admin/settings/note-templates/")

        # Reports
        self.visit(role, "Export links management", "/reports/export-links/")

        # Diagnose
        self.visit(role, "Diagnose charts", "/admin/settings/diagnose-charts/")

        # Submissions
        self.visit(role, "Pending submissions", "/admin/submissions/")

    def test_admin_blocked_from_client_data(self):
        """Admin WITHOUT program role cannot access client data."""
        self.client.login(username="admin", password="testpass123")
        role = "Admin"

        self.visit_forbidden(
            role,
            "Client detail without program role (403)",
            f"/clients/{self.client_a.pk}/",
        )

    def test_non_admin_blocked_from_admin_pages(self):
        """Non-admin user gets 403 on admin pages."""
        self.client.login(username="staff", password="testpass123")
        role = "Non-admin spot check"

        self.visit_forbidden(
            role, "Admin settings (403)", "/admin/settings/"
        )
        self.visit_forbidden(
            role, "User list (403)", "/admin/users/"
        )


# =====================================================================
# Admin + Program Manager (dual role)
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminPMWalkthroughTest(UxWalkthroughBase):
    """Admin who also has a program manager role — can do everything."""

    def test_walkthrough(self):
        self.client.login(username="adminpm", password="testpass123")
        role = "Admin+PM"
        cid = self.client_a.pk

        # Can access client data (has program role)
        self.visit(role, "Client detail", f"/clients/{cid}/")
        self.visit(role, "Notes timeline", f"/notes/client/{cid}/")
        self.visit(role, "Plan view", f"/plans/client/{cid}/")

        # Can also access admin pages
        self.visit(role, "Admin settings", "/admin/settings/")
        self.visit(role, "User list", "/admin/users/")
