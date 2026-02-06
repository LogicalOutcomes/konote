"""Base test class with shared test data and visit helpers."""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from django.utils import timezone

import konote.encryption as enc_module

from .checker import Severity, UxChecker
from .conftest import get_report

TEST_KEY = Fernet.generate_key().decode()

# Default password for all test users
TEST_PASSWORD = "testpass123"


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class UxWalkthroughBase(TestCase):
    """Base class for all UX walkthrough tests.

    Provides shared test data, visit helpers, and report collection.
    """

    databases = {"default", "audit"}

    @classmethod
    def setUpTestData(cls):
        """Create all test data once for the entire test class."""
        enc_module._fernet = None

        from apps.admin_settings.models import FeatureToggle
        from apps.auth_app.models import User
        from apps.clients.models import (
            ClientDetailValue,
            ClientFile,
            ClientProgramEnrolment,
            CustomFieldDefinition,
            CustomFieldGroup,
        )
        from apps.events.models import Alert, Event, EventType
        from apps.notes.models import (
            ProgressNote,
            ProgressNoteTemplate,
            ProgressNoteTemplateSection,
        )
        from apps.plans.models import (
            MetricDefinition,
            PlanSection,
            PlanTarget,
            PlanTargetMetric,
        )
        from apps.programs.models import Program, UserProgramRole

        # --- Programs ---
        cls.program_a = Program.objects.create(
            name="Housing Support", colour_hex="#10B981"
        )
        cls.program_b = Program.objects.create(
            name="Youth Services", colour_hex="#3B82F6"
        )

        # --- Users ---
        cls.receptionist_user = User.objects.create_user(
            username="frontdesk",
            password="testpass123",
            display_name="Dana Front Desk",
        )
        cls.staff_user = User.objects.create_user(
            username="staff",
            password="testpass123",
            display_name="Casey Worker",
        )
        cls.manager_user = User.objects.create_user(
            username="manager",
            password="testpass123",
            display_name="Morgan Manager",
        )
        cls.executive_user = User.objects.create_user(
            username="executive",
            password="testpass123",
            display_name="Eva Executive",
        )
        cls.admin_user = User.objects.create_user(
            username="admin",
            password="testpass123",
            display_name="Alex Admin",
        )
        cls.admin_user.is_admin = True
        cls.admin_user.save()

        cls.admin_pm_user = User.objects.create_user(
            username="adminpm",
            password="testpass123",
            display_name="Admin PM",
        )
        cls.admin_pm_user.is_admin = True
        cls.admin_pm_user.save()

        # --- Role assignments ---
        UserProgramRole.objects.create(
            user=cls.receptionist_user,
            program=cls.program_a,
            role="receptionist",
        )
        UserProgramRole.objects.create(
            user=cls.staff_user,
            program=cls.program_a,
            role="staff",
        )
        UserProgramRole.objects.create(
            user=cls.manager_user,
            program=cls.program_a,
            role="program_manager",
        )
        UserProgramRole.objects.create(
            user=cls.executive_user,
            program=cls.program_a,
            role="executive",
        )
        UserProgramRole.objects.create(
            user=cls.admin_pm_user,
            program=cls.program_a,
            role="program_manager",
        )
        UserProgramRole.objects.create(
            user=cls.admin_pm_user,
            program=cls.program_b,
            role="program_manager",
        )

        # --- Clients ---
        cls.client_a = ClientFile.objects.create(is_demo=False)
        cls.client_a.first_name = "Jane"
        cls.client_a.last_name = "Doe"
        cls.client_a.status = "active"
        cls.client_a.consent_given_at = timezone.now()
        cls.client_a.consent_type = "written"
        cls.client_a.save()

        cls.client_b = ClientFile.objects.create(is_demo=False)
        cls.client_b.first_name = "Bob"
        cls.client_b.last_name = "Smith"
        cls.client_b.status = "active"
        cls.client_b.save()

        ClientProgramEnrolment.objects.create(
            client_file=cls.client_a, program=cls.program_a
        )
        ClientProgramEnrolment.objects.create(
            client_file=cls.client_b, program=cls.program_b
        )

        # --- Custom fields ---
        cls.field_group = CustomFieldGroup.objects.create(
            title="Contact Info", sort_order=1
        )
        cls.phone_field = CustomFieldDefinition.objects.create(
            group=cls.field_group,
            name="Phone Number",
            input_type="text",
            front_desk_access="edit",
            sort_order=1,
        )
        cls.case_notes_field = CustomFieldDefinition.objects.create(
            group=cls.field_group,
            name="Case Notes",
            input_type="textarea",
            front_desk_access="none",
            sort_order=2,
        )
        ClientDetailValue.objects.create(
            client_file=cls.client_a,
            field_def=cls.phone_field,
            value="555-1234",
        )

        # --- Metrics ---
        cls.metric_a = MetricDefinition.objects.create(
            name="PHQ-9 Score",
            definition="Depression screening (0-27)",
            category="mental_health",
            min_value=0,
            max_value=27,
            unit="score",
            is_enabled=True,
            is_library=True,
        )

        # --- Plan ---
        cls.plan_section = PlanSection.objects.create(
            client_file=cls.client_a,
            name="Mental Health Goals",
            program=cls.program_a,
        )
        cls.plan_target = PlanTarget.objects.create(
            plan_section=cls.plan_section,
            client_file=cls.client_a,
            name="Reduce depression symptoms",
            description="Target PHQ-9 below 10",
        )
        PlanTargetMetric.objects.create(
            plan_target=cls.plan_target, metric_def=cls.metric_a
        )

        # --- Note template ---
        cls.note_template = ProgressNoteTemplate.objects.create(
            name="Standard Session"
        )
        ProgressNoteTemplateSection.objects.create(
            template=cls.note_template,
            name="Session Notes",
            section_type="basic",
            sort_order=1,
        )

        # --- Progress note ---
        cls.note = ProgressNote.objects.create(
            client_file=cls.client_a,
            author=cls.staff_user,
            author_program=cls.program_a,
            note_type="quick",
        )
        cls.note.notes_text = "Client seemed well today."
        cls.note.save()

        # --- Event type + event + alert ---
        cls.event_type = EventType.objects.create(
            name="Intake", colour_hex="#22C55E"
        )
        cls.event = Event.objects.create(
            client_file=cls.client_a,
            title="Initial intake",
            event_type=cls.event_type,
            start_timestamp=timezone.now(),
            author_program=cls.program_a,
        )
        cls.alert = Alert.objects.create(
            client_file=cls.client_a,
            content="Safety concern noted",
            author=cls.staff_user,
            author_program=cls.program_a,
        )

        # --- Feature toggles ---
        FeatureToggle.objects.create(
            feature_key="programs", is_enabled=True
        )

    def setUp(self):
        enc_module._fernet = None
        # Don't raise exceptions on server errors — record them as issues
        self.client.raise_request_exception = False
        # Session-level forbidden content (set by login_as in UxScenarioBase)
        self._session_forbidden: list[str] = []

    def tearDown(self):
        enc_module._fernet = None

    @property
    def report(self):
        return get_report()

    # ------------------------------------------------------------------
    # Visit helpers
    # ------------------------------------------------------------------

    def _make_issue(self, severity, url, role, step, description):
        """Helper to create a UxIssue without needing a checker."""
        from .checker import UxIssue
        return UxIssue(
            severity=severity, url=url, role=role, step=step,
            description=description,
        )

    def _scan_response(self, response, role, step, url, forbidden_content=None):
        """Scan a response for forbidden content (privacy check).

        Merges session-level _session_forbidden with per-call forbidden_content.
        Only scans 200 responses where content is actually displayed.
        """
        all_forbidden = self._session_forbidden + (forbidden_content or [])
        issues = []
        if all_forbidden and response.status_code == 200:
            body = response.content.decode("utf-8", errors="replace").lower()
            for item in all_forbidden:
                if item.lower() in body:
                    issues.append(self._make_issue(
                        Severity.CRITICAL, url, role, step,
                        f"Forbidden content found: '{item}'",
                    ))
        return issues

    def visit(
        self,
        role: str,
        step: str,
        url: str,
        expected_status: int = 200,
        expected_lang: str = "en",
        role_should_see: list | None = None,
        role_should_not_see: list | None = None,
        forbidden_content: list | None = None,
    ):
        """GET a URL, run full-page UX checks, record results."""
        response = self.client.get(url)
        issues = []

        if response.status_code == 500:
            issues.append(self._make_issue(
                Severity.CRITICAL, url, role, step,
                "Server error (500) — view crashed",
            ))
        elif response.status_code == 200 and expected_status == 200:
            checker = UxChecker(
                response, url, role, step,
                is_partial=False,
                expected_lang=expected_lang,
                role_should_see=role_should_see,
                role_should_not_see=role_should_not_see,
            )
            issues = checker.run_all_checks()
        elif response.status_code != expected_status:
            issues.append(self._make_issue(
                Severity.CRITICAL, url, role, step,
                f"Expected {expected_status}, got {response.status_code}",
            ))

        issues.extend(self._scan_response(response, role, step, url, forbidden_content))
        self.report.record_step(role, step, url, response.status_code, issues)
        return response

    def visit_htmx(
        self,
        role: str,
        step: str,
        url: str,
        role_should_see: list | None = None,
        role_should_not_see: list | None = None,
        forbidden_content: list | None = None,
    ):
        """GET with HX-Request header, run partial UX checks."""
        response = self.client.get(url, HTTP_HX_REQUEST="true")
        issues = []

        if response.status_code == 500:
            issues.append(self._make_issue(
                Severity.CRITICAL, url, role, step,
                "Server error (500) on HTMX partial",
            ))
        elif response.status_code == 200:
            checker = UxChecker(
                response, url, role, step,
                is_partial=True,
                role_should_see=role_should_see,
                role_should_not_see=role_should_not_see,
            )
            issues = checker.run_all_checks()

        issues.extend(self._scan_response(response, role, step, url, forbidden_content))
        self.report.record_step(role, step, url, response.status_code, issues)
        return response

    def visit_and_follow(
        self,
        role: str,
        step: str,
        url: str,
        data: dict,
        expected_redirect: str | None = None,
        forbidden_content: list | None = None,
    ):
        """POST with follow=True, check redirect + success message on landing."""
        response = self.client.post(url, data, follow=True)
        issues = []

        if response.status_code == 500:
            issues.append(self._make_issue(
                Severity.CRITICAL, url, role, step,
                "Server error (500) after POST",
            ))
        else:
            # Check redirect chain
            if response.redirect_chain:
                final_url = response.redirect_chain[-1][0]
                if expected_redirect and expected_redirect not in final_url:
                    issues.append(self._make_issue(
                        Severity.WARNING, url, role, step,
                        f"Expected redirect to contain '{expected_redirect}', "
                        f"got '{final_url}'",
                    ))

            # Run UX checks on the final landing page
            if response.status_code == 200:
                checker = UxChecker(
                    response, url, role, step, is_partial=False,
                )
                issues.extend(checker.run_all_checks())
                # Check for success message
                checker.check_success_message()
                issues.extend(
                    [i for i in checker.issues if i not in issues]
                )

        issues.extend(self._scan_response(response, role, step, url, forbidden_content))
        self.report.record_step(role, step, url, response.status_code, issues)
        return response

    def visit_forbidden(self, role: str, step: str, url: str):
        """Visit a URL that should return 403, check error page quality.

        Note: forbidden_content scan is skipped on 403 pages — the access
        control already worked, so there's nothing to leak.
        """
        response = self.client.get(url)
        issues = []

        if response.status_code == 403:
            checker = UxChecker(response, url, role, step, is_partial=False)
            checker.check_403_quality()
            issues = checker.issues
        else:
            issues.append(self._make_issue(
                Severity.CRITICAL, url, role, step,
                f"Expected 403, got {response.status_code}",
            ))

        self.report.record_step(role, step, url, response.status_code, issues)
        return response

    def visit_redirect(self, role: str, step: str, url: str, forbidden_content=None):
        """Visit a URL that should redirect, follow it, check landing page."""
        response = self.client.get(url, follow=True)
        issues = []

        if response.status_code == 500:
            issues.append(self._make_issue(
                Severity.CRITICAL, url, role, step,
                "Server error (500) on redirect follow",
            ))
        else:
            if not response.redirect_chain:
                issues.append(self._make_issue(
                    Severity.WARNING, url, role, step,
                    "Expected redirect but got direct response",
                ))
            if response.status_code == 200:
                checker = UxChecker(
                    response, url, role, step, is_partial=False,
                )
                issues.extend(checker.run_all_checks())

        issues.extend(self._scan_response(response, role, step, url, forbidden_content))
        self.report.record_step(role, step, url, response.status_code, issues)
        return response


# =====================================================================
# Scenario Base — for story-driven multi-user walkthrough tests
# =====================================================================


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}},
)
class UxScenarioBase(UxWalkthroughBase):
    """Base for scenario tests that simulate real user journeys.

    Inherits all reference data from UxWalkthroughBase.setUpTestData.
    Scenarios create transactional data during test execution — Django
    TestCase rolls it back after each test method.

    IMPORTANT: Must use TestCase (not TransactionTestCase) to ensure
    each scenario's transactional data is rolled back and doesn't leak
    to other scenarios.
    """

    def login_as(self, username, forbidden_content=None):
        """Login as a user and set session-level forbidden content.

        Every subsequent visit() call will automatically scan responses
        for the forbidden strings (privacy check). This resets when
        login_as() is called again for a different user.
        """
        self.client.login(username=username, password=TEST_PASSWORD)
        self._session_forbidden = forbidden_content or []

    def switch_language(self, lang_code):
        """Switch the test client's language and set the cookie.

        Use 'en' or 'fr'. All subsequent visit() calls will check
        the lang attribute matches.
        """
        self.client.post("/i18n/switch/", {"language": lang_code})
        self.client.cookies["django_language"] = lang_code

    def record_scenario(self, scenario, role, step, url, status_code, issues):
        """Record a scenario step for the Scenario Walkthroughs report section."""
        self.report.record_scenario_step(
            scenario, role, step, url, status_code, issues,
        )

    def quick_create_client(self, first_name, last_name, program):
        """Create a client via POST, return the new ClientFile.

        This is a data helper — it creates the client but doesn't run
        UX checks. Use visit() calls in the scenario for UX assertions.
        """
        from apps.clients.models import ClientFile

        self.client.post("/clients/create/", data={
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": "",
            "birth_date": "",
            "record_id": "",
            "status": "active",
            "programs": [program.pk],
        })
        return ClientFile.objects.order_by("-pk").first()
