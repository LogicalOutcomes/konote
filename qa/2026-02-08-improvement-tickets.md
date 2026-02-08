# KoNote2 Improvement Tickets — 2026-02-08 (Updated)

Developer-facing handoff from the full scenario evaluation.
Each item has: what's wrong, where to look, what "fixed" looks like, and priority.

**Source:** Satisfaction report from 2026-02-08 full evaluation.
**Test runner version:** Playwright via pytest, `--no-llm` mode.
**Note:** Items marked [CONFIDENCE: Low] may be test artifacts. Verify before fixing.

---

## Status of Previous Tickets (from 2026-02-07)

| Ticket | Status | Evidence |
|--------|--------|----------|
| BLOCKER-1: Skip-to-content link | **NOT FIXED** | SCN-050: no skip link on login or any subsequent page |
| BLOCKER-2: Focus after login | **NOT FIXED** | SCN-050 step 6: focus ring visible on GitHub footer link after credentials entered |
| BUG-1: Wrong empty-state message | **FIXED** | SCN-010 step 1: "No Participants found matching 'Marie Santos'" with helpful suggestion |
| BUG-2: Create buttons for wrong roles | **FIXED** | SCN-010 step 3: receptionist sees proper 403 page, no Create button |
| BUG-3: Audit log jargon | **PARTIALLY FIXED** | CAL-003: "Created"/"Logged in" badges, IP hidden behind "Show technical details" |
| BUG-4: Language not tied to user | **NOT FIXED** | SCN-010 step 4 (Casey→French), SCN-047 step 5 (Omar→French), SCN-050 steps 3-7 (Amara→French), DITL-DS2 (Jean-Luc→English) |
| BUG-5: Executive landing page exposes PII | **NOT FIXED** | DITL-E1 step 1: client names visible to executive role |
| BUG-6: No offline handling — blank screen | **NOT FIXED** | SCN-048 steps 3-4: completely blank white page |
| IMPROVE-1: Settings state indicators | **PARTIALLY FIXED** | CAL-002: 4 of 6 cards show status |
| IMPROVE-2: Pre-select single program | **FIXED** | SCN-005 step 3: Housing Support pre-checked |
| IMPROVE-3: 403 page wording | **FIXED** | SCN-010 step 3: excellent plain-language error page (scored 4.7) |
| IMPROVE-4: Dashboard timestamp | **FIXED** | CAL-001: "Last updated: 2026-02-08 03:04" visible |

**Summary: 5 FIXED | 2 PARTIALLY FIXED | 5 NOT FIXED (including both BLOCKERs)**

---

## Recommended Fix Order

Fix in this order — each step unblocks the next:

1. **BLOCKER-1 + BLOCKER-2** (skip link + focus) — unblocks all accessibility testing
2. **BUG-5** (executive landing page PII) — quick redirect fix, high privacy impact
3. **BUG-4** (language preference) — unblocks bilingual testing, prevents cross-scenario contamination
4. **BUG-7** (new: 404 after create form submission) — blocks participant creation workflow
5. **BUG-6** (offline handling) — minimum viable banner is a small change
6. **BUG-3 remaining** (audit log polish) — cosmetic, lower priority
7. **IMPROVE-1 remaining** (2 settings cards) — cosmetic, lower priority
8. **IMPROVE-5** (new: post-creation confirmation) — usability polish

---

## BLOCKER-1: Add Skip-to-Content Link (WCAG 2.4.1)

**Status:** NOT FIXED (carried forward from 2026-02-07)
**Confidence:** High

**What's wrong:** No skip-to-content link exists anywhere in the app. Keyboard-only users (DS3 Amara) must Tab through the entire navigation bar, language selector, and footer links before reaching main content. On the login page, this means tabbing through 8+ elements before reaching the username field. This is a WCAG 2.4.1 Level A failure — the most basic accessibility requirement.

**Where to look:**
- Base template (likely `templates/base.html` or similar layout template)
- The `<body>` tag — skip link should be the very first focusable element

**What "fixed" looks like:**
```html
<!-- First element inside <body>, before any nav -->
<a href="#main-content" class="skip-link">Skip to main content</a>

<!-- Later, on the main content area -->
<main id="main-content" tabindex="-1">
```

```css
.skip-link {
  position: absolute;
  left: -9999px;
  z-index: 999;
  padding: 8px 16px;
  background: #1a1a2e;
  color: #fff;
  font-size: 14px;
}
.skip-link:focus {
  position: fixed;
  top: 0;
  left: 0;
}
```

**Acceptance criteria:**
- [ ] Pressing Tab on any page focuses the skip link as the FIRST interactive element
- [ ] The skip link is visually hidden until focused, then visible
- [ ] Activating the skip link moves focus to the `<main>` element
- [ ] Works on: login page, dashboard, participants list, client profile, admin pages
- [ ] JAWS/NVDA announces "Skip to main content, link"

**Screenshot reference:** `SCN-050_step1_DS3.png` — no skip link visible on login page.

**Priority:** BLOCKER. Blocks all keyboard-only testing (SCN-050 through SCN-055, SCN-061, SCN-062).

---

## BLOCKER-2: Fix Focus Management After Login

**Status:** NOT FIXED (carried forward from 2026-02-07)
**Confidence:** High

**What's wrong:** After submitting the login form, focus lands on the footer area (GitHub link has visible focus ring) instead of main content. Screen reader users have no way to know they've logged in successfully without manually navigating back up the entire page.

**Where to look:**
- Login view (likely `auth/views.py` or similar) — the redirect after successful login
- The landing page template — needs a focus target
- Any HTMX `hx-swap` or `hx-target` on the login form
- May need JavaScript: `document.querySelector('main h1').focus()` on page load

**What "fixed" looks like:**
After successful login, focus should move to:
1. The `<main>` element (with `tabindex="-1"`), OR
2. The `<h1>` of the landing page, OR
3. A welcome message announced as an ARIA live region

```javascript
// After login redirect/swap:
document.addEventListener('DOMContentLoaded', () => {
  const main = document.querySelector('main') || document.querySelector('h1');
  if (main) main.focus();
});
```

**Acceptance criteria:**
- [ ] After login, focus is on main content (not footer, not `<body>`)
- [ ] Screen reader announces the new page context (heading or welcome message)
- [ ] Focus is visible (focus ring/outline) on the target element
- [ ] Works for all user roles (staff, receptionist, executive, admin)

**Screenshot reference:** `SCN-050_step6_DS3.png` — focus ring visible on GitHub footer link.

**Priority:** BLOCKER. Combined with BLOCKER-1, makes the app unusable for keyboard-only and screen reader users.

---

## BUG-4: Language Preference Not Tied to User Account

**Status:** NOT FIXED (carried forward from 2026-02-07, now confirmed across 4 scenarios)
**Confidence:** High

**What's wrong:** The interface language is stored in the session/cookie rather than the user's account. When one user logs out and another logs in on the same browser, the second user inherits the first user's language. This is a systemic problem:
- Casey (English) sees French create form after a French session (SCN-010 step 4)
- Omar (English) sees French login on mobile (SCN-047 step 5)
- Amara (English) gets stuck in French redirect loop (SCN-050 steps 3-7)
- Jean-Luc (French) appears to see English dashboard (DITL-DS2 step 1)

**Where to look:**
- Language middleware (likely Django's `LocaleMiddleware` or a custom one)
- The language toggle in the footer/nav — how does it store the preference?
- User profile model — does it have a `language` or `preferred_language` field?
- Login handler — does it set language from user profile?

**What "fixed" looks like:**

| Before | After |
|--------|-------|
| Language stored in session cookie | Language stored in user profile |
| Persists across different users | Loaded from user profile on login |
| Logout doesn't clear language | Logout clears session; login sets from profile |
| Login page language unpredictable | Login page uses browser Accept-Language or default |

**Acceptance criteria:**
- [ ] Each user account has a `language` or `preferred_language` field
- [ ] On login, the interface language is set from the user's profile
- [ ] On logout, the language preference is cleared from the session
- [ ] The language toggle updates both the session AND the user profile
- [ ] Login page defaults to browser Accept-Language header or English
- [ ] A French user logging in after an English user sees French (and vice versa)

**Screenshot reference:** `SCN-010_step4_DS1.png` (English user sees French form), `DITL-DS2_step1_DS2.png` (French user sees English dashboard).

**Priority:** Priority fix. Affects bilingual agencies across all roles.

---

## BUG-5: Executive Landing Page Exposes Individual Client Names (PII)

**Status:** NOT FIXED (identified in previous report, still present)
**Confidence:** High

**What's wrong:** When an executive (E1 Margaret) logs in, the default landing page is the **staff operational dashboard** which shows:
1. Individual client names in "Priority Items" (Jane Doe, James Thompson, Client148, etc.)
2. A "New Participant" button — executives should never create clients
3. A search box that could look up individual clients

The Executive Overview page (`/clients/executive/`) correctly shows aggregate-only data with an explicit confidentiality statement, but it's not the default landing page.

Margaret's persona explicitly states: seeing individual client names is a **liability concern**. This is also a PIPEDA issue — minimum necessary access.

**Where to look:**
- Login redirect logic — what determines where each role lands
- Likely in `auth/views.py` or a `LOGIN_REDIRECT_URL` setting
- The executive role may not have a custom redirect

**What "fixed" looks like:**
```python
# In the login view or post-login redirect
if user.role == 'executive':
    return redirect('/clients/executive/')  # Aggregate-only dashboard
else:
    return redirect('/')  # Staff operational dashboard
```

**Acceptance criteria:**
- [ ] Executive role redirects to `/clients/executive/` after login
- [ ] Executive role does NOT see the staff dashboard with individual names
- [ ] Executive role does NOT see "New Participant" button
- [ ] Staff and receptionist roles still land on the operational dashboard (unchanged)

**Screenshot reference:** `DITL-E1_step1_E1.png` (client names visible to executive), `DITL-E1_step2_E1.png` (correct Executive Overview).

**Priority:** Priority fix. PII exposure to a role that shouldn't see it.

---

## BUG-6: Blank Page on Network Failure — No Error or Recovery

**Status:** NOT FIXED (identified in previous report, still present)
**Confidence:** Medium — blank screenshots may be a Playwright rendering issue, but the app itself has zero offline handling regardless.

**What's wrong:** When the network drops during use (SCN-048), the page goes completely blank — no loading indicator, no error message, no retry button, no offline banner. Any unsaved data is silently lost. Casey works at a drop-in centre with unreliable wifi; this is a realistic and high-impact scenario.

**Where to look:**
- HTMX error handling (`htmx:responseError`, `htmx:sendError` events)
- Service worker (if any) for offline caching
- Base template — no network error fallback exists currently

**What "fixed" looks like (minimum viable):**
```javascript
window.addEventListener('offline', () => {
  document.getElementById('offline-banner').hidden = false;
});
window.addEventListener('online', () => {
  document.getElementById('offline-banner').hidden = true;
});
```

```html
<!-- In base template, above main content -->
<div id="offline-banner" hidden role="alert"
     style="background: #fef3cd; padding: 12px; text-align: center; border-bottom: 2px solid #ffc107;">
  You appear to be offline. Your changes may not be saved.
  <button onclick="location.reload()">Try again</button>
</div>
```

**Nice to have (future):**
- Auto-save note drafts to localStorage every 30 seconds
- On reconnect, offer to restore the draft
- Show a loading spinner with timeout message on slow connections

**Acceptance criteria:**
- [ ] When the browser loses network, a visible banner appears
- [ ] The banner includes a "Try again" / "Reload" button
- [ ] When the network returns, the banner disappears
- [ ] The banner uses `role="alert"` so screen readers announce it
- [ ] No data is silently lost (at minimum, warn the user)

**Screenshot reference:** `SCN-048_step3_DS1.png`, `SCN-048_step4_DS1.png` — completely blank white pages.

**Priority:** Priority fix. Data loss risk for field workers with unreliable connections.

---

## BUG-7: 404 Error After Create Participant Form Submission (NEW)

**Status:** NEW
**Confidence:** High

**What's wrong:** After Casey (DS1) submits the Create Participant form in SCN-010, the system returns a 404 "Page Not Found" error instead of a success page or the new participant's profile. It's unclear whether the participant was actually created — all form data may have been lost.

**Where to look:**
- Create participant form's `action` attribute or HTMX `hx-post` target
- Post-creation redirect URL — may point to a non-existent route
- URL generation for the new participant's profile page (possibly a slug/ID mismatch)

**What "fixed" looks like:**

| Before | After |
|--------|-------|
| Form submits → 404 error page | Form submits → redirect to new participant's profile |
| No indication if data was saved | Success message: "Participant [Name] created successfully" |
| User left confused | Participant visible in profile and participant list |

**Acceptance criteria:**
- [ ] Create Participant form submits without error
- [ ] After successful creation, user is redirected to the new participant's profile
- [ ] A success message confirms the creation (toast, banner, or inline)
- [ ] The new participant appears in the participants list
- [ ] If creation fails, a clear error message explains why (not a 404)

**Screenshot reference:** `SCN-010_step6_DS1.png` (404 after form submission).

**Priority:** Priority fix. Blocks the core participant creation workflow.

---

## BUG-3: Audit Log Remaining Polish

**Status:** PARTIALLY FIXED (carried forward, updated)
**Confidence:** High

**What was fixed:**
- Action badges now show "Created" and "Logged in" instead of raw codes
- IP addresses hidden behind "Show technical details" toggle
- Column header changed from "Resource Type" to "Record type"

**What's still wrong:**
- Filter dropdowns are truncated: "All acti..." appears for Action and Context dropdowns
- "Auth" appears as a record type — should be "Account" or "Login"
- 6 filter fields visible for pages with very few results (2 rows in screenshot)
- No "Common searches" shortcuts for typical audit tasks

**Acceptance criteria (remaining):**
- [ ] Filter dropdowns show full text (not truncated)
- [ ] "Auth" record type renamed to "Account" or "Login"
- [ ] Optional: Filters collapsed by default behind a "Show filters" toggle
- [ ] Optional: Default date range (e.g., last 30 days) instead of all time

**Screenshot reference:** `CAL-003_step1_E1.png`.

**Priority:** Review recommended (core issues fixed, these are polish).

---

## IMPROVE-1: Settings Cards — Remaining State Indicators

**Status:** PARTIALLY FIXED (carried forward, updated)
**Confidence:** High

**What was fixed:** 4 of 6 cards now show summary data:
- Terminology: "Using defaults"
- Features: "2 of 6 enabled"
- Users: "9 active users"
- Note Templates: "1 template"

**What's still missing:**
- Instance Settings: No current values shown (e.g., "Session timeout: 30 min")
- Demo Accounts: No count shown (e.g., "3 demo users")

**Acceptance criteria (remaining):**
- [ ] Instance Settings card shows key current values
- [ ] Demo Accounts card shows a user count

**Screenshot reference:** `CAL-002_step1_E1.png`.

**Priority:** Review recommended (minor polish).

---

## IMPROVE-5: No Confirmation After Participant Creation (NEW)

**Status:** NEW
**Confidence:** Medium

**What's wrong:** After creating a new participant (SCN-005 step 4), the user returns to the dashboard but there's no success confirmation. The dashboard looks identical to before creation. A new user (DS1b Casey, first week) has no idea if the participant was actually created.

Note: This is separate from BUG-7 (404 error). Even when creation succeeds, there should be a visible confirmation.

**Where to look:**
- Post-create redirect handler
- Dashboard template — add a flash/toast message slot
- Django messages framework (likely already available)

**What "fixed" looks like:**
After successful creation:
- A green banner: "Participant [Name] created successfully" (using Django messages)
- OR redirect to the new participant's profile with a success toast
- The new participant should appear in "Recently Viewed" on the dashboard

**Acceptance criteria:**
- [ ] After creating a participant, a visible success message appears
- [ ] The message includes the participant's name
- [ ] Message is accessible (announced by screen readers via `aria-live`)
- [ ] The new participant appears in "Recently Viewed" on the dashboard

**Screenshot reference:** `SCN-005_step4_DS1b.png` (dashboard identical after creation — no confirmation).

**Priority:** Review recommended (usability polish).

---

## Items NOT Filed as Tickets (Likely Test Artifacts)

These appeared in the evaluation but need verification before filing as bugs. Most are likely caused by the test runner environment, not real UX issues.

| Finding | Why it's probably a test artifact | How to verify |
|---------|----------------------------------|---------------|
| SCN-005 steps 1-2 identical screenshots | Duplicate capture — step 2 is "understand the page" (observational) | Check test runner step definitions |
| SCN-010 steps 1-2 identical screenshots | Duplicate capture — step 2 is "correct spelling" but search term unchanged | Check if step 2 action executed |
| SCN-047 steps 1-4 all show login page | Test runner may have failed to submit credentials at 375px viewport | Re-run SCN-047 with login step verified |
| SCN-050 redirect loop (login → privacy → login) | Language carryover + focus issues cause cascading failures | Fix BUG-4 + BLOCKER-1/2 first, then re-run |
| DITL-DS2 showing English instead of French | Test runner not setting `Accept-Language` before login | Re-run with explicit language header |
| SCN-048 blank white pages | Playwright may not render Chrome's offline error page | Test offline behaviour manually in real browser |

**Recommendation:** After fixing BLOCKER-1, BLOCKER-2, and BUG-4, re-run all scenarios with the isolation protocol (fresh browser context, explicit language, prerequisite checks). Many of these may resolve themselves.

---

## All Active Tickets — Summary

| ID | Severity | Description | Priority | Status |
|----|----------|-------------|----------|--------|
| BLOCKER-1 | BLOCKER | No skip-to-content link (WCAG 2.4.1) | Fix first | NOT FIXED |
| BLOCKER-2 | BLOCKER | Focus goes to footer after login | Fix first | NOT FIXED |
| BUG-3 | BUG | Audit log filter truncation and jargon | Review recommended | PARTIALLY FIXED |
| BUG-4 | BUG | Language not tied to user account | Priority fix | NOT FIXED |
| BUG-5 | BUG | Executive landing page exposes PII | Priority fix | NOT FIXED |
| BUG-6 | BUG | Blank page on network failure | Priority fix | NOT FIXED |
| BUG-7 | BUG | 404 after create participant submission | Priority fix | **NEW** |
| IMPROVE-1 | IMPROVE | Settings cards — 2 missing indicators | Review recommended | PARTIALLY FIXED |
| IMPROVE-5 | IMPROVE | No confirmation after participant creation | Review recommended | **NEW** |

**Total: 2 BLOCKERS | 5 BUGS | 2 IMPROVEMENTS**
**New this round: BUG-7, IMPROVE-5**
