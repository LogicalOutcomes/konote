# QA Action Plan — Round 8 (2026-03-01)

**Date:** 2026-03-01
**Round:** 8 (tickets file labelled "Round 7" — renumbered to maintain continuity with pipeline log)
**Source report:** `qa/2026-03-01aa-improvement-tickets.md`
**Previous action plan:** `tasks/qa-action-plan-2026-02-21.md` (Round 7)

## Headline Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Total tickets | 84 | Up from 55 (Round 7) — broader scenario coverage |
| BLOCKERs | 13 + 2 PERMISSION | Up from 6 (Round 7) — 5 are unbuilt features |
| BUGs | 35 | Up from 23 (Round 7) |
| IMPROVEs | 16 | Up from 13 (Round 7) |
| TEST | 18 | Up from 11 (Round 7) |
| Finding groups | 17 | Up from 12 — new accessibility groups identified |
| Previously fixed (verify) | 4+ | Skip link, 404→403, language persistence, executive nav — all fixed in QA-R7-TIER1/TIER2 |
| Likely already fixed | 2-3 | BLOCKER-10/12 (data export built 2026-02-28) |

**Key finding: Several tickets match issues fixed in QA-R7-TIER1 (2026-02-21) and QA-R7-TIER2 (2026-02-22).** These may be regressions, stale-screenshot artefacts, or new instances beyond what was previously fixed. Each must be verified against the current deployment before work begins.

**ARCHIVE.md cross-reference (completed after initial panel):** The Round 7 Tier 1 fixes (language persistence, skip-to-content, notes 403, htmx syntax) were completed on 2026-02-21. The Round 7 Tier 2 fixes (executive nav, communication from client, 8 items verified) were completed on 2026-02-22. See `tasks/ARCHIVE.md` lines 74-76 for completion records.

**Evaluation provenance concern:** The pipeline log has no Step 1 (screenshot capture) or Step 2 (evaluation) entry for this round. Without knowing when screenshots were captured and against which deployment, some tickets may be testing code from before the Round 7 fixes shipped. Tickets matching known fixes are labelled "VERIFY" below.

**Positive signals:**
- Data export infrastructure was built (2026-02-28) — BLOCKER-10 and BLOCKER-12 may be resolved
- CIDS/FHIR implementation completed (PR #131) — service episode lifecycle now exists in data model
- Scenario coverage expanded (65→84 tickets reflects broader testing, not necessarily more bugs)
- 17 finding groups identified — shared root causes make fixes more efficient
- Round 7 Tier 1 and Tier 2 were both completed within 24 hours of the action plan

**Genuinely new issues in this round:**
- BLOCKER-13 (login autofocus race) — new security issue, credentials exposed in search bar
- BUG-33 (form data corruption) — silent data integrity issue on validation error
- BUG-20 (create form Tab order) — WCAG 1.3.2
- BUG-22/35 (Tab order to search results) — WCAG 2.4.3
- BLOCKER-5/BUG-19 (language toggle in Tab flow) — WCAG 2.4.3
- BLOCKER-6 (Actions dropdown ARIA pattern) — WCAG 4.1.2

---

## Items Likely Already Fixed (Verify Before Working)

These items were fixed in previous rounds or built between screenshot capture and this panel. Verify with a quick test before re-implementing:

| Ticket | Known Fix | When | Verification |
|--------|----------|------|-------------|
| BLOCKER-4/7 (skip link) | QA-R7-TIER1 | 2026-02-21 | Check skip link href on any page |
| BUG-2/5/16/17 (404→403) | QA-R7-TIER1 | 2026-02-21 | Visit restricted URL as receptionist, check for 403 |
| BUG-3/6/11/14/27 (language mixing) | QA-R7-TIER1 | 2026-02-21 | Login as French persona, check dashboard language |
| PERMISSION-1 (admin nav for executive) | QA-R7-TIER2 (IMPROVE-3) | 2026-02-22 | Login as E1, check nav items |
| BLOCKER-10 (data export) | QA-R7-PRIVACY1 | 2026-02-28 | Check client profile for export button |
| BLOCKER-12 (secure download links) | SecureExportLink | 2026-02-28 | Check `/reports/download/{id}/` route |
| BUG-18 (group auto-scope) | Round 7 same-day fix | 2026-02-21 | Check group creation form for PM1 |
| BLOCKER-3 (service episode) | FHIR-EPISODE1 (PR #131) | 2026-02-27 | Check if UI exists or only data model |

**Recommended first step for next session:** Do a quick spot-check of 3-4 verify items against the live app before starting any fix work. This calibrates how stale the evaluation actually is.

---

## Expert Panel Summary

**Panel:** Accessibility Specialist, UX Designer, Django Developer, Nonprofit Operations Lead

### Key Insights by Expert

**Accessibility Specialist:**
- Three WCAG Level A violations in BLOCKERs: skip link misdirection (2.4.1), language toggle Tab order (2.4.3), and actions dropdown ARIA pattern (4.1.2). If these persist after verification, they block any WCAG conformance claim.
- Skip link (BLOCKER-4/7) was fixed in QA-R7-TIER1 — verify whether this is a regression or stale screenshot before re-implementing.
- BUG-33 (form data corruption on validation error) is a genuinely new finding and especially dangerous for screen reader users — they cannot visually detect that Last Name migrated to Preferred Name.
- BUG-20 (Tab order in create form), BUG-22/35 (Tab presses to reach results), and BUG-23 (touch target size) form a coherent "form accessibility" bundle that should be done together.

**UX Designer:**
- Language mixing (FG-S-2) was fixed in QA-R7-TIER1 via middleware refactor. If it has regressed, the fix was incomplete or something overrode it. Verification should focus on whether the `UserLanguageMiddleware` is still active and positioned correctly.
- BUG-33 (form data corruption) is the most severe genuinely new UX bug — entered data silently moves between fields. This would erode trust with any agency if noticed in production.
- BUG-34 (form resubmission navigates to help page) suggests a broken redirect after POST — likely a form action URL issue.
- BLOCKER-13 (credentials in search bar) combines an autofocus race condition with a redirect timing issue — the fix needs both: single autofocus AND clearing input buffers after redirect.

**Django Developer:**
- BLOCKER-10/12 are likely already fixed by the SEC3 work merged 2026-02-28. SecureExportLink provides single-use, time-limited download links with audit trail. Verify routes exist before re-implementing.
- BLOCKER-13 (autofocus race) fix: remove `autofocus` from all elements except the username field on the login template. Then add `autocomplete="off"` to the search bar on the dashboard to prevent browser autofill from catching stale keystrokes.
- If BUG-2/5/16/17 (404→403) has regressed after the QA-R7-TIER1 fix, check whether new views were added since 2026-02-21 that use the old `get_object_or_404` pattern without the explicit permission check.
- BUG-33 (form data corruption) is likely a Django form field ordering issue — the form's `Meta.fields` order doesn't match the template's visual order, so re-rendered form data appears in wrong positions.

**Nonprofit Operations Lead:**
- The verification-first approach is critical. Before spending development time on tickets, confirm which issues actually exist in the current deployment. The evaluation may have tested stale code.
- BLOCKER-9 (demo login buttons) is a deployment risk for shared nonprofit devices — must be confirmed DEBUG-only before any agency pilot. This is a new verification item regardless of previous fix status.
- BLOCKER-11 (consent withdrawal) and PERMISSION-2 (executive audit log) are policy decisions, not code bugs. These need GK review before any implementation.
- The 5 survey-related tickets (BUG-30/31/32, TEST-10/11) should be excluded from scoring — they inflate failure counts for a feature that hasn't been built yet (tracked separately as SURVEY-LINK1).

### Areas of Agreement

1. **Verify before fixing** — spot-check 3-4 previously fixed items against the live app before starting any work (unanimous)
2. **BLOCKER-13 (autofocus race) is the top genuinely new priority** — credentials exposed on screen (unanimous)
3. **BUG-33 (form data corruption) must be fixed before any agency deployment** — silent data loss is disqualifying (unanimous)
4. **BLOCKER-10/12 should be verified, not rebuilt** — data export was built 2026-02-28 (unanimous)
5. **BLOCKER-11 and PERMISSION-2 need GK review before implementation** — policy decisions (unanimous)
6. **Deployment verification needed** — future QA rounds should record the deployed commit SHA so ticket provenance is clear (unanimous)

### Productive Disagreements

**BLOCKER-1 (funder demographic profile) — Tier 2 or Tier 3?**
- Operations Lead: Tier 2 — funder reports are critical for agency operations
- Django Developer: Tier 3 — the funder reporting system needs broader design work, not just a dropdown
- **Resolution:** Tier 3. Funder reporting is a feature area that needs GK review on methodology before building individual components.

**BLOCKER-9 (demo login buttons) — fix or verify?**
- Django Developer: Already DEBUG-only — just verify the template conditional
- Operations Lead: Don't trust — verify AND add a test that confirms buttons don't render without DEBUG=True
- **Resolution:** Tier 1 as verification + test. Quick to verify, catastrophic if wrong.

---

## Priority Tiers

### Tier 1 — Fix Now: Genuinely New Issues (5 items)

**1. BLOCKER-13 — Login autofocus race condition (security)**
- **Status:** NEW — not in any previous round
- **Expert reasoning:** Credentials appear in the dashboard search bar after login redirect. Dragon NaturallySpeaking and other voice input tools flush pending keystrokes into the wrong field.
- **Root cause:** Multiple elements compete for autofocus on login page; after redirect, search bar receives stale keystrokes.
- **Fix:** Remove `autofocus` from all login page elements except username field. Add `autocomplete="off"` to dashboard search bar.
- **Complexity:** Quick (30 min)
- **Fix in:** konote-app (login template, dashboard template)
- **Acceptance:** No password text appears in any non-password field after login

**2. BLOCKER-9 — Demo login buttons (security verification)**
- **Status:** NEW verification — not previously checked
- **Expert reasoning:** One-click login buttons for named personas visible on login page. On shared nonprofit devices after shift handoff, anyone can access the system without credentials.
- **Fix:** Verify login template wraps demo buttons in `{% if DEBUG %}` or equivalent. Add a test that confirms buttons don't render in production mode.
- **Complexity:** Quick (15 min)
- **Fix in:** konote-app (login template, add test)
- **Acceptance:** Demo buttons not visible with DEBUG=False; test in test suite

**3. BUG-33 — Form validation destroys entered data**
- **Status:** CLOSED — could not reproduce (2026-03-01)
- **Investigation:** Template uses explicit `name="first_name"`, `name="last_name"`, `name="preferred_name"` attributes with matching `value="{{ form.field_name.value|default:'' }}"` bindings. Django maps POST data by field name, not DOM position. No code path exists for Last Name data to migrate to Preferred Name. Likely a browser autofill artifact or stale screenshot.
- **Re-test in next QA round:** Add a specific scenario step to SCN-061 (or a new scenario) that: (1) fills the create participant form with First Name="Test", Last Name="Retest", Preferred Name left blank, (2) submits with a missing required field to trigger validation error, (3) checks that Last Name still shows "Retest" and Preferred Name is still blank. This confirms closure or catches a browser-specific issue.
- **Acceptance:** After validation error, all field values appear in their original fields

**4. BLOCKER-5/BUG-19 (FG-S-6) — Language toggle blocks login form (WCAG 2.4.3)**
- **Status:** NEW — language toggle Tab order not previously addressed (Round 7 fixes covered language persistence, not Tab flow)
- **Expert reasoning:** Language toggle buttons (English/Français) precede the login form in Tab order. Keyboard users must Tab through them to reach username/password. Accidental activation switches the interface language mid-login.
- **Fix:** Move language toggle after the login form in DOM order, or place it in a secondary nav region.
- **Complexity:** Quick (30 min)
- **Fix in:** konote-app (login template)
- **Acceptance:** Tab from skip link reaches username field without passing through language toggle

**5. BLOCKER-6 (FG-S-7) — Actions dropdown ARIA pattern (WCAG 4.1.2)**
- **Status:** NEW — Round 7 fixed ARIA tablist (profile tabs), not the Actions dropdown
- **Expert reasoning:** ArrowDown in the Actions dropdown activates "Record Event" instead of navigating to it. The dropdown doesn't follow ARIA menu button pattern.
- **Fix:** Implement ARIA menu button pattern: ArrowDown/Up moves focus between items without activating; Enter/Space activates the focused item.
- **Complexity:** Moderate (1-2 hours)
- **Fix in:** konote-app (actions dropdown JS, template ARIA attributes)
- **Acceptance:** ArrowDown/Up navigates items; Enter/Space activates; Escape closes

### Tier 1 — Verify: Previously Fixed Items (4 items)

**V1. BLOCKER-4/7 (FG-S-5) — Skip link misdirection (WCAG 2.4.1)**
- **Previous fix:** QA-R7-TIER1 (2026-02-21) — "skip-to-content verified"
- **Verify:** Check skip link href on any page. If still broken, this is a regression — re-fix.
- **Acceptance:** First Tab press on any page shows "Skip to main content" link; activating it moves focus to main content area

**V2. BUG-2/5/16/17 (FG-S-1) — 404 instead of 403 for restricted pages**
- **Previous fix:** QA-R7-TIER1 (2026-02-21) — "notes 403 fixed"
- **Verify:** Visit `/participants/{id}/notes/` as receptionist. If still 404, check whether new views added since 2026-02-21 use the old pattern.
- **Acceptance:** Restricted pages return styled 403 with role-specific message

**V3. PERMISSION-1 — Admin nav visible for executive role**
- **Previous fix:** QA-R7-TIER2 (2026-02-22) — "IMPROVE-3 (executive nav)"
- **Verify:** Login as E1/E2, check nav items. If still visible, this is a regression.
- **Acceptance:** E1/E2 login shows no admin nav items

**V4. Language mixing (FG-S-2) — BUG-3, 6, 11, 14, 27**
- **Previous fix:** QA-R7-TIER1 (2026-02-21) — "language persistence"
- **Verify:** Login as French persona (DS2, R2-FR), navigate dashboard. If language still mixes, check if `UserLanguageMiddleware` is active and positioned correctly in MIDDLEWARE setting.
- **Priority within Tier 1:** Do verification FIRST — if the middleware fix is intact, these 6 tickets are stale screenshots, not regressions.

### Tier 2 — Fix Soon (16 items)

**6. BUG-1 — Newly created client not searchable by other users**
- Cross-role intake handoff fails. DS1 searches for a client R1 just created and gets zero results. May be cache issue or queryset scoping bug.

**7. BUG-4 (FG-S-3) — Quick note entry point unreachable**
- `a[href*='quick']` matches nothing on client profile. Core note-writing workflow is inaccessible via expected URL pattern.

**8. BUG-20 — Create form Tab order doesn't match visual layout**
- Last Name receives focus before First Name in two-column layout. WCAG 1.3.2 / 2.4.3.

**9. BUG-22/35 — Excessive Tab presses to reach search results**
- Filter controls between search field and results in Tab order. Screen reader users must Tab through multiple controls. WCAG 2.4.3 / 4.1.3.

**10. BUG-23 — Checkboxes too small for tablet touch**
- Browser default ~16px checkboxes, below WCAG 2.5.8 minimum 24px target size.

**11. BUG-24/26 — Validation error not shown + no success confirmation**
- Missing required field shows no error. Successful creation shows no confirmation. Both sides of the feedback loop are broken.

**12. BUG-28 — Mobile edit navigates to wrong form**
- Edit contact info on mobile navigates to New Participant form instead of contact edit form. Mobile-specific URL or routing issue.

**13. BUG-29 — Offline navigation shows blank page (VERIFY)**
- Should show styled offline error page. Service worker offline fallback was fixed in Round 7 same-day fixes (2026-02-21, fix-log entry 9). **Verify first** — if the fix is intact, this is a stale screenshot.

**14. BUG-9/10 — Executive dashboard date presets + PDF export**
- Date range filter was added in Round 7 same-day fixes — verify BUG-9 first. BUG-10 (PDF export) is a genuinely new request (Round 7 added CSV).

**15. BUG-7/25 — French navigation fixes**
- French "Créer un participant" navigation broken (BUG-7). French `/clients/create/` URL returns 404 (BUG-25). Both block French-speaking receptionist workflows.

**16. BUG-8 — Calendar feed URL generation fails silently**
- Generate button produces no visible result. POST handler may be failing silently.

**17. BUG-34 — Form resubmission navigates to help page**
- Resubmitting a corrected participant form navigates to help page instead of completing creation. Broken redirect after POST.

**18. BUG-12 — /reports/funder/ returns 404**
- Funder report export URL does not exist. PM workflow blocked.

**19. BUG-13 — PM user management path missing**
- `/manage/users/` is missing or not linked. PM cannot manage staff. May relate to incomplete QA-W59 (/manage/ namespace move).

**20. Accessibility polish bundle (IMPROVE-11, 12, 13, 14)**
- Language toggle confirmation, breadcrumb touch targets, required field visibility, icon-only button labels. Related a11y improvements.

**21. BUG-21 — Profile tabs arrow key navigation**
- ArrowRight on profile tabs opens Actions dropdown instead of next tab. Related to FG-S-7 (ARIA pattern). Note: ARIA tablist was fixed in Round 7 same-day fixes — verify if this is a different issue or regression.

### Tier 3 — Backlog (11 items)

**22. Verify BLOCKER-10/12 — Data export and secure download links**
- Likely already fixed by SEC3/QA-R7-PRIVACY1 (2026-02-28). Verify routes exist and function before filing as open.

**23. BLOCKER-11 — Consent withdrawal workflow** — GK reviews privacy/data retention
- PIPEDA 4.5 obligation. Needs design for what gets deleted vs. retained. Already tracked as QA-R7-PRIVACY2 in Parking Lot.

**24. PERMISSION-2 — Executive audit log access** — GK reviews data access policy
- Design decision: should executives have read-only audit log access for PIPEDA 4.1.4 board accountability? Not a code bug — policy question.

**25. BLOCKER-1 — Funder demographic profile dropdown** — GK reviews reporting methodology
- Funder report page needs demographic profile selection with small-cell suppression. Broader funder reporting design needed.

**26. BUG-15 — Accent stripping in client list display**
- "Benoît" appears as "Benoit." May be encryption/decryption artifact or template encoding issue. Needs investigation.

**27. BUG-30/31/32 (FG-S-9) — Survey feature not deployed**
- Survey URLs return 404. Already tracked separately (SURVEY-LINK1). Exclude from satisfaction scoring.

**28. IMPROVE-1 — First-login attention panel for new users**
- 10+ unfamiliar client names for brand-new user. Consider simpler welcome panel for first week.

**29. IMPROVE-2 — "Notes Today" counter**
- Counter for batch note entry confirmation.

**30. IMPROVE-3/5/6/7/8/9/10/15 — UX improvements bundle**
- Section-level vs inline edit, calendar-quarter presets, PM nav sidebar, programme scope labels, audit log scope, meeting health indicator, per-program staff summary, settings URL.

**31. BLOCKER-2/3/8 — Scenario YAML issues**
- BLOCKER-2: /communications/ URL retired (update YAML). BLOCKER-3: Service episode YAML incomplete. BLOCKER-8: Quick note selector mismatch (partially test infra). Fix in qa-scenarios repo.

**32. IMPROVE-10 — Role-specific 403 messaging**
- Generic 403 denial page. Consider role-specific guidance.

---

## Test Infrastructure Issues (qa-scenarios repo)

18 TEST tickets identified. Fix in `konote-qa-scenarios` repo as a parallel workstream:

| Ticket | Issue | Priority |
|--------|-------|----------|
| TEST-1 | Events tab missing from client profile | High — investigate if feature exists |
| TEST-2 | Meeting create link not on client profile | High — blocks meeting scenarios |
| TEST-3 | SCN-040 note selector mismatch (French) | High — blocks French note workflow |
| TEST-4 | SCN-075 dynamic IDs not resolved | High — template variables literal |
| TEST-5 | SCN-076 group_id not resolved | High — template variables literal |
| TEST-6 | SCN-046 quick note selector mismatch | Medium — same as BUG-4 |
| TEST-7 | SCN-048 consent data not seeded | Medium — test data gap |
| TEST-8 | SCN-049 runner stopped after step 2 | Medium — runner bug |
| TEST-9 | SCN-151 template variables not resolved | Medium — template variables |
| TEST-10 | SCN-116 conditional logic untestable (surveys) | Low — feature not built |
| TEST-11 | SCN-117 French survey untestable (surveys) | Low — feature not built |
| TEST-12 | SCN-062 network error simulation | Medium — test tooling gap |
| TEST-13 | SCN-063 requires axe/JAWS audit | Low — supplemental tooling |
| TEST-14 | SCN-064 requires document.title capture | Low — runner enhancement |
| TEST-15 | SCN-065 requires scrolled screenshots | Low — runner enhancement |
| TEST-16 | SCN-082 meeting test data not seeded | Medium — test data gap |
| BLOCKER-2 | /communications/ URL retired in YAML | High — quick fix |
| BLOCKER-3 | Service episode YAML incomplete | Medium — depends on UI availability |

---

## Deployment Verification Recommendation

Future QA rounds should record the deployed commit SHA when capturing screenshots. This prevents the ambiguity in this round where tickets may be testing code from before known fixes shipped.

Suggested approach:
1. Add a `/version/` endpoint to the Django app that returns the git commit SHA
2. Step 1 (screenshot capture) logs the SHA in the pipeline log entry
3. Step 3 (action plan) compares ticket fix dates against the deployed SHA to determine if tickets are stale

---

## Satisfaction Gap Trend

| Round | Date | Gap | DS3 | Coverage | Notes |
|-------|------|-----|-----|----------|-------|
| 1 | 2026-02-07 | 2.3 | 1.5 | 69% | Baseline |
| 2b | 2026-02-08 | 1.5 | 2.0 | 50% | First fixes |
| 2c | 2026-02-08 | 1.3 | 1.9 | 75% | Same-day iteration |
| 3 | 2026-02-09 | 1.4 | — | 75% | Slight regression |
| 4 | 2026-02-12 | 1.3 | 2.9 | 63% | Stable |
| 5 | 2026-02-13 | 0.9 | 3.2 | 91% | Best gap |
| 6 | 2026-02-17 | 1.0 | 3.3 | 67% | Stable |
| 7 | 2026-02-21 | 1.22 | 3.01 | 75% | First regression |
| **8** | **2026-03-01** | **—** | **—** | **—** | **Scores not in handoff; no Step 2 logged** |

Note: Round 8 scores were not included in the improvement tickets file or satisfaction-history.json. The gap/DS3/coverage values should be added when the Step 2 pipeline log entry is written.

---

## Cross-Reference: Previous Ticket Status

| Issue | Round 7 Fix | Date | Round 8 Status |
|-------|-------------|------|----------------|
| Language persistence | QA-R7-TIER1 | 2026-02-21 | VERIFY — 6 tickets filed (BUG-3/6/11/14/27), may be stale |
| Skip-to-content link | QA-R7-TIER1 | 2026-02-21 | VERIFY — filed as BLOCKER-4/7, may be stale |
| Notes 404→403 | QA-R7-TIER1 | 2026-02-21 | VERIFY — filed as BUG-2/5/16/17, may be stale or new instances |
| htmx syntax errors | QA-R7-TIER1 | 2026-02-21 | NOT RE-TESTED — no matching ticket in Round 8 |
| /manage/ routes verification | QA-R7-TIER1 | 2026-02-21 | VERIFY — BUG-13 (PM user management) may indicate gap |
| Executive nav (IMPROVE-3) | QA-R7-TIER2 | 2026-02-22 | VERIFY — filed as PERMISSION-1, may be stale |
| Communication from client (BUG-7) | QA-R7-TIER2 | 2026-02-22 | VERIFY — TEST-1/2 (Events tab) may be related |
| ARIA tablist on profile tabs | Round 7 same-day | 2026-02-21 | VERIFY — BUG-21 may be same component or different |
| Data export (PIPEDA) | QA-R7-PRIVACY1 | 2026-02-28 | VERIFY — BLOCKER-10/12 may be stale |
| Group auto-scope | Round 7 same-day | 2026-02-21 | VERIFY — BUG-18 may be stale |

---

*Generated by 4-expert panel review — 2026-03-01*
*Corrected after ARCHIVE.md cross-reference (initial version incorrectly claimed Round 7 fixes were not done)*
*84 tickets filed, 8+ likely already fixed (pending verification), 76 analysed*
*5 Tier 1 fixes (genuinely new), 4 Tier 1 verifications (previously fixed), 15 Tier 2 fixes + 1 Tier 2 verification (fix soon), 11 Tier 3 (backlog), 18 TEST (qa-scenarios)*
