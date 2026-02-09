# KoNote2 UX Review: Usability Issues by Role

*Review date: 2026-02-03*

---

## Executive Summary

This review examines KoNote2's workflows from the perspective of three user roles: **Direct service staff** (primary users), **Front Desk staff**, and **Administrators**. The goal is to identify usability friction points like the recently-fixed "related notes dropdown" issue, where technical data representations (dates only) replaced human-readable content.

---

## Issues by Category

### 1. Dropdown Labels Missing Context

| Location | Current Display | Problem | Suggested Fix |
|----------|-----------------|---------|---------------|
| Event form → Related Note | ~~"Quick Note - 2026-02-03"~~ | **FIXED** | Now shows 40-char preview |
| Full Note form → Template | "Intake Template" | No description of what sections it includes | Add section count or description |
| Plan Section form → Program | "Youth Services" | Staff may not know which program to pick | Add client count or description |
| Event form → Event Type | "Crisis" | Works OK, but could show colour dot | Consider colour indicator |

### 2. Missing `__str__` Methods (Developer Oversight)

These models have no `__str__` method and will display as "Object (1)" if ever shown in a dropdown or admin:

| Model | Current Display | Fix |
|-------|-----------------|-----|
| `Event` | `<Event object (1)>` | Add: `f"{self.title or self.event_type} - {date}"` |
| `Alert` | `<Alert object (1)>` | Add: `f"Alert - {self.created_at:%Y-%m-%d}: {content[:40]}"` |
| `PlanTargetRevision` | `<PlanTargetRevision object>` | Add: `f"{self.name} (rev {self.created_at:%Y-%m-%d})"` |

### 3. Form Complexity (Direct Service Perspective)

#### Full Progress Note Form

**Current workflow:**
1. Select template (optional)
2. Select session date
3. Check which targets to record against (checkboxes)
4. For each selected target:
   - Write notes
   - Enter metric values
5. Write summary (optional)
6. Set follow-up date (optional)
7. Confirm consent (checkbox at bottom)
8. Save

**Problems:**
- **Consent checkbox is at the bottom** — easy to miss after scrolling through targets
- **No visual progress indicator** — staff member doesn't know how far along they are
- **Targets appear hidden until checkbox clicked** — discoverability issue
- **All fields shown regardless of template** — overwhelming

**Recommendations:**
- Move consent confirmation to the **top** (or make it a modal on submit)
- Add a sidebar progress indicator showing: Template → Targets → Summary → Consent
- Consider a wizard/step-by-step mode for new users

#### Quick Note Form

**Status:** Well-designed, simple, appropriate for the task. No changes needed.

### 4. Navigation and Information Hierarchy

#### Client Layout Tabs

**Current:** Info | Plan | Notes | Events | Analysis

**Problems:**
- No visual indication of which tabs have content (e.g., badge count)
- "Analysis" tab may confuse direct service staff (sounds like admin/reporting)
- Tab names use system terminology, not task-oriented language

**Recommendations:**
- Add counts: "Notes (12)" or a dot indicator for tabs with recent activity
- Consider renaming "Analysis" to "Progress Charts" or similar
- Add "last updated" subtle indicator

### 5. Missing Help Text and Jargon

| Field | Current Label | Problem | Plain-Language Alternative |
|-------|---------------|---------|---------------------------|
| `sort_order` | "Sort order" | Technical jargon | "Display order" or hide entirely |
| `status_reason` | "Status reason" | Vague | "Why is this being changed?" |
| `backdate` | "Backdate" | Unclear | "Session date (if different from today)" |
| `min_value` / `max_value` | Shown to direct service staff | Technical | Only show to admins |

### 6. Error Prevention Gaps

| Scenario | Current Behaviour | Risk | Fix |
|----------|-------------------|------|-----|
| Leaving form with unsaved changes | No warning | Data loss | Add `beforeunload` handler |
| Autosave | Data attribute present but no visible feedback | User doesn't know if saved | Add "Saved" indicator |
| Consent not checked | Error on submit | User scrolls back up confused | Highlight consent field, scroll to it |
| Duplicate note for same date | Allowed | Accidental duplicates | Warn if note already exists for date |

### 7. Role-Specific Issues

#### Direct Service Pain Points
1. **Too many options when starting** — should see "Write a note" prominently, not 5 tabs
2. **Metric entry is buried** — inside target accordions inside notes
3. **No "recent clients" shortcut** — must search every time
4. **Follow-up reminders not prominent** — buried on home page

#### Front Desk Pain Points
1. **Limited but unclear** — knows they can't do things but not always why
2. **Custom field access confusing** — some fields editable, some view-only, no explanation
3. **No clear task list** — what should a front desk user actually do in the system?

#### Administrator Pain Points
1. **Template preview missing** — can't see what a plan/note template looks like before deploying
2. **Bulk operations missing** — can't assign metrics to multiple targets at once
3. **No "undo" for destructive actions** — archive only, no restore preview

---

## Prioritised Recommendations

### Quick Wins (< 1 day each)

1. **Add `__str__` methods** to Event, Alert, PlanTargetRevision
2. **Move consent checkbox** to sticky footer on note forms
3. **Add "Saved" indicator** for autosave
4. **Add unsaved changes warning** (beforeunload)
5. **Add counts to tabs** (Notes (12), Events (3))
6. **Enhance page footer** — add support email, privacy link, session indicator

### Medium Effort (1-3 days each)

7. **Improve template dropdowns** — show description or section count
8. **Add recent clients** to home page sidebar
9. **Collapsible form sections** — progressive disclosure for Full Note
10. **Front Desk orientation** — add "Your role" explanation panel
11. **Duplicate note warning** — check before allowing same-day notes
12. **Keyboard shortcuts system** — with help modal (accessible via `?` key)

### Larger Improvements (1+ week)

13. **Dashboard redesign** — task-oriented home ("Write a note", "Check follow-ups")
14. **Template preview** — see plan/note template structure before applying
15. **Guided onboarding** — first-time user walkthrough by role
16. **Mobile-optimised forms** — responsive note entry
17. **Post-save feedback** — show "What changed" summary after saving notes

---

---

## 8. Page Footer Recommendations

### Current State

The footer currently shows only:
```
KoNote2 — Participant Outcome Management
```

This wastes valuable screen real estate and misses opportunities for user support.

### Recommended Footer Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEFT                         CENTRE                              RIGHT    │
│  ─────                        ──────                              ─────    │
│  KoNote2 © 2026               Keyboard shortcuts (?)              Logged in │
│  Agency Name                  Privacy Policy                     as: Jane  │
│  Support: help@agency.org     Help Centre                        Session:  │
│                                                                   28 min   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Footer Elements by Priority

| Element | Purpose | Implementation |
|---------|---------|----------------|
| **Product name + year** | Branding, copyright | `{{ site.product_name }} © {{ current_year }}` |
| **Agency name** | Multi-tenant clarity | `{{ site.agency_name }}` (new setting) |
| **Support contact** | User help | `{{ site.support_email }}` — already exists in settings |
| **Privacy Policy link** | PIPEDA compliance | Link to `/privacy/` or external URL |
| **Keyboard shortcuts** | Power user discovery | Modal/popover with shortcuts list |
| **Help Centre link** | Self-service support | Link to docs or external help site |
| **Session indicator** | Security awareness | "Logged in as Jane · 28 min remaining" |
| **Version number** | Troubleshooting | Small text: "v1.2.3" (dev/admin only?) |

### Keyboard Shortcuts Popover Content

When user clicks "Keyboard shortcuts (?)" or presses `?`:

```
┌─────────────────────────────────────────┐
│  Keyboard Shortcuts                     │
│  ──────────────────                     │
│                                         │
│  Navigation                             │
│  g then h    Go to Home                 │
│  g then n    Go to Notes (current client)│
│  g then p    Go to Plan (current client) │
│                                         │
│  Actions                                │
│  n          New quick note              │
│  Ctrl+S     Save current form           │
│  Esc        Close modal/cancel          │
│                                         │
│  Search                                 │
│  /          Focus client search         │
│                                         │
│  [Close]                                │
└─────────────────────────────────────────┘
```

### Session Timer Behaviour

The session indicator serves multiple purposes:

1. **Security awareness** — reminds users they're logged into a sensitive system
2. **Timeout prevention** — shows remaining time before auto-logout
3. **Multi-user clarity** — confirms who is logged in (prevents wrong-account errors)

**Behaviour:**
- Normal: "Session: 28 min" (subtle grey text)
- Warning (< 5 min): "Session: 4 min" (amber, slightly larger)
- Critical (< 1 min): "Session expiring!" (red, with extend option)

Clicking the session indicator should offer:
- "Extend session" (resets timeout)
- "Sign out now"

### Footer Variations by Context

| Context | Footer Adjustments |
|---------|-------------------|
| **Login page** | No session info, no shortcuts — just branding + privacy |
| **Public registration** | Agency name prominent, privacy policy required, no session |
| **Normal pages** | Full footer as described |
| **Note entry forms** | Sticky consent footer *above* page footer; page footer remains |
| **Print view** | Hide footer entirely or show minimal "Printed from KoNote2" |

### Accessibility Requirements

- Footer links must be in a `<footer>` element with `role="contentinfo"`
- Session timer must not auto-announce; only announce on user interaction
- Keyboard shortcuts modal must be keyboard-navigable and escapable
- Minimum touch target 44×44px for all interactive elements
- Sufficient contrast for grey "subtle" text (4.5:1 minimum)

### Mobile Footer

On small screens, condense to:

```
┌─────────────────────────────┐
│  KoNote2 · Privacy · Help    │
│  Jane D. · 28 min · [?]     │
└─────────────────────────────┘
```

- Shortcuts available via `[?]` button
- Session info on second line
- Support email accessible via Help link

---

## Questions for Expert Panel

1. Should the Full Note form be a wizard (step-by-step) or stay as one long form?
2. Is consent confirmation better at the top, as a modal, or as a sticky footer?
3. How do we balance "power user" efficiency with "new user" discoverability?
4. What's the right level of role-based UI simplification vs. one consistent interface?
