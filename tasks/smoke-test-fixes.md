# Smoke Test Fixes: CAL-001 Preflight + Known Bugs

**Created:** 2026-02-11
**Context:** Phase 1 smoke test gate revealed 3 blocked scenarios. Two were fixed (missing `persona:` fields in SCN-010 and SCN-035 — committed to konote-qa-scenarios). One remains: CAL-001 preflight failure. Plus 4 known bugs from Round 3 still block the full QA suite.

---

## Item 3: CAL-001 Preflight Failure (Executive Can't Pass Client List Check)

### What Happens

The smoke test for CAL-001 (E1 / executive persona, username `"executive"`) passes the test but produces a BLOCKED result because the **preflight check** fails with:

```
Preflight FAILED for E1 in CAL-001: No clients visible in client list
```

### Root Cause

The preflight check in `tests/scenario_eval/scenario_runner.py` (lines 576–651, method `_run_preflight`) runs **before** scenario steps execute. It does 5 checks:

1. Not on login page — PASSES
2. User badge visible — PASSES
3. Correct language — PASSES
4. Dashboard main content has text > 10 chars — PASSES
5. **Navigate to `/clients/` and check for `table tbody tr`** — FAILS

The executive user (username `"executive"`) has `UserProgramRole(program_a, role="executive", status="active")`. The `_get_accessible_clients()` function in `apps/clients/views.py:50-70` queries by `UserProgramRole.objects.filter(user=user, status="active")` which DOES include the executive role. Clients enrolled in program_a SHOULD appear.

However, CAL-001's actual scenario navigates to `/clients/executive/` (the executive dashboard at `apps/clients/urls.py:108`), not `/clients/`. The preflight is checking the wrong page for this persona — the executive has their own dashboard that shows aggregate stats, not a client list table.

### What Needs to Happen

Either:

**Option A (recommended):** Make the preflight smarter about executive personas. If the persona's role is "executive", skip the client list check (step 5) or navigate to `/clients/executive/` instead. The executive dashboard renders aggregate stats, not individual client rows, so the `table tbody tr` selector won't match anyway — check for a different element.

**Option B:** Add a `preflight_skip` or `preflight_url` field to scenarios or personas so the runner knows which page to check for each role.

### Key Files

| File | Location | What to Check |
|------|----------|---------------|
| Preflight logic | `tests/scenario_eval/scenario_runner.py:576-651` | `_run_preflight()` method |
| Executive dashboard view | `apps/clients/urls.py:14-102` | `executive_dashboard()` — renders to `clients/executive_dashboard.html` |
| Executive dashboard template | `templates/clients/executive_dashboard.html` | What elements are on the page (for the preflight selector) |
| Client list view | `apps/clients/views.py:101-183` | `client_list()` — the view the preflight currently checks |
| Accessible clients | `apps/clients/views.py:50-70` | `_get_accessible_clients()` — confirms executive role IS included |
| Persona data | `konote-qa-scenarios/personas/executive.yaml` | E1 test_user: username "executive", role "executive" |
| CAL-001 scenario | `konote-qa-scenarios/scenarios/calibration/CAL-001-good-page.yaml` | Steps navigate to `/clients/executive/` |

### Additional Context

20 other scenarios also lack the `persona:` field (they only have `actors:`). The full list is in the "Bulk Fix" section below. These should also be fixed before the full Round 4 evaluation, but they aren't blocking the smoke test gate.

---

## Item 4: Known Bugs Blocking Full QA Suite (Round 4)

These 4 bugs were identified in Round 3 (2026-02-09) and are tracked in `konote-qa-scenarios/TODO.md` as Phase 2A tasks.

### BUG-9: Language Persistence Lost Mid-Session (COMPLIANCE CRITICAL)

**Impact:** Blocks SCN-026, SCN-040 bilingual workflows. Official Languages Act / PHIPA s. 30(2) compliance issue.

**Symptom:** French-speaking personas (DS2/staff_fr, R2-FR/frontdesk_fr, PM2-FR/manager_fr) start on a French dashboard, but when they navigate to a form page (e.g. `/clients/create/`), the page reverts to English. The `<html lang="...">` attribute flips from `fr` to `en`.

**Evidence from smoke test:** SCN-040 step 2 scored language 1/5 with message: `Document lang 'en' does not match expected 'fr'`. The dashboard (step 1) was correctly French (lang=fr, score 5/5).

**Where to look:**
- Django's `LocaleMiddleware` or the app's language-switching mechanism
- Check if the user's `preferred_language` field is being honoured on every request, not just the first
- Check if `django.utils.translation.activate()` is being called consistently
- Check session-based vs cookie-based language persistence
- The login view at `apps/auth_app/views.py` sets language on login — does it persist across navigation?

### BUG-7: 404 After Multi-Program Client Creation

**Impact:** Blocks SCN-042 (multi-program client scenario).

**Symptom:** Receptionist creates a client enrolled in multiple programs. After form submission, the redirect URL produces a 404 instead of landing on the new client's profile page.

**Where to look:**
- `apps/clients/views.py` — the `client_create` view's success redirect
- Check if the redirect uses a client ID that doesn't match the newly created record
- Check if `ClientProgramEnrolment` creation for multiple programs causes an issue with the redirect

### TEST-2: CAL-005 Test Runner Captures Wrong Page

**Impact:** Blocks the inaccessible-page calibration validation (CAL-005 should score <= 2.5).

**Symptom:** The test runner navigates to what should be an inaccessible data table but instead captures the Insights filter form. CAL-005 URL was previously fixed from `/reports/outcomes/` to `/reports/insights/` (T46), but the captured page is still wrong.

**Where to look:**
- `konote-qa-scenarios/scenarios/calibration/CAL-005-inaccessible-page.yaml` — check the goto URL in the step actions
- The Insights page may have a filter form that loads first, and the data table only appears after submitting filters
- May need to add a `click` or `fill` action to submit the filter form before capturing

### TEST-4: 8 Multi-Persona Scenarios Produce No Screenshots

**Impact:** Blocks PM1, DS4, DS1c evaluation — 8 scenarios never capture screenshots.

**Symptom:** Scenarios SCN-030, SCN-035, SCN-042, SCN-045, SCN-049, SCN-058, SCN-059, SCN-070 produce 0 screenshots. All are multi-persona or multi-actor scenarios.

**Root cause (likely):** The scenario runner creates a fresh browser context per scenario but doesn't handle actor switches within a scenario correctly. When a step has `login_as: "different_user"`, the runner switches users, but the screenshot capture may fail because the browser context or page object is stale.

**Note:** SCN-035 was also missing the `persona:` field (now fixed). Re-test after the YAML fix to see if it now produces screenshots. The others likely have the same `persona:` field issue — check the bulk fix list below.

**Where to look:**
- `tests/scenario_eval/scenario_runner.py` — `run_scenario()` method, specifically how `login_as` actions interact with `_setup_context_for_scenario()`
- `tests/scenario_eval/state_capture.py` — `capture_step_state()` — does it handle a page that was just switched?

---

## Bulk Fix: 20 Scenarios Missing `persona:` Field

These scenarios have `actors:` but no `persona:` field. The runner uses `scenario.get("persona", "")` for auto-login, so without it, no login happens and preflight fails. For each, add `persona:` set to the first actor (or the primary actor for the scenario).

| File | actors | Suggested persona |
|------|--------|-------------------|
| `calibration/CAL-002-mediocre-page.yaml` | Check YAML | First actor |
| `calibration/CAL-003-bad-page.yaml` | Check YAML | First actor |
| `calibration/CAL-004-accessible-page.yaml` | Check YAML | First actor |
| `accessibility/SCN-058-cognitive-load.yaml` | Check YAML | DS1c likely |
| `accessibility/SCN-059-voice-navigation.yaml` | Check YAML | DS4 likely |
| `accessibility/SCN-062-aria-live-fatigue.yaml` | Check YAML | DS3 likely |
| `accessibility/SCN-063-alt-text-images.yaml` | Check YAML | DS3 likely |
| `accessibility/SCN-064-page-titles.yaml` | Check YAML | DS3 likely |
| `accessibility/SCN-065-focus-not-obscured.yaml` | Check YAML | DS3 likely |
| `cross-role/SCN-042-multi-program-client.yaml` | ["R1", "DS1"] likely | R1 |
| `cross-role/SCN-075-alert-recommendation-workflow.yaml` | Check YAML | First actor |
| `cross-role/SCN-076-group-management-permissions.yaml` | Check YAML | First actor |
| `daily/SCN-026-french-intake.yaml` | Check YAML | R2-FR or DS2 |
| `edge-cases/SCN-045-error-states.yaml` | Check YAML | First actor |
| `edge-cases/SCN-049-shared-device-handoff.yaml` | Check YAML | First actor |
| `edge-cases/SCN-070-consent-withdrawal.yaml` | Check YAML | First actor |
| `periodic/SCN-030-board-prep.yaml` | Check YAML | E1 likely |
| `periodic/SCN-036-pm-program-config.yaml` | ["PM1"] likely | PM1 |
| `periodic/SCN-037-pm-staff-management.yaml` | ["PM1"] likely | PM1 |

**Note:** CAL-001 already has `persona: "E1"` — its issue is the preflight check, not a missing field. CAL-002 through CAL-004 may have the same preflight issue depending on their persona roles.

**Important:** The `persona:` field should match the actor who starts the scenario (usually the first in the `actors:` list). For multi-actor scenarios where step 1 has `login_as:`, the persona should match that user's persona ID.

---

## Suggested Order of Work

1. **Fix CAL-001 preflight** (Item 3) — quick change in `scenario_runner.py`
2. **Bulk-fix the 20 missing `persona:` fields** in konote-qa-scenarios — systematic but straightforward
3. **Re-run smoke test** to verify CAL-001, SCN-010, SCN-035 all pass
4. **Fix BUG-9** (language persistence) — compliance critical, most impactful
5. **Fix BUG-7** (404 after multi-program create)
6. **Fix TEST-2** (CAL-005 wrong page capture)
7. **Fix TEST-4** (multi-persona screenshots) — may be largely resolved by the `persona:` bulk fix
