# Improvement Tickets — 2026-02-07

Developer-facing handoff from the scenario evaluation.
Each item has: what's wrong, where to look, what "fixed" looks like, and priority.

**Source:** Satisfaction report from 2026-02-07 dry run.
**Test runner version:** Playwright via pytest, `--no-llm` mode.
**Note:** Items marked [CONFIDENCE: Low] may be test artifacts. Verify before fixing.

---

## BLOCKER-1: Add skip-to-content link

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

**Priority:** BLOCKER. Blocks all keyboard-only testing.
**Confidence:** High — this is a structural issue, not a test artifact.

---

## BLOCKER-2: Fix focus management after login

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

## BUG-1: Search "no results" shows wrong empty-state message

**What's wrong:** When a user searches for a name that doesn't exist, the page shows:
> "No Participant files yet. Create the first one"

This is the system's empty state (when no participants exist at all), not a search-results-empty state. It confuses users who know the system has hundreds of clients.

**Where to look:**
- Client list template (likely `clients/templates/clients/client_list.html` or the HTMX partial that renders search results)
- Look for the string "No Participant files yet" — this is used for both the initial empty state AND the filtered-results-empty state
- The HTMX search endpoint probably returns the same partial for "zero total clients" and "zero matching clients"

**What "fixed" looks like:**
Two distinct empty states:

| Condition | Message |
|-----------|---------|
| No participants exist at all | "No Participant files yet. Create the first one" (current, fine) |
| Search/filter returns no results | "No participants found matching '[search term]'. Try a different name or check the spelling." |

The search-results-empty state should NOT show a "Create" button for receptionist roles.

**Acceptance criteria:**
- [ ] Searching for a name that doesn't exist shows "No participants found" (not "No Participant files yet")
- [ ] The search term is echoed back in the message (helps user spot typos)
- [ ] The "Create the first one" button does NOT appear in the search-empty state
- [ ] The "Create the first one" button does NOT appear for receptionist roles in any empty state

**Screenshot reference:** `SCN-010_step1_R1.png` and `SCN-010_step2_R1.png` — both show "No Participant files yet" after searching for "Marie Santos" and "Maria Santos."

**Priority:** Priority fix.
**Confidence:** High — reproducible across two searches in the same scenario.

---

## BUG-2: Create buttons visible to roles that can't create

**What's wrong:** Dana (receptionist, `role: "receptionist"`) sees two create buttons on the client list page:
1. A "New Participant" button at the top of the page
2. A "Create the first one" button in the empty state

Clicking either leads to a 403 Access Denied page. The buttons should be hidden (or disabled with tooltip) for roles without create permission.

**Where to look:**
- Client list template — find the "New Participant" button and the "Create the first one" button
- Both likely need a permission check: `{% if user.has_perm('clients.add_client') %}` or role check
- The 403 page itself (`templates/403.html`) is well-designed — no changes needed there

**What "fixed" looks like:**
```html
{% if perms.clients.add_client %}
  <a href="{% url 'clients:create' %}" class="btn btn-primary">+ New Participant</a>
{% endif %}
```

Same pattern for the empty-state CTA.

**Acceptance criteria:**
- [ ] Receptionist role does NOT see "New Participant" button on client list
- [ ] Receptionist role does NOT see "Create the first one" in empty state
- [ ] Staff role DOES still see both buttons
- [ ] No broken layout when buttons are hidden (empty state still looks intentional)

**Screenshot reference:** `SCN-010_step1_R1.png` — "New Participant" button visible for Dana Front Desk. `SCN-010_step3_R1.png` — resulting 403 page.

**Priority:** Priority fix.
**Confidence:** High.

---

## BUG-3: Audit log uses developer jargon

**What's wrong:** The audit log at `/admin/audit/` displays:
- Action column: HTTP verbs like "POST" and "Login" — "POST" is meaningless to non-developers
- Columns visible: "IP Address," "Resource Type," "Resource ID" — database concepts

Margaret (executive with temporary admin access) cannot answer "Who exported client data last month?" from this page.

**Where to look:**
- Audit log template and view (likely `admin/templates/admin/audit_log.html`)
- The Action badge rendering — currently shows the HTTP method or action code
- The table column definitions

**What "fixed" looks like:**

Replace action codes with plain-language labels:

| Current | Replacement |
|---------|-------------|
| POST | Created |
| Login | Logged in |
| GET (export) | Exported |
| PUT/PATCH | Updated |
| DELETE | Deleted |

Hide technical columns by default:

| Column | Default | Advanced |
|--------|---------|----------|
| Timestamp | Show | Show |
| User | Show | Show |
| Action (plain language) | Show | Show |
| What changed (Resource Type, readable) | Show | Show |
| IP Address | **Hide** | Show |
| Resource ID | **Hide** | Show |

**Acceptance criteria:**
- [ ] Action column shows plain language (Created, Logged in, Exported) not HTTP verbs
- [ ] IP Address is hidden by default (available via "Show advanced" toggle)
- [ ] Resource ID is hidden by default
- [ ] "Resource Type" is renamed to something like "What" or "Record type"
- [ ] Optional: Add a "Common searches" dropdown (Recent exports, Login activity, Data changes)

**Screenshot reference:** `CAL-003_step1_E1.png` — shows "POST" badge and IP Address column.

**Priority:** Priority fix.
**Confidence:** High.

---

## BUG-4: Language preference not tied to user account

**What's wrong:** During testing, an English-speaking staff member (Casey Worker, `username: "staff"`) saw the create form entirely in French. The language appears to be stored in the session/cookie rather than the user profile, meaning:
- A previous user on the same browser can change the language for the next user
- A mis-click on "Français" persists until manually switched back
- Test scenarios bleed language state into each other

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

**Screenshot reference:** `SCN-010_step4_DS1.png` — French create form for English-speaking Casey Worker.

**Priority:** Priority fix.
**Confidence:** Low — may be a test runner artifact (language carried over between scenarios). Verify by having two different users log in on the same browser and checking if language leaks.

---

## IMPROVE-1: Settings page needs state indicators

**What's wrong:** All 6 cards on `/admin/settings/` look identical. No card shows its current state (how many features enabled, how many users, etc.). Margaret can't answer "Is groups enabled?" without clicking through to the Features page.

**Where to look:**
- Admin settings template (likely `admin/templates/admin/settings.html`)
- Each card's view/context — needs to pass a summary stat

**What "fixed" looks like:**
Each card gets a subtitle badge:
- Terminology: "3 custom terms"
- Features: "4 of 6 enabled"
- Instance Settings: "Session timeout: 30 min"
- Users: "12 active"
- Note Templates: "5 templates"
- Demo Accounts: "3 demo users"

**Acceptance criteria:**
- [ ] Each settings card shows a summary of its current state
- [ ] The summary is generated from live data (not hard-coded)
- [ ] Margaret can answer simple questions without clicking through

**Screenshot reference:** `CAL-002_step1_E1.png`.

**Priority:** Review recommended.
**Confidence:** High.

---

## IMPROVE-2: Pre-select program when user has only one

**What's wrong:** On the create-participant form, the Programs checkbox is unchecked even when the logged-in staff member has access to only one program. Casey (Housing Support only) must manually check the box.

**Where to look:**
- Client create view (likely `clients/views.py`, the form class or `get_initial()`)
- The form template that renders the Programs checkboxes

**What "fixed" looks like:**
```python
# In the create view or form __init__
if user.programs.count() == 1:
    form.initial['programs'] = [user.programs.first().pk]
```

**Acceptance criteria:**
- [ ] When a user has exactly 1 program, it's pre-checked on the create form
- [ ] When a user has 2+ programs, none are pre-checked (user must choose)
- [ ] The pre-checked program can still be unchecked if needed

**Screenshot reference:** `SCN-005_step3_DS1b.png` — Housing Support checkbox unchecked despite being the only option.

**Priority:** Review recommended.
**Confidence:** High.

---

## IMPROVE-3: 403 page could use warmer language

**What's wrong:** The 403 page says "Access denied. You do not have the required role for this action." The design is good (styled, has suggestions, navigation), but the language is slightly technical and may feel accusatory to a non-technical user like Dana.

**Where to look:**
- 403 template (likely `templates/403.html`)

**What "fixed" looks like:**

| Current | Suggested |
|---------|-----------|
| "Access Denied" | "You don't have access to this page" |
| "You do not have the required role for this action" | "This page is only available to staff members and program managers" |
| "Contact your administrator" | "Ask your program manager if you need access" |

**Acceptance criteria:**
- [ ] Heading uses softer language (not "Access Denied")
- [ ] Message is role-specific where possible (mentions which roles CAN access)
- [ ] Tone doesn't imply the user did something wrong

**Screenshot reference:** `SCN-010_step3_R1.png`.

**Priority:** Review recommended.
**Confidence:** High.

---

## IMPROVE-4: Dashboard needs "last updated" timestamp

**What's wrong:** The executive dashboard shows aggregate numbers but no indication of when the data was generated or last refreshed. Margaret might wonder if she's looking at today's data or last week's.

**Where to look:**
- Executive dashboard template (likely `clients/templates/clients/executive_dashboard.html`)
- The view that provides the context data

**What "fixed" looks like:**
Add a line below the summary cards:
> Data as of February 7, 2026 at 2:15 PM

**Acceptance criteria:**
- [ ] Dashboard shows a "Data as of [datetime]" line
- [ ] The timestamp reflects when the data was actually queried (not cached)

**Screenshot reference:** `CAL-001_step1_E1.png`.

**Priority:** Review recommended (minor — dashboard scored 4.6 overall).
**Confidence:** High.

---

## Items NOT filed as tickets (test artifacts)

These appeared in the evaluation but are likely caused by the test runner, not real UX issues. Verify before acting.

| Finding | Why it's probably a test artifact | How to verify |
|---------|----------------------------------|---------------|
| SCN-010 steps 5-6: Stuck on create form / 404 | Dry run didn't submit the form, so client wasn't created | Re-run with `--no-llm` removed, or manually complete the form |
| SCN-050 steps 3-7: Cascading failure on Privacy page | Skip link failure caused all downstream steps to fail | Fix BLOCKER-1 first, then re-run SCN-050 |
| SCN-050 steps 5-6: Session expired, back to login page | Long keyboard Tab sequences may have hit session timeout | Check session timeout config; extend for test runs if needed |
| French interface in SCN-050 steps 4-6 | Language cookie carried over from a previous test scenario | Run with fresh browser context per scenario |
