# Improvement Tickets — 2026-02-08

Developer-facing handoff from the scenario evaluation.
Each item has: what's wrong, where to look, what "fixed" looks like, and priority.

**Source:** Satisfaction report from 2026-02-08 full evaluation (replacing 2026-02-07 dry run).
**Test runner version:** Playwright via pytest, `--no-llm` mode.
**Note:** Items marked [CONFIDENCE: Low] may be test artifacts. Verify before fixing.

---

## Status of Previous Tickets (from 2026-02-07)

| Ticket | Status | Evidence |
|--------|--------|----------|
| BLOCKER-1: Skip-to-content link | **NOT FIXED** | SCN-050 step 2 still lands on Privacy page |
| BLOCKER-2: Focus after login | **NOT FIXED** | SCN-050 step 1 — focus ring on GitHub footer link |
| BUG-1: Wrong empty-state message | **FIXED** | SCN-010 step 1 now shows "No Participants found matching..." |
| BUG-2: Create buttons for wrong roles | **FIXED** | SCN-010 step 1 — no "New Participant" for receptionist |
| BUG-3: Audit log jargon | **PARTIALLY FIXED** | CAL-003 shows "Created"/"Logged in" badges, IP hidden behind "Show technical details" |
| BUG-4: Language not tied to user | **NOT FIXED** | SCN-010 step 4, SCN-050 steps 4-6, SCN-047 step 5, DITL-DS2 |
| IMPROVE-1: Settings state indicators | **PARTIALLY FIXED** | 4 of 6 cards now show summary stats |
| IMPROVE-2: Pre-select single program | **FIXED** | SCN-005 step 3 — Housing Support pre-checked |
| IMPROVE-3: 403 page wording | **FIXED** | SCN-010 step 3 — "You don't have access to this page" |
| IMPROVE-4: Dashboard timestamp | **FIXED** | CAL-001 — "Last updated: 2026-02-08 03:04" visible |

**Fix these first:** BLOCKER-1 and BLOCKER-2 block ALL keyboard/screen reader testing. Until they're fixed, SCN-050 through SCN-055 and SCN-061 can't produce useful results.

---

## BLOCKER-1: Add skip-to-content link

**Status:** NOT FIXED (carried forward from 2026-02-07)

**What's wrong:** No skip-to-content link exists anywhere in the app. After login, pressing Tab sends focus to the footer (Privacy, Help, GitHub links) instead of main content. Keyboard-only users cannot reach the main application.

**WCAG violation:** 2.4.1 Bypass Blocks (Level A — this is not just AA, it's the baseline).

**Where to look:**
- Base template (likely `templates/base.html` or similar layout template)
- The `<body>` tag or first child — skip link should be the very first focusable element

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
}
.skip-link:focus {
  position: static;
  /* or position: fixed; top: 0; left: 0; with visible styling */
}
```

**Acceptance criteria:**
- [ ] Pressing Tab on any page focuses the skip link as the FIRST interactive element
- [ ] The skip link is visually hidden until focused, then visible
- [ ] Activating the skip link moves focus to the `<main>` element
- [ ] Works on: login page, client list, client profile, dashboard, admin pages
- [ ] JAWS/NVDA announces "Skip to main content, link"

**Screenshot reference:** `SCN-050_step2_DS3.png` — shows Privacy page instead of main content after Tab+Enter.

**Priority:** BLOCKER. Blocks all keyboard-only testing (SCN-050 through SCN-055, SCN-061).
**Confidence:** High — this is a structural issue, not a test artifact.

---

## BLOCKER-2: Fix focus management after login

**Status:** NOT FIXED (carried forward from 2026-02-07)

**What's wrong:** After submitting the login form, focus lands on `<body>` or an unspecified element. The first Tab press goes to footer links rather than main navigation or content.

**Where to look:**
- Login view (likely `auth/views.py` or similar) — the redirect after successful login
- The landing page template — needs a focus target
- May need JavaScript: `document.getElementById('main-content').focus()` on page load after redirect

**What "fixed" looks like:**
After login redirect, focus should land on either:
1. The `<main>` element (with `tabindex="-1"` so it can receive programmatic focus), or
2. The first heading (`<h1>`) inside main content, or
3. A welcome message that serves as a live region announcement

**Acceptance criteria:**
- [ ] After login, focus is NOT on `<body>`
- [ ] After login, pressing Tab goes to the skip link (if added) or main content — not footer
- [ ] JAWS announces the new page context (heading or welcome message)

**Screenshot reference:** `SCN-050_step1_DS3.png` — focus ring visible on GitHub footer link, not on main content.

**Priority:** BLOCKER. Combined with BLOCKER-1, makes the app unusable for keyboard users.
**Confidence:** High — visible focus ring on footer link confirms the issue.

---

## BUG-4: Language preference not tied to user account

**Status:** NOT FIXED (carried forward from 2026-02-07, now confirmed across multiple scenarios)

**What's wrong:** The interface language is stored in the session/cookie, not the user profile. This means:
- A previous user on the same browser can change the language for the next user
- On shared computers (common in nonprofits), language bleeds between users
- Jean-Luc (DS2, profile says `language: "fr"`) sees English after login
- Casey (DS1, English speaker) sees French after a French user was on the same browser

**Confirmed in:** SCN-010 step 4 (Casey sees French), SCN-050 steps 4-6 (screen reader user gets French), SCN-047 step 5 (mobile user gets French), DITL-DS2 steps 1-2 (Jean-Luc gets English).

**Where to look:**
- Language middleware (likely Django's `LocaleMiddleware` or a custom one)
- The language toggle in the footer/nav — how does it store the preference?
- User profile model — does it have a `language` field?

**What "fixed" looks like:**
1. Language preference stored on the User model (e.g., `user.profile.language = 'en'`)
2. On login, language is set from the user profile (overrides any session/cookie value)
3. The language toggle in the UI updates the user profile, not just the session
4. Unauthenticated pages (login) use browser Accept-Language header or default to English

**Acceptance criteria:**
- [ ] Each user has a language preference in their profile
- [ ] Login sets the interface language from the user profile
- [ ] Switching language in the UI persists to the user profile
- [ ] A French user logging in after an English user sees French (and vice versa)
- [ ] The login page defaults to English (or uses browser language)

**Screenshot reference:** `SCN-010_step4_DS1.png` (Casey sees French), `DITL-DS2_step1_DS2.png` (Jean-Luc sees English).

**Priority:** Priority fix. Affects bilingual agencies across all roles.
**Confidence:** Medium — confirmed across 4 scenarios, but shared-computer behaviour should also be tested manually outside the test runner to rule out Playwright session bleed.

---

## BUG-5: Executive landing page exposes individual client names

**Status:** NEW

**What's wrong:** After login, the executive (E1 Margaret, `role: "executive"`) lands on the **staff dashboard**, which shows:
1. A "New Participant" button — executives should never create clients
2. Individual client names in the "Priority Items" section (Jane Doe, James Thompson, Client148 Test148, etc.)
3. A search box that could be used to look up individual clients

Margaret's persona explicitly says seeing individual client names is a **liability concern**. The Executive Dashboard (at `/clients/executive/`) correctly shows aggregate-only data with no PII — but the user doesn't land there after login.

**Where to look:**
- Login redirect logic — what determines where each role lands after login
- Likely in `auth/views.py` or a `LOGIN_REDIRECT_URL` setting
- The executive role may not have a custom redirect, so it falls through to the default staff landing page

**What "fixed" looks like:**
```python
# In the login view or a post-login signal
if user.role == 'executive':
    return redirect('/clients/executive/')  # Executive Dashboard
else:
    return redirect('/')  # Staff landing page
```

**Acceptance criteria:**
- [ ] Executive role lands on `/clients/executive/` (Executive Dashboard) after login
- [ ] Executive role does NOT see the staff landing page with individual client names
- [ ] Executive role does NOT see "New Participant" button
- [ ] Staff and receptionist roles still land on the staff landing page (unchanged)

**Screenshot reference:** `DITL-E1_step1_E1.png` — shows Eva Executive seeing "Jane Doe Safety concern noted", "James Thompson", and 10+ test client names in Priority Items.

**Priority:** Priority fix. PII exposure to a role that shouldn't see it.
**Confidence:** High — screenshot clearly shows individual names on the executive's landing page.

---

## BUG-6: No offline handling — blank screen when network drops

**Status:** NEW

**What's wrong:** When the network connection drops, the app shows a completely blank white screen. There is:
- No "You're offline" message from the app
- No service worker or cached page
- No draft preservation in localStorage
- No retry mechanism
- No warning before the connection is lost

Casey (DS1) works at a drop-in centre with unreliable wifi. If she's mid-note and the connection drops, she loses everything with zero warning and zero recovery.

**Where to look:**
- There is currently no offline handling to look at — this is a missing feature
- Start with a simple approach: a JavaScript-based online/offline detector

**What "fixed" looks like (minimum viable):**
```javascript
// Add to base template or a shared JS file
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
- [ ] When the browser loses network, a visible banner appears saying "You appear to be offline"
- [ ] The banner includes a "Try again" button
- [ ] When the network returns, the banner disappears
- [ ] The banner uses `role="alert"` so screen readers announce it
- [ ] No data is silently lost (at minimum, warn the user)

**Screenshot reference:** `SCN-048_step3_DS1.png` and `SCN-048_step4_DS1.png` — both completely blank.

**Priority:** Priority fix. Data loss risk for field workers with unreliable connections.
**Confidence:** Medium — blank screenshots may be a Playwright rendering issue (Chrome normally shows its own error page), but the app itself has zero offline handling regardless.

---

## BUG-3: Audit log still needs work (partially fixed)

**Status:** PARTIALLY FIXED (carried forward, updated)

**What was fixed:**
- Action badges now show "Created" and "Logged in" instead of "POST" and raw action codes
- IP Address and Resource ID are hidden behind a "Show technical details" toggle
- Column header changed from "Resource Type" to "Record type"

**What's still wrong:**
- Filter dropdowns are truncated: "All acti..." appears for both Action and Context dropdowns (labels cut off)
- "Record type" field shows placeholder "e.g. client," — still somewhat technical
- "Auth" appears as a record type — should be "Account" or "Login"
- No "Common searches" shortcut (e.g., "Recent exports", "Login activity")
- Margaret still can't easily answer "Who exported client data last month?" without knowing how to use the filters

**Where to look:**
- Audit log template — fix dropdown widths or use full labels
- Action/record type display logic — map "Auth" to "Account" or "Login"

**Acceptance criteria (remaining):**
- [ ] Filter dropdowns are not truncated — full labels visible
- [ ] "Auth" record type renamed to "Account" or "Login"
- [ ] Optional: "Common searches" dropdown with pre-built filter combinations

**Screenshot reference:** `CAL-003_step1_E1.png` — shows truncated dropdowns and "Auth" record type.

**Priority:** Review recommended (core issues fixed, these are polish).
**Confidence:** High.

---

## IMPROVE-1: Settings page state indicators (partially fixed)

**Status:** PARTIALLY FIXED (carried forward, updated)

**What was fixed:** 4 of 6 cards now show summary data:
- Terminology: "Using defaults"
- Features: "2 of 6 enabled"
- Users: "9 active users"
- Note Templates: "1 template"

**What's still missing:**
- Instance Settings: Shows description only ("Branding, date format, and session timeout.") — no current values
- Demo Accounts: Shows description only — no count of demo users

**Where to look:**
- Admin settings template (likely `admin/templates/admin/settings.html`)
- The view/context for Instance Settings and Demo Accounts cards

**Acceptance criteria (remaining):**
- [ ] Instance Settings card shows a summary (e.g., "Session timeout: 30 min")
- [ ] Demo Accounts card shows a count (e.g., "3 demo users")

**Screenshot reference:** `CAL-002_step1_E1.png`.

**Priority:** Review recommended (4 of 6 done, minor polish).
**Confidence:** High.

---

## Items NOT filed as tickets (test artifacts or re-run needed)

These appeared in the evaluation but need verification before acting.

| Finding | Why it's probably a test artifact | How to verify |
|---------|----------------------------------|---------------|
| SCN-047 steps 2-5: Stuck on login page | Test runner didn't submit login credentials on mobile viewport | Re-run SCN-047 with login step configured correctly |
| SCN-010 steps 5-6: Create form not submitted / 404 | Test runner captured the form but didn't fill and submit it | Re-run SCN-010 with form submission enabled |
| SCN-050 steps 3-7: Cascading failure | Skip link failure (BLOCKER-1) caused all downstream steps to fail | Fix BLOCKER-1 and BLOCKER-2 first, then re-run SCN-050 |
| SCN-048 steps 3-4: Blank white screen | Playwright may not capture Chrome's offline error page | Test offline behaviour manually in a real browser |
| SCN-005 step 4: "Recently Viewed" empty after create | Test runner may not have submitted the create form | Re-run with form submission, check if participant appears |

---

## Recommended Fix Order

Fix in this order — each step unblocks the next:

1. **BLOCKER-1 + BLOCKER-2** (skip link + focus) — unblocks all accessibility testing
2. **BUG-5** (executive landing page) — quick redirect fix, high privacy impact
3. **BUG-4** (language preference) — unblocks bilingual testing, prevents cross-scenario contamination
4. **BUG-6** (offline handling) — minimum viable banner is a small change
5. **BUG-3 remaining** (audit log polish) — cosmetic, lower priority
6. **IMPROVE-1 remaining** (2 settings cards) — cosmetic, lower priority

After fixes 1-3 are done, re-run **all scenarios** to get clean scores.
