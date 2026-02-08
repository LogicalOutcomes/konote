"""Base class for browser-based UX tests using Playwright.

Uses StaticLiveServerTestCase so Django serves static files (CSS, JS)
via finders — no collectstatic needed.  Playwright drives a headless
Chromium browser against the live test server.

No new pip dependencies: uses playwright.sync_api directly + axe-core
injected from CDN for accessibility checks.
"""
import json
import os
import shutil
import tempfile

# DJANGO_ALLOW_ASYNC_UNSAFE is set in setUpClass rather than at module
# level, so importing this module doesn't affect other test classes.

from cryptography.fernet import Fernet
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.utils import timezone

import konote.encryption as enc_module

from .checker import Severity, UxIssue
from .conftest import get_report

# Lazy import — lets the module load even if Playwright isn't installed
# (tests skip gracefully via pytest.importorskip in test_browser.py)
pw_api = None

TEST_KEY = Fernet.generate_key().decode()
TEST_PASSWORD = "testpass123"

# axe-core CDN — pinned version for reproducibility
AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"


def _get_pw():
    """Lazy-load playwright.sync_api on first use."""
    global pw_api
    if pw_api is None:
        from playwright.sync_api import sync_playwright
        pw_api = sync_playwright
    return pw_api


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    RATELIMIT_ENABLE=False,
    SESSION_COOKIE_SECURE=False,
    LANGUAGE_COOKIE_SECURE=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}},
)
class BrowserTestBase(StaticLiveServerTestCase):
    """Base for tests that need a real browser (Playwright + Chromium).

    Uses file-based SQLite instead of :memory: because LiveServerTestCase
    runs the server in a separate thread, and SQLite :memory: databases
    are per-connection (threads can't share them).

    Class-level: one Playwright + browser instance per test class.
    Per-test: fresh browser context + page (isolated cookies/sessions).
    """

    databases = {"default", "audit"}

    # Playwright resources — shared across all test methods in the class
    _pw = None
    _browser = None

    @classmethod
    def setUpClass(cls):
        # Playwright's sync API uses an internal async event loop.
        # Django 4.1+ raises SynchronousOnlyOperation during DB ops
        # from async contexts. This env var allows sync ORM calls.
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        enc_module._fernet = None

        # Switch to file-based SQLite so the live server thread can
        # share the database with the test thread.
        cls._db_dir = tempfile.mkdtemp(prefix="konote_browser_")
        from django.conf import settings
        from django import db

        cls._orig_default = settings.DATABASES["default"]["NAME"]
        cls._orig_audit = settings.DATABASES["audit"]["NAME"]
        settings.DATABASES["default"]["NAME"] = os.path.join(
            cls._db_dir, "default.sqlite3"
        )
        settings.DATABASES["audit"]["NAME"] = os.path.join(
            cls._db_dir, "audit.sqlite3"
        )
        db.connections.close_all()

        super().setUpClass()

        # Create tables in the file-based databases
        from django.core.management import call_command
        call_command("migrate", "--run-syncdb", verbosity=0)
        call_command("migrate", "--database=audit", "--run-syncdb", verbosity=0)

        # Launch Playwright browser once for the entire class
        start = _get_pw()
        cls._pw = start().start()
        cls._browser = cls._pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        if cls._browser:
            cls._browser.close()
        if cls._pw:
            cls._pw.stop()
        super().tearDownClass()

        # Restore original :memory: database settings
        from django.conf import settings
        from django import db
        settings.DATABASES["default"]["NAME"] = cls._orig_default
        settings.DATABASES["audit"]["NAME"] = cls._orig_audit
        db.connections.close_all()

        # Clean up temp database files
        shutil.rmtree(cls._db_dir, ignore_errors=True)
        enc_module._fernet = None

    def setUp(self):
        enc_module._fernet = None
        self._create_test_data()
        self._context = self._browser.new_context()
        self.page = self._context.new_page()

    def tearDown(self):
        if hasattr(self, "page") and self.page:
            self.page.close()
        if hasattr(self, "_context") and self._context:
            self._context.close()
        enc_module._fernet = None

    # ------------------------------------------------------------------
    # Test data — mirrors UxWalkthroughBase.setUpTestData
    # ------------------------------------------------------------------

    def _create_test_data(self):
        """Create test data in setUp (TransactionTestCase flushes between tests)."""
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

        # Programs
        self.program_a = Program.objects.create(
            name="Housing Support", colour_hex="#10B981"
        )
        self.program_b = Program.objects.create(
            name="Youth Services", colour_hex="#3B82F6"
        )

        # Users
        self.receptionist_user = User.objects.create_user(
            username="frontdesk", password=TEST_PASSWORD,
            display_name="Dana Front Desk",
        )
        self.staff_user = User.objects.create_user(
            username="staff", password=TEST_PASSWORD,
            display_name="Casey Worker",
        )
        self.manager_user = User.objects.create_user(
            username="manager", password=TEST_PASSWORD,
            display_name="Morgan Manager",
        )
        self.executive_user = User.objects.create_user(
            username="executive", password=TEST_PASSWORD,
            display_name="Eva Executive",
        )
        self.admin_user = User.objects.create_user(
            username="admin", password=TEST_PASSWORD,
            display_name="Alex Admin",
        )
        self.admin_user.is_admin = True
        self.admin_user.save()

        # Role assignments
        UserProgramRole.objects.create(
            user=self.receptionist_user, program=self.program_a,
            role="receptionist",
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role="staff",
        )
        UserProgramRole.objects.create(
            user=self.manager_user, program=self.program_a,
            role="program_manager",
        )
        UserProgramRole.objects.create(
            user=self.executive_user, program=self.program_a,
            role="executive",
        )

        # Clients
        self.client_a = ClientFile.objects.create(is_demo=False)
        self.client_a.first_name = "Jane"
        self.client_a.last_name = "Doe"
        self.client_a.status = "active"
        self.client_a.consent_given_at = timezone.now()
        self.client_a.consent_type = "written"
        self.client_a.save()

        self.client_b = ClientFile.objects.create(is_demo=False)
        self.client_b.first_name = "Bob"
        self.client_b.last_name = "Smith"
        self.client_b.status = "active"
        self.client_b.save()

        ClientProgramEnrolment.objects.create(
            client_file=self.client_a, program=self.program_a,
        )
        ClientProgramEnrolment.objects.create(
            client_file=self.client_b, program=self.program_b,
        )

        # Custom fields
        self.field_group = CustomFieldGroup.objects.create(
            title="Contact Info", sort_order=1,
        )
        self.phone_field = CustomFieldDefinition.objects.create(
            group=self.field_group, name="Phone Number",
            input_type="text", front_desk_access="edit", sort_order=1,
        )
        self.case_notes_field = CustomFieldDefinition.objects.create(
            group=self.field_group, name="Case Notes",
            input_type="textarea", front_desk_access="none", sort_order=2,
        )
        ClientDetailValue.objects.create(
            client_file=self.client_a, field_def=self.phone_field,
            value="555-1234",
        )

        # Metrics + plan
        self.metric_a = MetricDefinition.objects.create(
            name="PHQ-9 Score", definition="Depression screening (0-27)",
            category="mental_health", min_value=0, max_value=27,
            unit="score", is_enabled=True, is_library=True,
        )
        self.plan_section = PlanSection.objects.create(
            client_file=self.client_a, name="Mental Health Goals",
            program=self.program_a,
        )
        self.plan_target = PlanTarget.objects.create(
            plan_section=self.plan_section, client_file=self.client_a,
            name="Reduce depression symptoms",
            description="Target PHQ-9 below 10",
        )
        PlanTargetMetric.objects.create(
            plan_target=self.plan_target, metric_def=self.metric_a,
        )

        # Note template + notes
        self.note_template = ProgressNoteTemplate.objects.create(
            name="Standard Session",
        )
        ProgressNoteTemplateSection.objects.create(
            template=self.note_template, name="Session Notes",
            section_type="basic", sort_order=1,
        )
        self.note = ProgressNote.objects.create(
            client_file=self.client_a, author=self.staff_user,
            author_program=self.program_a, note_type="quick",
        )
        self.note.notes_text = "Client seemed well today."
        self.note.save()

        # Events + alerts
        self.event_type = EventType.objects.create(
            name="Intake", colour_hex="#22C55E",
        )
        Event.objects.create(
            client_file=self.client_a, title="Initial intake",
            event_type=self.event_type, start_timestamp=timezone.now(),
            author_program=self.program_a,
        )
        Alert.objects.create(
            client_file=self.client_a, content="Safety concern noted",
            author=self.staff_user, author_program=self.program_a,
        )

        # Feature toggles
        FeatureToggle.objects.create(feature_key="programs", is_enabled=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def report(self):
        return get_report()

    def live_url(self, path):
        """Full URL from a path, e.g. '/clients/' -> 'http://localhost:PORT/clients/'."""
        return f"{self.live_server_url}{path}"

    def login_via_browser(self, username):
        """Log in by filling the login form in the real browser."""
        self.page.goto(self.live_url("/auth/login/"))
        self.page.wait_for_load_state("networkidle")
        self.page.fill("#username", username)
        self.page.fill("#password", TEST_PASSWORD)
        # Use specific selector — the login page has language-switch submit
        # buttons before the login form's submit button.
        self.page.click("form[action*='login'] button[type='submit']")
        self.page.wait_for_load_state("networkidle")

    def switch_user(self, username):
        """Switch to a different user (new browser context)."""
        self.page.close()
        self._context.close()
        self._context = self._browser.new_context()
        self.page = self._context.new_page()
        self.login_via_browser(username)

    def switch_user_with_scheme(self, username, color_scheme="light"):
        """Switch to a different user with a specific colour scheme."""
        self.page.close()
        self._context.close()
        self._context = self._browser.new_context(color_scheme=color_scheme)
        self.page = self._context.new_page()
        self.login_via_browser(username)

    def wait_for_htmx(self, timeout=5000):
        """Wait until all HTMX requests have completed.

        Checks that no elements have the htmx-request class (set during
        active requests), then waits a small buffer for the DOM to settle.
        """
        self.page.wait_for_function(
            """() => {
                if (typeof htmx === 'undefined') return true;
                return document.querySelectorAll('.htmx-request').length === 0;
            }""",
            timeout=timeout,
        )
        self.page.wait_for_timeout(200)

    def inject_axe(self):
        """Inject axe-core from CDN into the current page."""
        # Only inject if not already present
        already = self.page.evaluate("() => typeof axe !== 'undefined'")
        if already:
            return
        self.page.add_script_tag(url=AXE_CDN)
        self.page.wait_for_function(
            "() => typeof axe !== 'undefined'", timeout=15000,
        )

    def run_axe(self, options=None):
        """Run axe-core and return the results dict."""
        self.inject_axe()
        opts = json.dumps(options) if options else "{}"
        return self.page.evaluate(
            f"async () => await axe.run(document, {opts})"
        )

    def run_colour_contrast_check(self):
        """Run only the colour contrast rule via axe-core."""
        return self.run_axe(options={
            "runOnly": {"type": "rule", "values": ["color-contrast"]},
        })

    def get_focused_element_info(self):
        """Return info about the currently focused element."""
        return self.page.evaluate("""() => {
            const el = document.activeElement;
            if (!el || el === document.body) return null;
            return {
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                className: el.className || null,
                tabIndex: el.tabIndex,
                text: el.textContent.substring(0, 80).trim(),
                role: el.getAttribute('role'),
                ariaLabel: el.getAttribute('aria-label'),
            };
        }""")

    def focus_is_inside(self, container_selector):
        """Check if the currently focused element is inside a container."""
        return self.page.evaluate(f"""() => {{
            const container = document.querySelector('{container_selector}');
            return container && container.contains(document.activeElement)
                   && document.activeElement !== document.body;
        }}""")

    def record_browser_finding(self, category, severity, url, description, detail=""):
        """Record a finding into the shared UX report."""
        self.report.record_browser_finding(
            category=category,
            severity=severity,
            url=url,
            description=description,
            detail=detail,
        )
