"""Scenario-based UX walkthrough tests — story-driven, multi-user simulations.

These tests complement test_roles.py (page-by-page per role) with realistic
user journeys that test handoffs, privacy isolation, and bilingual workflows.

Run all scenarios:
    pytest tests/ux_walkthrough/test_scenarios.py -v

Run a single scenario:
    pytest tests/ux_walkthrough/test_scenarios.py::CrossProgramIsolationScenario -v
"""
from django.test import override_settings

from .base import TEST_KEY, UxScenarioBase
from .checker import Severity

# ------------------------------------------------------------------
# Forbidden content constants — what each user should NEVER see
# ------------------------------------------------------------------

# Casey (Housing Support staff) should never see Youth Services data
CASEY_FORBIDDEN = ["Bob", "Smith", "Youth Services"]

# A hypothetical Youth Services worker should never see Housing data
HOUSING_FORBIDDEN = ["Jane", "Doe", "Housing Support"]

# English UI strings that should NOT appear when language is French.
# NOTE: Program names ("Housing Support") are data, not translated UI.
# This list only includes strings wrapped in {% trans %} in templates.
ENGLISH_UI_STRINGS = [
    "Sign Out",
    "Dashboard",
    "Reports",
    "Filters",
    "Active",
    "Inactive",
    "Status",
    "Privacy",
    "Help",
    "Logged in as",
]


# =====================================================================
# Scenario 2: Cross-Program Data Isolation
# =====================================================================
# Priority: HIGHEST — validates that users can't see data from programs
# they aren't assigned to. This is the core privacy guarantee.


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CrossProgramIsolationScenario(UxScenarioBase):
    """Scenario: Casey (Housing Support staff) must never see data from
    Youth Services. Bob Smith is enrolled only in Youth Services.

    Tests privacy at multiple layers:
    - Client list: Bob's name must not appear
    - Client search: searching for Bob must return no results
    - Direct URL: accessing Bob's profile must return 403
    - HTMX partials: custom field partials must also be blocked
    """

    SCENARIO = "Cross-Program Isolation"

    def test_client_list_hides_other_programs(self):
        """Casey's client list shows only Housing Support clients."""
        self.login_as("staff", forbidden_content=CASEY_FORBIDDEN)
        role = "Direct Service"

        resp = self.visit(role, "Client list (Housing only)", "/clients/")
        # visit() already ran _scan_response via session forbidden content
        self.record_scenario(
            self.SCENARIO, role, "Client list (Housing only)",
            "/clients/", resp.status_code, [],
        )

    def test_search_hides_other_programs(self):
        """Searching for a Youth Services client returns nothing for Casey.

        Note: The search input echoes the query term, so we can't use
        forbidden_content scanning here (it would always find the query
        in the HTML). Instead we temporarily clear session forbidden and
        check that no client profile links appear in the results.
        """
        self.login_as("staff")  # No session forbidden — we check manually
        role = "Direct Service"

        url = "/clients/search/?q=Bob"
        resp = self.visit(role, "Search for Bob (should find no results)", url)

        # Check that no link to Bob's client profile appears in results
        issues = []
        if resp.status_code == 200:
            body = resp.content.decode("utf-8", errors="replace")
            bob_url = f"/clients/{self.client_b.pk}/"
            if bob_url in body:
                issues.append(self._make_issue(
                    Severity.CRITICAL, url, role,
                    "Search results for Bob",
                    f"Link to Bob's profile ({bob_url}) found in search results",
                ))

        self.record_scenario(
            self.SCENARIO, role, "Search for Bob (no results expected)",
            url, resp.status_code, issues,
        )

    def test_direct_url_blocked(self):
        """Casey can't access Bob's profile by guessing the URL."""
        self.login_as("staff", forbidden_content=CASEY_FORBIDDEN)
        role = "Direct Service"

        url = f"/clients/{self.client_b.pk}/"
        resp = self.visit_forbidden(
            role, "Direct access to Bob's profile (403)", url,
        )
        self.record_scenario(
            self.SCENARIO, role, "Direct access to Bob (403)",
            url, resp.status_code, [],
        )

    def test_htmx_partial_blocked(self):
        """HTMX requests for Bob's data are also blocked."""
        self.login_as("staff", forbidden_content=CASEY_FORBIDDEN)
        role = "Direct Service"

        url = f"/clients/{self.client_b.pk}/custom-fields/display/"
        resp = self.client.get(url, HTTP_HX_REQUEST="true")
        # Should be 403 — middleware blocks before the view runs
        issues = []
        if resp.status_code != 403:
            issues.append(self._make_issue(
                "critical", url, role,
                "HTMX partial for Bob's custom fields",
                f"Expected 403, got {resp.status_code}",
            ))
        self.record_scenario(
            self.SCENARIO, role, "HTMX partial for Bob (403)",
            url, resp.status_code, issues,
        )

    def test_own_program_data_visible(self):
        """Casey CAN see Jane (Housing Support) — sanity check."""
        self.login_as("staff", forbidden_content=CASEY_FORBIDDEN)
        role = "Direct Service"

        url = f"/clients/{self.client_a.pk}/"
        resp = self.visit(role, "Access Jane's profile (own program)", url)
        # Jane's data should be visible — check status is 200
        issues = []
        if resp.status_code != 200:
            issues.append(self._make_issue(
                "critical", url, role,
                "Jane's profile (own program)",
                f"Expected 200, got {resp.status_code}",
            ))
        self.record_scenario(
            self.SCENARIO, role, "Jane's profile (own program)",
            url, resp.status_code, issues,
        )

    def test_plan_target_history_blocked(self):
        """Casey can't view revision history for Bob's plan targets."""
        self.login_as("staff", forbidden_content=CASEY_FORBIDDEN)
        role = "Direct Service"

        url = f"/plans/targets/{self.plan_target_b.pk}/history/"
        resp = self.visit_forbidden(
            role, "Target history for Bob (403)", url,
        )
        self.record_scenario(
            self.SCENARIO, role, "Target history blocked",
            url, resp.status_code, [],
        )

    def test_admin_without_program_sees_no_clients(self):
        """Admin (no program role) sees no client data at all."""
        self.login_as("admin")
        role = "Admin (no program)"

        url = f"/clients/{self.client_a.pk}/"
        resp = self.visit_forbidden(
            role, "Admin blocked from client detail (403)", url,
        )
        self.record_scenario(
            self.SCENARIO, role, "Admin blocked from Jane (403)",
            url, resp.status_code, [],
        )


# =====================================================================
# Scenario 1: Morning Intake Flow
# =====================================================================
# Story: A new client arrives. Dana (reception) searches but can't find
# them. Casey (staff) creates the client file and writes a quick note.
# Morgan (manager) reviews and adds a plan section.


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MorningIntakeScenario(UxScenarioBase):
    """Scenario: New client Maria Santos arrives for intake.

    Act 1: Dana (Front Desk) searches, not found — Dana creates the file
    Act 2: Casey (Staff) documents the intake with a progress note
    Act 3: Morgan (Manager) reviews the client and plan (read-only)
    """

    SCENARIO = "Morning Intake Flow"

    def test_morning_intake(self):
        # =============================================================
        # Act 1: Dana (Front Desk) — searches and creates the client
        # =============================================================
        self.login_as("frontdesk", forbidden_content=CASEY_FORBIDDEN)
        role = "Front Desk"

        # Dana searches — Maria isn't in the system yet
        resp = self.visit(
            role, "Search for unknown client",
            "/clients/search/?q=Maria",
        )
        self.record_scenario(
            self.SCENARIO, role, "Search for Maria (not found)",
            "/clients/search/?q=Maria", resp.status_code, [],
        )

        # Dana opens the create form (client.create: ALLOW for receptionist)
        resp = self.visit(
            role, "Create client form", "/clients/create/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Dana opens create form",
            "/clients/create/", resp.status_code, [],
        )

        # =============================================================
        # Act 2: Casey (Staff) — documents the intake
        # =============================================================
        self.login_as("staff", forbidden_content=CASEY_FORBIDDEN)
        role = "Direct Service"

        # Casey creates Maria's file (staff also has client.create)
        new_client = self.quick_create_client(
            "Maria", "Santos", self.program_a,
        )
        self.assertIsNotNone(new_client, "Client creation failed")
        cid = new_client.pk

        # Casey views Maria's new profile
        resp = self.visit(
            role, "View new client profile", f"/clients/{cid}/",
        )
        self.record_scenario(
            self.SCENARIO, role, "View Maria's profile",
            f"/clients/{cid}/", resp.status_code, [],
        )

        # Casey writes a quick note about the intake
        resp = self.visit_and_follow(
            role, "Document intake session",
            f"/notes/client/{cid}/quick/",
            data={
                "interaction_type": "session",
                "notes_text": "Initial intake with Maria Santos. "
                    "Referred to Housing Support program.",
                "consent_confirmed": "on",
            },
            expected_redirect=f"/notes/client/{cid}/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Write intake note",
            f"/notes/client/{cid}/quick/", resp.status_code, [],
        )

        # Casey checks the notes timeline — should show the new note
        resp = self.visit(
            role, "Notes timeline after intake",
            f"/notes/client/{cid}/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Check notes timeline",
            f"/notes/client/{cid}/", resp.status_code, [],
        )

        # =============================================================
        # Act 3: Morgan (Manager) — reviews (read-only)
        # =============================================================
        self.login_as("manager", forbidden_content=CASEY_FORBIDDEN)
        role = "Program Manager"

        # Morgan views Maria's profile
        resp = self.visit(
            role, "Review new client", f"/clients/{cid}/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Review Maria's profile",
            f"/clients/{cid}/", resp.status_code, [],
        )

        # Morgan views the plan page (read-only — plan.edit: DENY)
        resp = self.visit(
            role, "Plan view (empty for new client)",
            f"/plans/client/{cid}/",
            role_should_not_see=["Add Section"],
        )
        self.record_scenario(
            self.SCENARIO, role, "View empty plan",
            f"/plans/client/{cid}/", resp.status_code, [],
        )

        # Morgan can't create plan sections (plan.edit: DENY)
        resp = self.visit_forbidden(
            role, "Create plan section (403)",
            f"/plans/client/{cid}/sections/create/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create plan section",
            f"/plans/client/{cid}/sections/create/", resp.status_code, [],
        )


# =====================================================================
# Scenario 3: Full French Workday
# =====================================================================
# Story: Dana's agency serves francophone clients. She switches to
# French and completes a full workflow. English UI strings should not
# appear — but program names and client names are data, not UI, so
# they stay as-is regardless of language.


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FrenchWorkdayScenario(UxScenarioBase):
    """Scenario: Dana switches to French and navigates the key pages.

    Checks that Django i18n strings are properly translated — English
    UI labels like 'Sign Out', 'Dashboard', 'Reports' should be
    replaced with French equivalents.

    NOTE: Program names ('Housing Support') are data stored in the
    database, not translatable via i18n. This scenario tests UI chrome
    translation only.
    """

    SCENARIO = "Full French Workday"

    def test_french_workflow(self):
        self.login_as("frontdesk")
        self.switch_language("fr")
        role = "Front Desk (FR)"
        cid = self.client_a.pk

        # Each page is visited in French with English UI strings forbidden.
        # If a translation is missing, Django renders the English msgid,
        # which the forbidden_content check will catch.

        pages = [
            ("Home page", "/"),
            ("Client list", "/clients/"),
            ("Client detail", f"/clients/{cid}/"),
            ("Programs list", "/programs/"),
        ]

        for step_name, url in pages:
            resp = self.visit(
                role, step_name, url,
                expected_lang="fr",
                forbidden_content=ENGLISH_UI_STRINGS,
            )
            # visit() already ran _scan_response with forbidden_content,
            # so we just record the scenario step without re-scanning.
            self.record_scenario(
                self.SCENARIO, role, step_name,
                url, resp.status_code, [],
            )

        # Switch back to English to avoid affecting other tests
        self.switch_language("en")


# =====================================================================
# Scenario 4: Client Search by Note Content
# =====================================================================
# Story: Casey searches the client list for text that appears only in
# progress notes, not in the client's name or record ID. The search
# should find the correct client. It must NOT surface clients from
# programs Casey can't access.


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class NoteContentSearchScenario(UxScenarioBase):
    """Scenario: Searching the client list and search page by note content.

    Jane (Housing Support) has a note: "Client seemed well today."
    Bob (Youth Services) has a note: "Discussed vocational training options."
    Casey is Housing Support staff — can see Jane but not Bob.
    """

    SCENARIO = "Client Note Search"

    def test_client_list_search_by_note_content(self):
        """Casey searches the client list for text in Jane's note."""
        self.login_as("staff", forbidden_content=CASEY_FORBIDDEN)
        role = "Direct Service"

        url = "/clients/?q=seemed+well"
        resp = self.visit(role, "Search client list by note text", url)

        issues = []
        if resp.status_code == 200:
            body = resp.content.decode("utf-8", errors="replace")
            jane_url = f"/clients/{self.client_a.pk}/"
            if jane_url not in body:
                issues.append(self._make_issue(
                    Severity.CRITICAL, url, role,
                    "Search client list by note text",
                    "Jane not found when searching for text in her note",
                ))

        self.record_scenario(
            self.SCENARIO, role, "Client list search by note content",
            url, resp.status_code, issues,
        )

    def test_dedicated_search_by_note_content(self):
        """Casey searches the dedicated search page for text in Jane's note."""
        self.login_as("staff")
        role = "Direct Service"

        url = "/clients/search/?q=seemed+well"
        resp = self.visit(role, "Dedicated search by note text", url)

        issues = []
        if resp.status_code == 200:
            body = resp.content.decode("utf-8", errors="replace")
            jane_url = f"/clients/{self.client_a.pk}/"
            if jane_url not in body:
                issues.append(self._make_issue(
                    Severity.CRITICAL, url, role,
                    "Dedicated search by note text",
                    "Jane not found when searching for text in her note",
                ))

        self.record_scenario(
            self.SCENARIO, role, "Dedicated search by note content",
            url, resp.status_code, issues,
        )

    def test_note_search_respects_program_isolation(self):
        """Casey must NOT find Bob by searching for text in Bob's notes.

        Bob's note says "vocational training" — Casey should get no
        results for that phrase since Bob is in Youth Services.
        """
        self.login_as("staff")
        role = "Direct Service"

        url = "/clients/search/?q=vocational"
        resp = self.visit(role, "Search for other program's note content", url)

        issues = []
        if resp.status_code == 200:
            body = resp.content.decode("utf-8", errors="replace")
            bob_url = f"/clients/{self.client_b.pk}/"
            if bob_url in body:
                issues.append(self._make_issue(
                    Severity.CRITICAL, url, role,
                    "Note search isolation",
                    f"Bob's profile link ({bob_url}) found — note content "
                    "leaked across programs",
                ))

        self.record_scenario(
            self.SCENARIO, role, "Note search isolation (no cross-program leak)",
            url, resp.status_code, issues,
        )


# =====================================================================
# Scenario 5: Group & Plan Permission Leakage
# =====================================================================
# Priority: HIGH — validates that users can't access groups, milestones,
# memberships, or plan data from programs they aren't assigned to.
# Complements CrossProgramIsolationScenario (which tests client data).


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GroupPermissionLeakageScenario(UxScenarioBase):
    """Scenario: Casey (Housing Support staff) must not access groups,
    milestones, or plan data in Youth Services.

    Tests program isolation at the group and plan level:
    - Group detail for other program's group must return 403
    - Session log for other program's group must return 403
    - Membership remove in other program must return 403
    - Milestone create/edit in other program must return 403
    - Outcome create in other program must return 403
    - Plan target history for other program's client must return 403
    """

    SCENARIO = "Group Permission Leakage"

    def test_group_detail_blocked(self):
        """Casey can't view a group in Youth Services."""
        self.login_as("staff", forbidden_content=CASEY_FORBIDDEN)
        role = "Direct Service"
        url = f"/groups/{self.group_b.pk}/"
        resp = self.visit_forbidden(role, "Group detail (other program, 403)", url)
        self.record_scenario(
            self.SCENARIO, role, "Group detail blocked",
            url, resp.status_code, [],
        )

    def test_session_log_blocked(self):
        """Casey can't log a session for a Youth Services group."""
        self.login_as("staff", forbidden_content=CASEY_FORBIDDEN)
        role = "Direct Service"
        url = f"/groups/{self.group_b.pk}/session/"
        resp = self.visit_forbidden(role, "Session log (other program, 403)", url)
        self.record_scenario(
            self.SCENARIO, role, "Session log blocked",
            url, resp.status_code, [],
        )

    def test_membership_remove_blocked(self):
        """Casey can't remove a member from a Youth Services group."""
        self.login_as("staff")
        role = "Direct Service"
        url = f"/groups/member/{self.membership_b.pk}/remove/"
        resp = self.client.post(url)
        issues = []
        if resp.status_code != 403:
            issues.append(self._make_issue(
                Severity.CRITICAL, url, role,
                "Membership remove (other program)",
                f"Expected 403, got {resp.status_code}",
            ))
        self.record_scenario(
            self.SCENARIO, role, "Membership remove blocked",
            url, resp.status_code, issues,
        )

    def test_milestone_create_blocked(self):
        """Casey can't create a milestone in a Youth Services group."""
        self.login_as("staff")
        role = "Direct Service"
        url = f"/groups/{self.group_b.pk}/milestone/"
        resp = self.client.post(url, {"title": "Hacked", "status": "not_started"})
        issues = []
        if resp.status_code != 403:
            issues.append(self._make_issue(
                Severity.CRITICAL, url, role,
                "Milestone create (other program)",
                f"Expected 403, got {resp.status_code}",
            ))
        self.record_scenario(
            self.SCENARIO, role, "Milestone create blocked",
            url, resp.status_code, issues,
        )

    def test_milestone_edit_blocked(self):
        """Casey can't edit a milestone in a Youth Services group."""
        self.login_as("staff", forbidden_content=CASEY_FORBIDDEN)
        role = "Direct Service"
        url = f"/groups/milestone/{self.milestone_b.pk}/edit/"
        resp = self.visit_forbidden(role, "Milestone edit (other program, 403)", url)
        self.record_scenario(
            self.SCENARIO, role, "Milestone edit blocked",
            url, resp.status_code, [],
        )

    def test_outcome_create_blocked(self):
        """Casey can't record an outcome in a Youth Services group."""
        self.login_as("staff")
        role = "Direct Service"
        url = f"/groups/{self.group_b.pk}/outcome/"
        resp = self.client.post(url, {
            "outcome_date": "2026-01-15",
            "description": "Hacked outcome",
        })
        issues = []
        if resp.status_code != 403:
            issues.append(self._make_issue(
                Severity.CRITICAL, url, role,
                "Outcome create (other program)",
                f"Expected 403, got {resp.status_code}",
            ))
        self.record_scenario(
            self.SCENARIO, role, "Outcome create blocked",
            url, resp.status_code, issues,
        )

    def test_target_history_blocked(self):
        """Casey can't view plan target history for a Youth Services client."""
        self.login_as("staff", forbidden_content=CASEY_FORBIDDEN)
        role = "Direct Service"
        url = f"/plans/targets/{self.plan_target_b.pk}/history/"
        resp = self.visit_forbidden(role, "Target history (other program, 403)", url)
        self.record_scenario(
            self.SCENARIO, role, "Target history blocked",
            url, resp.status_code, [],
        )

    def test_own_program_group_accessible(self):
        """Casey CAN access her own program's group — sanity check."""
        self.login_as("staff", forbidden_content=CASEY_FORBIDDEN)
        role = "Direct Service"
        url = f"/groups/{self.group_a.pk}/"
        resp = self.visit(role, "Own program group (200)", url)
        issues = []
        if resp.status_code != 200:
            issues.append(self._make_issue(
                Severity.CRITICAL, url, role,
                "Own program group",
                f"Expected 200, got {resp.status_code}",
            ))
        self.record_scenario(
            self.SCENARIO, role, "Own program group accessible",
            url, resp.status_code, issues,
        )
