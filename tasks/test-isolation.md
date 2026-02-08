# Test Isolation for QA Scenario Runner (QA-ISO1)

## What This Is

Each QA scenario (the persona-based tests in `konote-qa-scenarios`) must run in a completely fresh browser state. Right now, the test runner reuses browser context between scenarios, which lets state leak from one test into the next.

## Why It Matters

During the first round of QA evaluations (2026-02-07), we found a **language carryover bug**: a French-language persona (DS2, Jean-Luc) ran before English personas, and the French interface appeared for English users in subsequent scenarios. This happened because the browser kept the language cookie from the French session.

This made scores unreliable. Several scenario steps had to be tagged "Low confidence" because we couldn't tell whether the problem was a real UX issue or a test infrastructure artifact. Fixing this means every score we report can be trusted.

## What Needs to Change

### 1. Fresh BrowserContext per scenario

Use Playwright's `browser.new_context()` for each scenario instead of reusing pages. This ensures no cookies, localStorage, or session data carries over.

```python
# In conftest.py or browser_base.py
@pytest.fixture
def scenario_context(browser):
    context = browser.new_context(
        locale=persona_locale,        # e.g., "en-CA" or "fr-CA"
        extra_http_headers={"Accept-Language": persona_locale},
    )
    yield context
    context.close()
```

### 2. Explicit locale override

Set `Accept-Language` header and locale in context options to match each persona's language. Don't rely on cookies from previous runs or the browser default.

- DS2 (Jean-Luc): `fr-CA`
- All others: `en-CA`
- Use the persona YAML's `test_user.language` field as the source of truth

### 3. Login as fixture, not step

Move login out of scenario steps and into a pytest fixture. Right now, step 1 of most scenarios is "navigate to login page and log in." This should happen automatically before the scenario starts.

Benefits:
- Step 1 of each scenario is the actual task, not boilerplate
- Login time is excluded from scenario timing measurements
- Login failures are reported as fixture errors, not scenario failures

```python
@pytest.fixture
def logged_in_page(scenario_context, persona):
    page = scenario_context.new_page()
    page.goto("/auth/login/")
    page.fill("#id_username", persona["test_user"]["username"])
    page.fill("#id_password", "testpass123")
    page.click("button[type='submit']")
    page.wait_for_url("**/dashboard/**")
    yield page
```

### 4. Prerequisite validation

Before running a scenario that depends on existing data (e.g., "add a note to client X"), check that the prerequisite data actually exists. Fail fast with a clear message if not.

Example:
- SCN-015 ("add progress note") requires client "Maria Santos" to exist
- If the client doesn't exist (because a setup scenario failed or wasn't run), the scenario should fail immediately with: `PREREQUISITE MISSING: Client 'Maria Santos' not found. Run SCN-005 first or seed demo data.`

### 5. Demo data cleanup

After each scenario, delete any records created during the test. Options:
- **Transaction rollback** (preferred): wrap each scenario in a database transaction and roll back at the end
- **Explicit cleanup**: delete created records by ID in a teardown fixture
- **Known demo data**: use `is_demo=True` records that can be reset to a known state

## Success Criteria

- [ ] Every scenario passes when run alone (`pytest tests/ux_walkthrough/test_scn_015.py`)
- [ ] Every scenario passes when run as part of the full suite in any order (`pytest tests/ux_walkthrough/ --randomly-seed=12345`)
- [ ] Language never carries over between scenarios (no "Low confidence" tags from test infrastructure)
- [ ] Login time is excluded from scenario timing measurements
- [ ] A missing prerequisite produces a clear error message, not a confusing test failure

## Files Likely Affected

| File | Change |
|------|--------|
| `tests/ux_walkthrough/browser_base.py` | New context per scenario, locale options |
| `tests/ux_walkthrough/conftest.py` | Login fixture, cleanup fixture, prerequisite checks |
| `tests/ux_walkthrough/base.py` | User creation and role assignment (may need PM user) |
| `konote-qa-scenarios/scenarios/**/*.yaml` | Remove login steps from scenario definitions |

## Reference

- QA scenarios repo: `konote-qa-scenarios`
- Round 1 evaluation report: `konote-qa-scenarios/reports/`
- Language carryover bug: fixed at app level (BUG-4), but test isolation prevents recurrence
- Persona YAML files: `konote-qa-scenarios/personas/`
