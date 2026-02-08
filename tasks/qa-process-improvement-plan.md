# QA Process Improvement Plan — konote-web

**Date:** 2026-02-08
**Context:** The QA scenario runner in konote-web captures screenshots and page state for evaluation by the konote-qa-scenarios repo. After Round 2, only 23% of scenarios produced usable screenshots. These improvements target the test runner, test data, and developer workflow.

---

## W1. Pre-flight check in test runner

**Problem:** Several scenarios failed at login (SCN-047 stuck on login page, SCN-050 in redirect loop). All downstream steps were wasted.

**Solution:** Add a pre-flight validation step to the scenario runner that runs before each persona's test suite.

**Steps:**
- [x] Add `_run_preflight(persona)` method to `scenario_runner.py` that: logs in, verifies language, confirms dashboard loads, checks test data exists (QA-W1a)
- [x] If pre-flight fails, skip all scenarios for that persona and write `BLOCKED: preflight failed` to the output (QA-W1b)
- [x] Log the failure reason (login failed, wrong language, missing test data) for debugging (QA-W1c)

---

## W2. Browser console capture

**Problem:** The 404 after form submission (BUG-7) and blank page on network failure (BUG-6) would be easier to diagnose with browser console output. Currently only screenshots are captured.

**Solution:** Save browser console logs alongside screenshots.

**Steps:**
- [x] Add `page.on('console')` listener to `scenario_runner.py` (QA-W2a)
- [x] Save console output to `{scenario}_{step}_{persona}_console.log` alongside each screenshot (QA-W2b)
- [x] Also capture `page.on('pageerror')` for uncaught JS exceptions (QA-W2c)
- [x] Include console errors in the test output summary (QA-W2d)

---

## W3. Duplicate screenshot detection

**Problem:** Multiple scenarios produced identical consecutive screenshots (SCN-005 steps 1-2, SCN-010 steps 1-2, SCN-047 steps 1-4), wasting evaluator time.

**Solution:** Compare consecutive screenshots and flag duplicates.

**Steps:**
- [x] After each screenshot capture, compute a perceptual hash (or pixel diff) against the previous step's screenshot (QA-W3a)
- [x] If similarity > 95%, add `[DUPLICATE]` to the screenshot filename or a sidecar `.meta` file (QA-W3b)
- [x] Log a warning: "Step X screenshot identical to step X-1 — action may not have executed" (QA-W3c)

---

## W4. Verify actions executed

**Problem:** Some test runner steps didn't execute their intended actions — the form wasn't filled, the button wasn't clicked, the search wasn't typed. This produced screenshots of unchanged pages.

**Solution:** Add action verification to the scenario runner.

**Steps:**
- [x] After each `fill` action, verify the field has the expected value (QA-W4a)
- [x] After each `click` action, verify navigation occurred (URL changed) or content changed (DOM mutation) (QA-W4b)
- [x] After each `login_as` action, verify the user is logged in (check for welcome message or role badge) (QA-W4c)
- [x] If verification fails, retry once, then log `ACTION_FAILED` and continue (don't abort the whole scenario) (QA-W4d)

---

## W5. DITL screenshot coverage

**Problem:** Day-in-the-life scenarios only captured 2 screenshots each for narratives that describe 5-11 moments across a full day.

**Solution:** Capture screenshots at each key moment defined in the DITL YAML.

**Steps:**
- [x] Read the `key_moments` list from DITL YAMLs (once konote-qa-scenarios adds them per P4) (QA-W5a)
- [x] For each key moment, navigate to the relevant page and capture a screenshot (QA-W5b)
- [x] For narrative-only DITL scenarios (no automated steps), capture a screenshot of each distinct page the persona would visit (QA-W5c)

---

## W6. Report naming with sequence suffix

**Problem:** Only one report per day is possible with the current `YYYY-MM-DD` naming. Multiple evaluations in a day overwrite each other.

**Solution:** Add a sequence letter suffix when multiple reports exist for the same date.

**Steps:**
- [x] When generating screenshots or reports, check if files already exist for today's date (QA-W6a)
- [x] If they do, append a sequence letter: `2026-02-08a`, `2026-02-08b`, etc. (QA-W6b)
- [x] Apply to both screenshot filenames and report filenames (QA-W6c)
- [x] Update the scenario runner and evaluator to use the latest sequence for the day by default (QA-W6d)

---

## W7. BUG-7 fix — 404 after create participant

**Problem:** After submitting the Create Participant form, the system returns a 404 error. The redirect URL after creation may be wrong.

**Steps:**
- [x] Check the create participant form's `action` or `hx-post` target and the post-creation redirect URL (QA-W7a)
- [x] Fix the redirect to point to the new participant's profile page (QA-W7b)
- [x] Add a success flash message: "Participant [Name] created successfully" (QA-W7c)
- [x] Add a test: submit create form → verify redirect to profile → verify success message (QA-W7d)

---

## W8. IMPROVE-5 — Post-creation confirmation

**Problem:** Even when creation succeeds, there's no visible confirmation. The dashboard looks identical before and after.

**Steps:**
- [x] Add a Django messages flash after successful participant creation (QA-W8a)
- [x] Ensure the message includes the participant's name (QA-W8b)
- [x] Add `aria-live="polite"` to the messages container for screen reader announcement (QA-W8c)
- [x] Add the new participant to the "Recently Viewed" section on the dashboard (QA-W8d)

---

## Priority Order

| Priority | Task | Why |
|----------|------|-----|
| 1 | W1 (Pre-flight) | Prevents wasted screenshots from login failures |
| 2 | W7 (BUG-7 fix) | Core workflow broken — participant creation fails |
| 3 | W4 (Verify actions) | Improves screenshot quality and reduces false "blocked" |
| 4 | W2 (Console capture) | Makes debugging faster for future rounds |
| 5 | W6 (Report naming) | Allows multiple evaluations per day |
| 6 | W3 (Duplicate detection) | Saves evaluator time |
| 7 | W8 (IMPROVE-5) | Usability polish |
| 8 | W5 (DITL coverage) | Depends on P4 in konote-qa-scenarios |
