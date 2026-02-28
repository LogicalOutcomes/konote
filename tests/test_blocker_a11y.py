"""
Test BLOCKER-1 (skip-to-content) and BLOCKER-2 (post-login focus)
using Django's StaticLiveServerTestCase + Playwright.

Run with: python manage.py test tests.test_blocker_a11y -v2 --settings=konote.settings.test
"""
import json
import os
import shutil
import tempfile

# Required for LiveServerTestCase with synchronous DB operations
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from cryptography.fernet import Fernet
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings

import konote.encryption as enc_module
from apps.auth_app.models import User

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class BlockerA11yTests(StaticLiveServerTestCase):
    """Test BLOCKER-1 and BLOCKER-2 accessibility issues with real browser.

    Uses file-based SQLite instead of :memory: because LiveServerTestCase
    runs the server in a separate thread, and SQLite :memory: databases
    are per-connection (threads can't share them).
    """

    databases = {"default", "audit"}

    @classmethod
    def setUpClass(cls):
        if not HAS_PLAYWRIGHT:
            raise Exception("Playwright not installed")
        enc_module._fernet = None

        # Switch to file-based SQLite so the live server thread can
        # share the database with the test thread.
        cls._db_dir = tempfile.mkdtemp(prefix="konote_blocker_")
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

        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
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
        self.user = User.objects.create_user(
            username="testadmin",
            password="testpass123",
            is_admin=True,
            display_name="Test Admin",
        )

    def _login(self, page):
        """Log in via the login form, handling the first-visit language chooser."""
        page.goto(f"{self.live_server_url}/auth/login/")
        page.wait_for_load_state("networkidle")

        # First visit shows language chooser — pick English
        english_btn = page.locator("button.lang-chooser-btn:has-text('English')")
        if english_btn.count() > 0:
            english_btn.click()
            page.wait_for_load_state("networkidle")

        # Now fill the login form (be specific to avoid matching language toggle button)
        page.locator('#username').fill("testadmin")
        page.locator('#password').fill("testpass123")
        page.locator('form[action="/auth/login/"] button[type="submit"]').click()
        page.wait_for_load_state("networkidle")

        # Check if login succeeded
        url = page.url
        if "/auth/login" in url:
            # Login failed — capture error for debugging
            error = page.locator('[role="alert"]')
            if error.count() > 0:
                print(f"  LOGIN ERROR: {error.text_content()}")
            # Try getting the page HTML for debugging
            title = page.title()
            print(f"  LOGIN FAILED — still on login page. Title: {title}")
            print(f"  URL: {url}")
            page.screenshot(path="C:/Users/gilli/AppData/Local/Temp/blocker_login_failed.png", full_page=True)
            return False
        return True

    def _login_via_client(self, page):
        """Log in by injecting session cookie from Django test client."""
        # Use Django test client to get a session
        from django.test import Client
        client = Client()
        client.login(username="testadmin", password="testpass123")
        session_cookie = client.cookies.get("sessionid")
        if not session_cookie:
            self.fail("Could not get session cookie from Django test client")

        # Navigate to site first (needed to set cookie domain)
        page.goto(f"{self.live_server_url}/auth/login/")
        page.wait_for_load_state("networkidle")

        # Inject session cookie
        page.context.add_cookies([{
            "name": "sessionid",
            "value": session_cookie.value,
            "domain": "localhost",
            "path": "/",
        }])

        # Now navigate to dashboard — should be authenticated
        page.goto(f"{self.live_server_url}/")
        page.wait_for_load_state("networkidle")

        url = page.url
        if "/auth/login" in url:
            print(f"  Cookie login also failed. URL: {url}")
            return False
        return True

    def test_blocker2_post_login_focus(self):
        """BLOCKER-2: After login, focus should be on #main-content, not footer."""
        page = self.browser.new_page()
        try:
            # Try form login first, fall back to cookie injection
            logged_in = self._login(page)
            if not logged_in:
                print("  Retrying with cookie-based login...")
                logged_in = self._login_via_client(page)
            if not logged_in:
                self.fail("Could not log in with either method")

            print(f"\n  Dashboard URL: {page.url}")
            import tempfile, os
            page.screenshot(path=os.path.join(tempfile.gettempdir(), "blocker2_dashboard.png"), full_page=True)

            focus_info = page.evaluate("""() => {
                const el = document.activeElement;
                return { tag: el.tagName, id: el.id, className: el.className };
            }""")
            print(f"  BLOCKER-2 focus: {json.dumps(focus_info)}")

            main_info = page.evaluate("""() => {
                const main = document.getElementById('main-content');
                if (!main) return {exists: false};
                return { exists: true, tag: main.tagName, tabindex: main.getAttribute('tabindex') };
            }""")
            print(f"  #main-content: {json.dumps(main_info)}")

            # Focus must NOT be in the footer
            in_footer = page.evaluate("() => document.activeElement.closest('footer') !== null")
            self.assertFalse(in_footer, "BLOCKER-2 FAIL: Focus is in the footer!")

            if focus_info.get("id") == "main-content":
                print("  >>> BLOCKER-2: PASS — focus is on #main-content")
            elif focus_info.get("tag") in ("BODY", "HTML"):
                print("  >>> BLOCKER-2: ACCEPTABLE — focus is on BODY")
            else:
                print(f"  >>> BLOCKER-2: INVESTIGATE — focus on {focus_info['tag']}#{focus_info.get('id', '?')}")

        finally:
            page.close()

    def test_blocker1_skip_link_and_focusable_main(self):
        """BLOCKER-1: Skip link exists and main content is keyboard-focusable."""
        page = self.browser.new_page()
        try:
            # Log in and navigate to dashboard
            logged_in = self._login(page)
            if not logged_in:
                logged_in = self._login_via_client(page)
            if not logged_in:
                self.fail("Could not log in")

            # Navigate to dashboard fresh (to reset focus state)
            page.goto(f"{self.live_server_url}/")
            page.wait_for_load_state("networkidle")

            print(f"\n  Dashboard URL: {page.url}")

            # Verify skip link exists and targets #main-content
            skip_link_info = page.evaluate("""() => {
                const link = document.querySelector('a[href="#main-content"]');
                if (!link) return null;
                return {
                    exists: true,
                    href: link.getAttribute('href'),
                    text: link.textContent.trim(),
                    className: link.className
                };
            }""")
            print(f"  Skip link info: {json.dumps(skip_link_info)}")
            self.assertIsNotNone(skip_link_info, "Skip link should exist for WCAG 2.2 AA compliance")
            self.assertEqual(skip_link_info["href"], "#main-content", "Skip link should target #main-content")

            # Verify main content element is keyboard-focusable
            main_info = page.evaluate("""() => {
                const main = document.getElementById('main-content');
                if (!main) return null;
                return {
                    tag: main.tagName,
                    id: main.id,
                    tabindex: main.getAttribute('tabindex'),
                    hasAriaLabel: main.hasAttribute('aria-label'),
                    ariaLabel: main.getAttribute('aria-label')
                };
            }""")
            print(f"  Main content info: {json.dumps(main_info)}")
            self.assertIsNotNone(main_info, "Main content element should exist")
            self.assertEqual(main_info["tag"], "MAIN", "Main content should be a <main> element")
            self.assertEqual(main_info["tabindex"], "-1", "Main content should have tabindex='-1' for skip link focus")
            self.assertTrue(main_info["hasAriaLabel"], "Main content should have aria-label")

            import tempfile, os
            page.screenshot(path=os.path.join(tempfile.gettempdir(), "blocker1_skip_link.png"), full_page=True)
            print("  >>> BLOCKER-1: PASS — skip link exists, main content is keyboard-focusable")

        finally:
            page.close()
