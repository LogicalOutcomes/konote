# Improvement Tickets — 2026-02-12a (Round 4)

**Generated:** 2026-02-12 15:30
**Round:** 4
**Previous active tickets:** BUG-8, BUG-11 (NOT FIXED), BUG-9 (PARTIALLY FIXED)

---

## New Tickets

### BUG-14: lang='fr' on /reports/insights/ — residual language issue

- **Severity:** Priority fix
- **Affects:** DS3 (and any English-preferring persona visiting the reports page)
- **Detected in:** CAL-005 (calibration), confirmed via objective scoring
- **Evidence:** axe-core/lang check shows `<html lang="fr">` on `/reports/insights/` when persona expects `lang="en"`. Screen readers (JAWS, NVDA) would default to French pronunciation rules, making English content unintelligible.
- **Impact:** Language dimension score = 1.0 (lowest possible). CAL-005 would score ~3.7 without this penalty.
- **Relation:** May be residual from BUG-9 (language persistence, marked FIXED 2026-02-11). BUG-9 fix may not cover the reports module. Or this is a BUG-8/BUG-11 (French translation gaps) overlap.
- **Recommendation:** Check `reports/views.py` or the reports template for hardcoded `lang="fr"`. Ensure language is set dynamically from user preference or session.
- **PIPEDA/PHIPA:** Not directly, but AODA requires content to be perceivable; wrong lang attribute violates WCAG 3.1.1 (Language of Page, Level A).
- **WCAG:** 3.1.1 Language of Page (Level A) — FAIL

---

### TEST-5: SCN-035 all steps produce identical screenshots

- **Severity:** Test infrastructure
- **Affects:** PM1 (Morgan) — funder reporting scenario
- **Detected in:** Screenshot deduplication analysis
- **Evidence:** All 5 steps of SCN-035 produce identical 94864-byte PNG files. The test runner lands on `/clients/` and never navigates to the reporting pages.
- **Impact:** PM1's funder reporting workflow cannot be evaluated. Coverage blocked for periodic/PM scenarios.
- **Root cause (suspected):** PM1 test user (`program_mgr`) may lack permissions to reporting pages, OR the test method's navigation path doesn't match the scenario YAML's expected URLs (e.g., `/reports/` vs `/reports/funder/`).
- **Recommendation:** Verify PM1 user's permissions include `reports: true`. Check `test_scn_035_funder_reporting()` in conftest for correct URL paths.

---

### TEST-6: SCN-020 step 2 produces duplicate screenshot

- **Severity:** Test infrastructure
- **Affects:** R1 (Dana) — phone number update
- **Evidence:** Step 1 and step 2 both produce 36637-byte PNG files. Step 2 (open client profile) never navigates away from the client list.
- **Root cause (suspected):** The click or search step in the test method doesn't wait for navigation. Add `page.wait_for_url()` or `page.wait_for_load_state("networkidle")` after the click.
- **Recommendation:** Add explicit wait in `test_scn_020_phone_update()` step 2.

---

### TEST-7: SCN-025 step 2 produces duplicate screenshot

- **Severity:** Test infrastructure
- **Affects:** R2 (Omar) — quick client lookup
- **Evidence:** Step 1 and step 2 both produce 38170-byte PNG files. Same issue as TEST-6 — client profile navigation not executing.
- **Recommendation:** Same fix as TEST-6. Consider a shared `navigate_to_client_profile()` helper that includes proper waits.

---

### TEST-8: SCN-047 extensive duplication at 375px viewport

- **Severity:** Test infrastructure
- **Affects:** R2 (Omar) — mobile phone experience
- **Evidence:** Steps 1–2 identical (36191 B), steps 3–5 identical (44752 B). Only 2 of 5 steps are evaluable.
- **Root cause (suspected):** At 375px viewport width, touch targets and navigation elements may be collapsed into a hamburger menu. The test runner clicks on elements that are not visible at this viewport width, producing no navigation.
- **Recommendation:** Update `test_scn_047_mobile_phone()` to:
  1. Open hamburger/mobile navigation menu before clicking nav links
  2. Use `element.scroll_into_view_if_needed()` before interactions
  3. Add viewport-specific selectors if the responsive layout uses different element IDs

---

### TEST-9: SCN-048 steps 3–4 produce 4KB screenshots

- **Severity:** Test infrastructure
- **Affects:** DS1 (Casey) — offline/slow network simulation
- **Evidence:** Steps 3 and 4 produce identical 4253-byte PNG files (nearly blank). Additionally, both produce i18n-switch.png files (26639 B) instead of the expected page content.
- **Root cause (suspected):** The offline/slow-network simulation (`page.route("**/*", ...)` or network throttling) may block ALL resources including the HTML. The 4 KB screenshot is likely a Chrome "ERR_CONNECTION_RESET" page or blank white page. The i18n-switch.png suggests a redirect to a language selection page occurred during the offline state.
- **Recommendation:**
  1. Ensure offline simulation only throttles API calls, not the base HTML
  2. Pre-load the page before applying network throttling
  3. Consider using `page.set_offline(True)` after initial page load instead of blocking all routes

---

## Previously Filed Tickets — Status Update

### Fixed This Cycle

| Ticket | Description | Fix Date | Verification |
|--------|-------------|----------|-------------|
| BUG-7 | 404 after multi-program client creation | 2026-02-11 | No 404s observed in SCN-010/040 client creation flows |
| BUG-10 | Tab order mismatch on create form | 2026-02-11 | CAL-004 improved from 2.8 → 4.0 (+1.2 pts) |
| BUG-12 | Front desk button missing | 2026-02-11 | R1 workflows proceed normally |
| BUG-6 | Offline error page not helpful | 2026-02-11 | Steps 1–2 of SCN-048 show styled pages (94–39 KB) |
| TEST-2 | CAL-005 captures wrong page | 2026-02-11 | CAL-005 now captures /reports/insights/ |
| TEST-4 | 8 multi-persona scenarios produce no screenshots | 2026-02-11 | Multi-persona scenarios now produce screenshots |

### Partially Fixed

| Ticket | Description | Status |
|--------|-------------|--------|
| BUG-9 | Language persistence — compliance critical | Most pages fixed; `/reports/insights/` still shows `lang='fr'`. See BUG-14. |

### Not Fixed (Carried Forward)

| Ticket | Description | Since |
|--------|-------------|-------|
| BUG-8 | French translation gaps (DS2 affected) | Round 2 |
| BUG-11 | French translation gaps (PM2-FR affected) | Round 2b |

---

## Priority Order

1. **BUG-14** (priority fix) — lang='fr' on reports page. WCAG 3.1.1 Level A violation. Blocks CAL-005 from moving to Green band.
2. **BUG-8 / BUG-11** (carried) — French translation gaps. Blocks DS2 and PM2-FR scenarios from Green band.
3. **TEST-5** (test infra) — PM1 reporting blocked. Needed for coverage improvement.
4. **TEST-8** (test infra) — Mobile viewport testing broken. Needed for R2 mobile evaluation.
5. **TEST-6 / TEST-7** (test infra) — Client profile navigation. Quick fix with waits.
6. **TEST-9** (test infra) — Offline simulation. Lower priority but affects edge case scoring.

---

## Recommendations for Round 5

1. Fix BUG-14 and verify BUG-9 is fully resolved across ALL pages (especially reports module)
2. Fix TEST-5/6/7/8 to improve coverage from 63% toward the 80% target
3. Capture screenshots for the 15 missing scenarios (SCN-026, 030, 036, 037, 042, 045, 049, 058, 059, 063, 064, 065, 070, 075, 076)
4. Run permissions sync to update the hash before next evaluation
5. Consider adding `aria-live="polite"` regions for HTMX content swaps (SCN-055 persistent Orange)
6. Improve form error announcements for keyboard/screen reader users (SCN-061 persistent Orange)
