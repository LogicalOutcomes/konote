"""Automated axe-core accessibility smoke tests for CI.

Runs axe-core on key pages and fails on critical or serious violations.
Uses Playwright + CDN-hosted axe-core (same approach as browser_base.py).

Marked @browser so it runs in the dedicated a11y CI job, not the fast
unit-test job.

Run locally:  pytest tests/test_a11y_ci.py -v --override-ini="addopts=-v --tb=short"
"""
import json
import os
import shutil
import tempfile

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

import pytest
from cryptography.fernet import Fernet
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings

import konote.encryption as enc_module

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

TEST_KEY = Fernet.generate_key().decode()
AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"

# Pages to test (path, description, requires_login)
SMOKE_PAGES = [
    ("/auth/login/", "Login page", False),
    ("/", "Dashboard", True),
    ("/participants/", "Participant list", True),
]


@pytest.mark.browser
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AxeA11ySmokeTest(StaticLiveServerTestCase):
    """Run axe-core on key pages — fail on critical or serious violations.

    Uses file-based SQLite for LiveServerTestCase thread safety.
    """

    databases = {"default", "audit"}

    @classmethod
    def setUpClass(cls):
        if not HAS_PLAYWRIGHT:
            raise pytest.skip("Playwright not installed")
        enc_module._fernet = None

        cls._db_dir = tempfile.mkdtemp(prefix="konote_a11y_")
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

        from django.core.management import call_command
        call_command("migrate", "--run-syncdb", verbosity=0)
        call_command("migrate", "--database=audit", "--run-syncdb", verbosity=0)

        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()
        super().tearDownClass()

        from django.conf import settings
        from django import db
        settings.DATABASES["default"]["NAME"] = cls._orig_default
        settings.DATABASES["audit"]["NAME"] = cls._orig_audit
        db.connections.close_all()
        shutil.rmtree(cls._db_dir, ignore_errors=True)
        enc_module._fernet = None

    def setUp(self):
        enc_module._fernet = None
        self._create_minimal_data()
        self._context = self._browser.new_context()
        self.page = self._context.new_page()

    def tearDown(self):
        self.page.close()
        self._context.close()
        enc_module._fernet = None

    def _create_minimal_data(self):
        """Create just enough data for pages to render."""
        from apps.auth_app.models import User
        from apps.programs.models import Program, UserProgramRole

        self.user = User.objects.create_user(
            username="a11y_staff", password="testpass123",
            is_admin=True, display_name="A11y Tester",
        )
        self.program = Program.objects.create(
            name="Test Program", colour_hex="#10B981",
        )
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="program_manager",
        )

    def _login(self):
        """Log in via the login form."""
        self.page.goto(f"{self.live_server_url}/auth/login/")
        self.page.wait_for_load_state("networkidle")

        # Dismiss language chooser if present
        english_btn = self.page.locator("button.lang-chooser-btn:has-text('English')")
        if english_btn.count() > 0:
            english_btn.click()
            self.page.wait_for_load_state("networkidle")

        self.page.locator("#username").fill("a11y_staff")
        self.page.locator("#password").fill("testpass123")
        self.page.locator('form[action*="login"] button[type="submit"]').click()
        self.page.wait_for_load_state("networkidle")

    def _inject_axe(self):
        """Inject axe-core from CDN."""
        already = self.page.evaluate("() => typeof axe !== 'undefined'")
        if not already:
            self.page.add_script_tag(url=AXE_CDN)
            self.page.wait_for_function(
                "() => typeof axe !== 'undefined'", timeout=15000,
            )

    def _run_axe(self):
        """Run axe-core and return violations at critical/serious level."""
        self._inject_axe()
        results = self.page.evaluate(
            "async () => await axe.run(document, {})"
        )
        return [
            v for v in results.get("violations", [])
            if v["impact"] in ("critical", "serious")
        ]

    def _format_violations(self, violations, page_path):
        """Format violations for readable test output."""
        lines = [f"\nAxe violations on {page_path}:"]
        for v in violations:
            lines.append(f"  [{v['impact'].upper()}] {v['id']}: {v['help']}")
            for node in v.get("nodes", [])[:3]:
                target = node.get("target", ["?"])[0]
                lines.append(f"    - {target}")
        return "\n".join(lines)

    def test_axe_smoke_all_pages(self):
        """Run axe-core on key pages — fail on critical/serious violations."""
        logged_in = False
        all_violations = {}

        for path, description, requires_login in SMOKE_PAGES:
            if requires_login and not logged_in:
                self._login()
                logged_in = True

            self.page.goto(f"{self.live_server_url}{path}")
            self.page.wait_for_load_state("networkidle")

            violations = self._run_axe()
            if violations:
                all_violations[path] = violations

        if all_violations:
            report = []
            for path, violations in all_violations.items():
                report.append(self._format_violations(violations, path))
            self.fail(
                f"Axe-core found critical/serious accessibility violations "
                f"on {len(all_violations)} page(s):"
                + "\n".join(report)
            )
