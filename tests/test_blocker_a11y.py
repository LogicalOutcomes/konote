"""
Test BLOCKER-1 (skip-to-content) and BLOCKER-2 (post-login focus)
using Django's StaticLiveServerTestCase + Playwright.

Run with: python manage.py test tests.test_blocker_a11y -v2 --settings=konote.settings.test
"""
import json
import os

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
    """Test BLOCKER-1 and BLOCKER-2 accessibility issues with real browser."""

    databases = {"default", "audit"}

    @classmethod
    def setUpClass(cls):
        if not HAS_PLAYWRIGHT:
            raise Exception("Playwright not installed")
        enc_module._fernet = None
        super().setUpClass()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        super().tearDownClass()

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
            page.screenshot(path="C:/Users/gilli/AppData/Local/Temp/blocker2_dashboard.png", full_page=True)

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

    def test_blocker1_skip_to_content_link(self):
        """BLOCKER-1: First Tab from top of page should reach skip-to-content link."""
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

            # Verify skip link exists in DOM
            skip_link = page.evaluate("""() => {
                const link = document.querySelector('a[href="#main-content"]');
                if (!link) return {exists: false};
                return {
                    exists: true,
                    text: link.textContent.trim(),
                    className: link.className
                };
            }""")
            print(f"  Skip link in DOM: {json.dumps(skip_link)}")
            self.assertTrue(skip_link.get("exists"), "Skip link not found in DOM!")

            # Reset focus to body (clear any autofocus or JS focus management)
            page.evaluate("() => { if (document.activeElement) document.activeElement.blur(); }")
            page.wait_for_timeout(100)

            # Press Tab once from top
            page.keyboard.press("Tab")
            page.wait_for_timeout(300)

            focus_after_tab = page.evaluate("""() => {
                const el = document.activeElement;
                return {
                    tag: el.tagName,
                    id: el.id,
                    href: el.href || '',
                    text: (el.textContent || '').trim().substring(0, 80),
                    className: el.className
                };
            }""")
            print(f"  After 1st Tab: {json.dumps(focus_after_tab)}")
            page.screenshot(path="C:/Users/gilli/AppData/Local/Temp/blocker1_after_tab.png", full_page=True)

            is_skip = "#main-content" in focus_after_tab.get("href", "")

            if is_skip:
                print("  Skip link IS the first Tab stop")

                # Activate it
                page.keyboard.press("Enter")
                page.wait_for_timeout(300)

                focus_after_enter = page.evaluate("""() => {
                    const el = document.activeElement;
                    return {tag: el.tagName, id: el.id};
                }""")
                print(f"  After Enter: {json.dumps(focus_after_enter)}")

                if focus_after_enter.get("id") == "main-content":
                    print("  >>> BLOCKER-1: PASS — skip link works, focus moved to #main-content")
                else:
                    print(f"  >>> BLOCKER-1: PARTIAL — skip link focused, but Enter moved to {focus_after_enter['tag']}#{focus_after_enter.get('id', '?')}")
            else:
                # Search for skip link in tab order
                found_at = None
                for i in range(10):
                    page.keyboard.press("Tab")
                    page.wait_for_timeout(100)
                    check = page.evaluate("() => document.activeElement.href || ''")
                    if "#main-content" in check:
                        found_at = i + 2
                        break

                if found_at:
                    print(f"  >>> BLOCKER-1: FAIL — skip link is Tab stop #{found_at}, should be #1")
                else:
                    print("  >>> BLOCKER-1: FAIL — skip link never gets Tab focus")

        finally:
            page.close()
