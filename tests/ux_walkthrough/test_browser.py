"""Browser-based UX tests — colour contrast, focus management, responsive layout.

These tests complement the existing Django test-client walkthrough by using a
real browser (Playwright + headless Chromium) to check things that can only be
tested with rendered CSS and JavaScript execution.

Run with:  pytest tests/ux_walkthrough/test_browser.py -v
"""
import unittest

import pytest

# Check if Playwright is installed — used by @skipUnless on each class
HAS_PLAYWRIGHT = False
try:
    import playwright  # noqa: F401
    HAS_PLAYWRIGHT = True
except ImportError:
    pass

from .browser_base import BrowserTestBase


# ======================================================================
# 1. Colour Contrast
# ======================================================================


@unittest.skipUnless(HAS_PLAYWRIGHT, "Playwright not installed")
@pytest.mark.browser
class ColourContrastBrowserTest(BrowserTestBase):
    """Test colour contrast on key pages using axe-core.

    axe-core evaluates computed CSS styles to determine actual contrast
    ratios against WCAG 2.1 AA requirements (4.5:1 for normal text,
    3:1 for large text).
    """

    def _check_pages(self, pages, scheme_label="light"):
        """Run colour contrast checks on a list of pages.

        Parameters
        ----------
        pages : list of (username_or_None, path, label) tuples
        scheme_label : str — used in finding descriptions
        """
        current_user = None
        for username, path, label in pages:
            if username != current_user:
                if username:
                    if current_user is None:
                        self.login_via_browser(username)
                    else:
                        self.switch_user(username)
                current_user = username

            self.page.goto(self.live_url(path))
            self.page.wait_for_load_state("networkidle")

            try:
                results = self.run_colour_contrast_check()
            except Exception as exc:
                self.record_browser_finding(
                    "Colour Contrast", "info", path,
                    f"[{scheme_label}] {label}: Could not run axe-core",
                    detail=str(exc)[:200],
                )
                continue

            for violation in results.get("violations", []):
                impact = violation.get("impact", "unknown")
                severity = "critical" if impact in ("serious", "critical") else "warning"
                for node in violation.get("nodes", []):
                    target = ", ".join(node.get("target", []))
                    summary = (node.get("failureSummary") or "")[:200]
                    self.record_browser_finding(
                        "Colour Contrast", severity, path,
                        f"[{scheme_label}] {label}: Contrast violation "
                        f"({impact}) on `{target}`",
                        detail=summary,
                    )

    def test_colour_contrast_light_mode(self):
        """Run colour contrast audit on key pages in light mode."""
        pk = self.client_a.pk
        pages = [
            (None, "/auth/login/", "Login page"),
            ("staff", "/clients/", "Client list"),
            ("staff", f"/clients/{pk}/", "Client detail"),
            ("staff", f"/notes/client/{pk}/", "Notes timeline"),
            ("manager", f"/plans/client/{pk}/", "Plan view"),
            ("admin", "/admin/settings/", "Admin settings"),
            ("executive", "/clients/executive/", "Executive dashboard"),
        ]
        self._check_pages(pages, scheme_label="light")

    def test_colour_contrast_dark_mode(self):
        """Run colour contrast audit with dark colour scheme preference."""
        # Replace context with dark-mode context
        self.page.close()
        self._context.close()
        self._context = self._browser.new_context(color_scheme="dark")
        self.page = self._context.new_page()

        pk = self.client_a.pk
        pages = [
            (None, "/auth/login/", "Login page"),
            ("staff", "/clients/", "Client list"),
            ("staff", f"/clients/{pk}/", "Client detail"),
            ("staff", f"/notes/client/{pk}/", "Notes timeline"),
            ("admin", "/admin/settings/", "Admin settings"),
        ]
        self._check_pages(pages, scheme_label="dark")


# ======================================================================
# 2. Focus Management after HTMX Swaps
# ======================================================================


@unittest.skipUnless(HAS_PLAYWRIGHT, "Playwright not installed")
@pytest.mark.browser
class FocusManagementBrowserTest(BrowserTestBase):
    """Test that focus is managed correctly after HTMX content swaps.

    WCAG 2.4.3 (Focus Order) requires that when content changes
    dynamically, focus either stays in a logical place or moves to the
    new content. "Focus lost to <body>" is a failure.
    """

    def test_custom_fields_edit_toggle(self):
        """After clicking Edit on custom fields, focus should be inside the form."""
        pk = self.client_a.pk
        url = f"/clients/{pk}/"
        self.login_via_browser("staff")
        self.page.goto(self.live_url(url))
        self.page.wait_for_load_state("networkidle")

        edit_btn = self.page.locator(
            "[hx-get*='custom-fields/edit']"
        )
        if edit_btn.count() == 0:
            self.record_browser_finding(
                "Focus Management", "info", url,
                "Custom fields: No edit button found (may not have editable fields)",
            )
            return

        edit_btn.first.click()
        self.wait_for_htmx()

        if not self.focus_is_inside("#custom-fields-section"):
            focused = self.get_focused_element_info()
            self.record_browser_finding(
                "Focus Management", "warning", url,
                "Custom fields: Focus lost after switching to edit mode",
                detail=f"Focus on: {focused}",
            )

    def test_consent_form_toggle(self):
        """After clicking Update/Record Consent, focus should be inside the form."""
        pk = self.client_a.pk
        url = f"/clients/{pk}/"
        self.login_via_browser("staff")
        self.page.goto(self.live_url(url))
        self.page.wait_for_load_state("networkidle")

        # The consent section may be inside a collapsed <details> element;
        # expand it first so the button becomes visible.
        consent_details = self.page.locator("#consent-section details")
        if consent_details.count() > 0:
            summary = consent_details.first.locator("summary")
            if summary.count() > 0 and summary.first.is_visible():
                summary.first.click()
                self.page.wait_for_timeout(300)

        consent_btn = self.page.locator(
            "[hx-get*='consent/edit']"
        )
        if consent_btn.count() == 0:
            self.record_browser_finding(
                "Focus Management", "info", url,
                "Consent: No consent edit button found",
            )
            return

        consent_btn.first.click()
        self.wait_for_htmx()

        if not self.focus_is_inside("#consent-section"):
            focused = self.get_focused_element_info()
            self.record_browser_finding(
                "Focus Management", "warning", url,
                "Consent: Focus lost after opening consent edit form",
                detail=f"Focus on: {focused}",
            )

    def test_search_focus_stays_on_input(self):
        """After typing in search, focus should stay on the search input."""
        url = "/clients/search/"
        self.login_via_browser("staff")
        self.page.goto(self.live_url(url))
        self.page.wait_for_load_state("networkidle")

        search_input = self.page.locator("#client-search")
        if search_input.count() == 0:
            self.record_browser_finding(
                "Focus Management", "info", url,
                "Search: No #client-search input found",
            )
            return

        search_input.fill("Jane")
        self.wait_for_htmx()

        focused = self.get_focused_element_info()
        if not focused or focused.get("id") != "client-search":
            self.record_browser_finding(
                "Focus Management", "warning", url,
                "Search: Focus left the search input after results loaded",
                detail=f"Focus on: {focused}",
            )

    def test_plan_section_edit(self):
        """After clicking Edit on a plan section, focus should enter the edit form."""
        pk = self.client_a.pk
        url = f"/plans/client/{pk}/"
        self.login_via_browser("manager")
        self.page.goto(self.live_url(url))
        self.page.wait_for_load_state("networkidle")

        section_id = self.plan_section.pk
        edit_btn = self.page.locator(
            f"#section-{section_id} [hx-get*='section'][hx-get*='edit']"
        )
        if edit_btn.count() == 0:
            # Try a broader selector
            edit_btn = self.page.locator(
                f"#section-{section_id} button:has-text('Edit')"
            )
        if edit_btn.count() == 0:
            self.record_browser_finding(
                "Focus Management", "info", url,
                "Plan section: No edit button found",
            )
            return

        edit_btn.first.click()
        self.wait_for_htmx()

        if not self.focus_is_inside(f"#section-{section_id}"):
            focused = self.get_focused_element_info()
            self.record_browser_finding(
                "Focus Management", "warning", url,
                "Plan section: Focus lost after clicking Edit",
                detail=f"Focus on: {focused}",
            )

    def test_note_expansion_focus(self):
        """Note expansion should focus .note-detail-content (validates existing behaviour)."""
        pk = self.client_a.pk
        url = f"/notes/client/{pk}/"
        self.login_via_browser("staff")
        self.page.goto(self.live_url(url))
        self.page.wait_for_load_state("networkidle")

        note_id = self.note.pk
        note_link = self.page.locator(f"#note-{note_id} .note-card-link")
        if note_link.count() == 0:
            self.record_browser_finding(
                "Focus Management", "info", url,
                "Note expansion: No note card link found",
            )
            return

        note_link.first.click()
        self.wait_for_htmx()

        # Check that focus moved to .note-detail-content
        focused_on_detail = self.page.evaluate("""() => {
            const el = document.activeElement;
            return el && el.classList.contains('note-detail-content');
        }""")
        if not focused_on_detail:
            focused = self.get_focused_element_info()
            self.record_browser_finding(
                "Focus Management", "warning", url,
                "Note expansion: Focus did not move to .note-detail-content",
                detail=f"Focus on: {focused}",
            )


# ======================================================================
# 3. Responsive Layout
# ======================================================================


@unittest.skipUnless(HAS_PLAYWRIGHT, "Playwright not installed")
@pytest.mark.browser
class ResponsiveLayoutBrowserTest(BrowserTestBase):
    """Test responsive layout at mobile, tablet, and desktop viewpoints.

    Checks for horizontal overflow, touch target sizes, and navigation
    usability at different screen widths.
    """

    VIEWPORTS = [
        ("mobile", 375, 667),
        ("tablet", 768, 1024),
        ("desktop", 1280, 720),
    ]

    def test_no_horizontal_overflow(self):
        """No page should require horizontal scrolling at any breakpoint."""
        pk = self.client_a.pk
        pages = [
            (None, "/auth/login/", "Login"),
            ("staff", "/clients/", "Client list"),
            ("staff", f"/clients/{pk}/", "Client detail"),
            ("staff", f"/notes/client/{pk}/", "Notes timeline"),
            ("manager", f"/plans/client/{pk}/", "Plan view"),
        ]

        current_user = None
        for vp_name, width, height in self.VIEWPORTS:
            self.page.set_viewport_size({"width": width, "height": height})

            for username, path, label in pages:
                if username != current_user:
                    if username:
                        if current_user is None:
                            self.login_via_browser(username)
                        else:
                            self.switch_user(username)
                            self.page.set_viewport_size(
                                {"width": width, "height": height}
                            )
                    elif current_user is not None:
                        # Switching from logged-in to anonymous: new context
                        self.page.close()
                        self._context.close()
                        self._context = self._browser.new_context()
                        self.page = self._context.new_page()
                        self.page.set_viewport_size(
                            {"width": width, "height": height}
                        )
                    current_user = username

                self.page.goto(self.live_url(path))
                self.page.wait_for_load_state("networkidle")

                has_overflow = self.page.evaluate("""() =>
                    document.documentElement.scrollWidth >
                    document.documentElement.clientWidth
                """)
                if has_overflow:
                    scroll_w = self.page.evaluate(
                        "() => document.documentElement.scrollWidth"
                    )
                    client_w = self.page.evaluate(
                        "() => document.documentElement.clientWidth"
                    )
                    self.record_browser_finding(
                        "Responsive Layout", "warning", path,
                        f"[{vp_name}] {label}: Horizontal overflow detected",
                        detail=f"scrollWidth={scroll_w}, clientWidth={client_w} "
                               f"at {width}x{height}",
                    )

    def test_touch_targets_mobile(self):
        """Interactive elements should be at least 44x44px on mobile (WCAG 2.5.5)."""
        self.page.set_viewport_size({"width": 375, "height": 667})
        self.login_via_browser("staff")

        pk = self.client_a.pk
        pages = [
            (f"/clients/{pk}/", "Client detail"),
            ("/clients/", "Client list"),
        ]

        for path, label in pages:
            self.page.goto(self.live_url(path))
            self.page.wait_for_load_state("networkidle")

            small_targets = self.page.evaluate("""() => {
                const MIN = 44;
                const problems = [];
                const els = document.querySelectorAll(
                    'a, button, input:not([type="hidden"]), select, textarea, [role="button"]'
                );
                els.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) return;
                    const style = getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') return;
                    // Skip elements scrolled off screen
                    if (rect.bottom < 0 || rect.top > window.innerHeight) return;
                    if (rect.width < MIN || rect.height < MIN) {
                        problems.push({
                            tag: el.tagName.toLowerCase(),
                            text: el.textContent.substring(0, 40).trim(),
                            w: Math.round(rect.width),
                            h: Math.round(rect.height),
                        });
                    }
                });
                return problems;
            }""")

            for target in small_targets:
                self.record_browser_finding(
                    "Responsive Layout", "info", path,
                    f"[mobile] {label}: Touch target too small — "
                    f"<{target['tag']}> \"{target['text'][:30]}\" "
                    f"is {target['w']}x{target['h']}px (min 44x44)",
                )

    def test_navigation_usable_mobile(self):
        """On mobile, the navigation should be accessible."""
        self.page.set_viewport_size({"width": 375, "height": 667})
        self.login_via_browser("staff")
        self.page.goto(self.live_url("/clients/"))
        self.page.wait_for_load_state("networkidle")

        # Check if nav element is present
        nav = self.page.locator("nav")
        if nav.count() == 0:
            self.record_browser_finding(
                "Responsive Layout", "warning", "/clients/",
                "[mobile] No <nav> element found",
            )
            return

        # Check if a toggle button exists for mobile nav
        toggle = self.page.locator("[aria-controls*='nav'], .nav-toggle, #nav-toggle, [data-nav-toggle]")
        if toggle.count() > 0 and toggle.first.is_visible():
            # Toggle exists — click it and verify menu opens
            toggle.first.click()
            self.page.wait_for_timeout(400)
            # Check that some nav links became visible
            nav_links = self.page.locator("nav a")
            visible_count = 0
            for i in range(min(nav_links.count(), 5)):
                if nav_links.nth(i).is_visible():
                    visible_count += 1
            if visible_count == 0:
                self.record_browser_finding(
                    "Responsive Layout", "warning", "/clients/",
                    "[mobile] Navigation toggle exists but menu links not visible after click",
                )
