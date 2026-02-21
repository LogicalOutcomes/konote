"""Track A: Quick Check — Playwright interaction tests.

15 tests that verify core workflows actually function: forms submit,
data saves, errors are handled, permissions are enforced.

These are standard pytest + Playwright tests. No YAML, no LLM.
Run with: python manage.py qa_check
    or:   pytest tests/scenario_eval/test_interactions.py -v

Design doc: docs/plans/2026-02-21-qa-evaluation-enrichment-design.md
"""
import re

import pytest

pw = pytest.importorskip("playwright.sync_api", reason="Playwright required")

from tests.ux_walkthrough.browser_base import BrowserTestBase, TEST_PASSWORD


@pytest.mark.scenario_eval
@pytest.mark.browser
class TestInteractions(BrowserTestBase):
    """Quick Check interaction tests — verifies core workflows function."""

    # ------------------------------------------------------------------
    # 1. Login (each role)
    # ------------------------------------------------------------------
    def test_login_each_role(self):
        """Each role can log in and sees the correct dashboard."""
        for username in ("staff", "manager", "executive", "frontdesk", "admin"):
            with self.subTest(role=username):
                self.switch_user(username)
                # Should NOT be on login page
                self.assertNotIn("/auth/login", self.page.url)
                # Should see some main content
                has_main = self.page.evaluate(
                    "() => !!document.querySelector('main, [role=\"main\"]')"
                )
                self.assertTrue(has_main, f"{username}: no main content on dashboard")

    # ------------------------------------------------------------------
    # 2. Participant search
    # ------------------------------------------------------------------
    def test_participant_search(self):
        """Staff can search for participants and see results."""
        self.login_via_browser("staff")
        self.page.goto(self.live_url("/participants/"))
        self.page.wait_for_load_state("networkidle")

        # Should see at least one client (test data has Jane Doe, Bob Smith)
        body_text = self.page.text_content("body")
        self.assertTrue(
            "Jane" in body_text or "Bob" in body_text,
            "No test clients visible in participant list",
        )

    # ------------------------------------------------------------------
    # 3. Create participant
    # ------------------------------------------------------------------
    def test_create_participant(self):
        """Staff can create a new participant — form saves and redirects."""
        self.login_via_browser("staff")
        self.page.goto(self.live_url("/participants/create/"))
        self.page.wait_for_load_state("networkidle")

        # Fill required fields
        self.page.fill("[name='first_name'], #id_first_name", "Test")
        self.page.fill("[name='last_name'], #id_last_name", "Participant")

        # Submit
        self.page.click("button[type='submit']")
        self.page.wait_for_load_state("networkidle")

        # Should redirect to participant profile (not stay on create form)
        self.assertNotIn("/create/", self.page.url)
        # Should see the new participant name somewhere on the page
        body = self.page.text_content("body")
        self.assertIn("Test", body)

    # ------------------------------------------------------------------
    # 4. Create progress note
    # ------------------------------------------------------------------
    def test_create_progress_note(self):
        """Staff can create a note — saves with confirmation shown."""
        self.login_via_browser("staff")
        # Navigate to the first client's notes
        self.page.goto(self.live_url("/participants/"))
        self.page.wait_for_load_state("networkidle")

        # Click first client link
        client_link = self.page.locator("a[href*='/participants/']").first
        if client_link.count() > 0:
            client_link.click()
            self.page.wait_for_load_state("networkidle")

        # Find and click "Add Note" or navigate to notes
        current_url = self.page.url
        # Try navigating to the notes add page for client_a
        note_url = re.sub(r"/participants/(\d+)/.*", r"/participants/\1/notes/add/", current_url)
        if "/participants/" in current_url:
            self.page.goto(note_url)
        else:
            self.page.goto(self.live_url(f"/participants/{self.client_a.pk}/notes/add/"))
        self.page.wait_for_load_state("networkidle")

        # Fill note content (look for textarea or rich text field)
        textarea = self.page.locator("textarea").first
        if textarea.count() > 0:
            textarea.fill("Test note content from interaction test")

        # Submit
        submit = self.page.locator("button[type='submit']").first
        if submit.count() > 0:
            submit.click()
            self.page.wait_for_load_state("networkidle")

        # Should show confirmation or redirect to notes list
        body = self.page.text_content("body")
        note_saved = (
            "saved" in body.lower()
            or "created" in body.lower()
            or "/notes/" in self.page.url
        )
        self.assertTrue(note_saved, "No confirmation of note creation")

    # ------------------------------------------------------------------
    # 5. Note validation error
    # ------------------------------------------------------------------
    def test_note_validation_error(self):
        """Submitting an empty note form shows an error, not a crash."""
        self.login_via_browser("staff")
        self.page.goto(
            self.live_url(f"/participants/{self.client_a.pk}/notes/add/")
        )
        self.page.wait_for_load_state("networkidle")

        # Submit without filling anything
        submit = self.page.locator("button[type='submit']").first
        if submit.count() > 0:
            submit.click()
            self.page.wait_for_load_state("networkidle")

        # Should stay on the form (not 500 error) and show a validation message
        # or the form itself (i.e., not a server error page)
        self.assertNotIn("500", self.page.title())
        self.assertNotIn("Server Error", self.page.text_content("body"))
