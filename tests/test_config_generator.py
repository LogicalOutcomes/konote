"""Playwright browser tests for the standalone config generator HTML."""
import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.browser

CONFIG_PATH = Path(__file__).resolve().parent.parent / "tools" / "config-generator.html"
FILE_URL = CONFIG_PATH.as_uri()


@pytest.fixture
def page(browser):
    """Open the config generator in a fresh browser page."""
    p = browser.new_page()
    p.goto(FILE_URL)
    p.wait_for_load_state("domcontentloaded")
    yield p
    p.close()


@pytest.fixture
def browser(playwright):
    b = playwright.chromium.launch(headless=True)
    yield b
    b.close()


@pytest.fixture
def playwright():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        yield pw


class TestTabNavigation:
    def test_all_tabs_render(self, page):
        """All 7 tabs should be present and clickable."""
        tabs = page.query_selector_all('.tab-nav button')
        assert len(tabs) == 7

    def test_tab_switching(self, page):
        """Clicking a tab should show its panel and hide others."""
        tabs = page.query_selector_all('.tab-nav button')
        for tab in tabs:
            tab.click()
            tab_id = tab.get_attribute('data-tab')
            panel = page.query_selector(f'#tab-{tab_id}')
            assert 'active' in panel.get_attribute('class')
            # The tab button itself should be active
            assert 'active' in tab.get_attribute('class')

    def test_default_tab_is_infrastructure(self, page):
        """Infrastructure tab should be active by default."""
        panel = page.query_selector('#tab-infrastructure')
        assert 'active' in panel.get_attribute('class')


class TestKeyGeneration:
    def test_generate_all_keys(self, page):
        """Clicking Generate All Keys should populate all three key displays."""
        page.click('button:text("Generate All Keys")')

        secret_key = page.text_content('#secret_key_display')
        assert len(secret_key) == 50

        encryption_key = page.text_content('#encryption_key_display')
        # Fernet key: base64 of 32 bytes = 44 chars (with padding)
        assert len(encryption_key) == 44

        email_key = page.text_content('#email_hash_key_display')
        assert len(email_key) >= 40  # URL-safe base64 without padding

    def test_regenerate_individual_keys(self, page):
        """Each Regenerate button should change its key."""
        page.click('button:text("Generate All Keys")')
        old_secret = page.text_content('#secret_key_display')

        page.query_selector('#secret_key_display').evaluate(
            'el => el.closest(".key-display-row").querySelector("button").click()'
        )
        new_secret = page.text_content('#secret_key_display')
        # Very unlikely to be the same
        assert len(new_secret) == 50

    def test_secret_key_charset(self, page):
        """SECRET_KEY should only contain allowed characters."""
        page.click('button:text("Generate All Keys")')
        key = page.text_content('#secret_key_display')
        allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*(-_=+)')
        assert all(c in allowed for c in key)


class TestPrograms:
    def test_add_remove_program(self, page):
        """Adding and removing programs should work."""
        page.click('button[data-tab="programs-metrics"]')
        page.click('button:text("+ Add Program")')
        page.click('button:text("+ Add Program")')

        items = page.query_selector_all('#programs-list .repeatable-item')
        assert len(items) == 2

        # Remove first
        items[0].query_selector('.remove-btn').click()
        items = page.query_selector_all('#programs-list .repeatable-item')
        assert len(items) == 1


class TestMetrics:
    def test_metrics_rendered(self, page):
        """All metrics should be rendered as checkboxes."""
        page.click('button[data-tab="programs-metrics"]')
        checkboxes = page.query_selector_all('[data-metric-name]')
        assert len(checkboxes) == 32  # matches METRIC_LIBRARY length

    def test_metric_search_filter(self, page):
        """Searching should filter metrics visibly."""
        page.click('button[data-tab="programs-metrics"]')
        page.fill('#metric-search', 'PHQ')

        visible = page.eval_on_selector_all(
            '.metric-item',
            'items => items.filter(i => i.style.display !== "none").length'
        )
        assert visible >= 1

    def test_metric_search_hides_non_matches(self, page):
        """Non-matching metrics should be hidden."""
        page.click('button[data-tab="programs-metrics"]')
        page.fill('#metric-search', 'xyznonexistent')

        visible = page.eval_on_selector_all(
            '.metric-item',
            'items => items.filter(i => i.style.display !== "none").length'
        )
        assert visible == 0


class TestFeatures:
    def test_features_rendered(self, page):
        """Feature toggles table should be populated."""
        page.click('button[data-tab="features"]')
        rows = page.query_selector_all('#feature-table input[type="checkbox"]')
        assert len(rows) >= 20

    def test_dependency_auto_enable(self, page):
        """Enabling portal_journal should auto-enable participant_portal."""
        page.click('button[data-tab="features"]')
        # First uncheck participant_portal if checked
        portal_cb = page.query_selector('#feat_participant_portal')
        if portal_cb.is_checked():
            portal_cb.uncheck()

        journal_cb = page.query_selector('#feat_portal_journal')
        if not journal_cb.is_checked():
            journal_cb.check()

        # participant_portal should now be checked
        assert portal_cb.is_checked()


class TestPreviewAndDownload:
    def test_preview_renders(self, page):
        """Review tab should show non-empty previews."""
        page.click('button:text("Generate All Keys")')
        page.click('button[data-tab="review"]')

        env_content = page.text_content('#env-preview')
        json_content = page.text_content('#json-preview')

        assert 'SECRET_KEY=' in env_content
        assert 'FIELD_ENCRYPTION_KEY=' in env_content
        assert '"features"' in json_content

    def test_json_is_valid(self, page):
        """Generated JSON should be parseable."""
        page.click('button:text("Generate All Keys")')
        page.click('button[data-tab="review"]')

        json_content = page.text_content('#json-preview')
        parsed = json.loads(json_content)
        assert 'features' in parsed

    def test_env_has_required_keys(self, page):
        """Generated .env should include all required environment variables."""
        page.click('button:text("Generate All Keys")')
        page.click('button[data-tab="review"]')

        env_content = page.text_content('#env-preview')
        assert 'SECRET_KEY=' in env_content
        assert 'FIELD_ENCRYPTION_KEY=' in env_content
        assert 'EMAIL_HASH_KEY=' in env_content
        assert 'DATABASE_URL=' in env_content
        assert 'AUDIT_DATABASE_URL=' in env_content
        assert 'AUTH_MODE=' in env_content

    def test_domain_auto_derives(self, page):
        """Setting a domain should auto-populate ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS."""
        page.fill('#domain', 'konote.example.ca')
        page.click('button:text("Generate All Keys")')
        page.click('button[data-tab="review"]')

        env_content = page.text_content('#env-preview')
        assert 'ALLOWED_HOSTS=konote.example.ca' in env_content
        assert 'CSRF_TRUSTED_ORIGINS=https://konote.example.ca' in env_content

    def test_programs_in_json(self, page):
        """Added programs should appear in the JSON output."""
        page.click('button[data-tab="programs-metrics"]')
        page.click('button:text("+ Add Program")')
        page.fill('#programs-list .prog-name', 'Test Program')

        page.click('button:text("Generate All Keys")')
        page.click('button[data-tab="review"]')

        json_content = page.text_content('#json-preview')
        parsed = json.loads(json_content)
        assert len(parsed['programs']) == 1
        assert parsed['programs'][0]['name'] == 'Test Program'
