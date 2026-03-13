"""Collected browser smoke tests for the CSP-safe config generator."""

import json
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


def test_feature_dependency_auto_enables_parent(page):
    """Checking a dependent feature should re-enable its required parent."""
    page.click('button[data-tab="features"]')

    portal_cb = page.locator("#feat_participant_portal")
    journal_cb = page.locator("#feat_portal_journal")

    if journal_cb.is_checked():
        journal_cb.uncheck()
    if portal_cb.is_checked():
        portal_cb.uncheck()

    journal_cb.check()

    assert portal_cb.is_checked()


def test_added_program_appears_in_review_json(page):
    """Programs added through the UI should appear in the generated JSON preview."""
    page.click('button:text("Generate All Keys")')
    page.click('button[data-tab="programs-metrics"]')
    page.click('button:text("+ Add Program")')
    page.fill("#programs-list .prog-name", "Test Program")

    page.click('button[data-tab="review"]')

    parsed = json.loads(page.text_content("#json-preview"))
    assert parsed["programs"][0]["name"] == "Test Program"