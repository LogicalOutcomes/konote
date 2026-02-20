# Portal Completion — Design Document

**Date:** 2026-02-20
**Branch:** feat/portal-q1-implementation
**Status:** Approved

## Context

The Participant Portal (Phases A-D from `tasks/participant-portal-implementation-plan.md`) is ~95% built. All models, middleware, views, forms, templates, and URL routing are in place. This document covers the remaining gaps needed to bring the portal to production readiness.

## What's Already Built

- **Phase A (Foundation):** ParticipantUser model with HMAC email lookup + Fernet encryption, login/logout, MFA (TOTP + email code), consent flow, invite system with verbal codes, quick-exit button, domain enforcement middleware, portal auth middleware, security system checks, session timeout warning, Django admin registration, audit logging, safety help page
- **Phase B (Core Value):** Dashboard with "new since last visit" banner, goals list and detail with Chart.js metrics, progress page, "What I've been saying" (my_words), milestones, correction requests (two-step soft flow), staff portal reminder after notes (B14)
- **Phase C (Participant Voice):** Journal with privacy disclosure, messages to worker, pre-session discussion prompts, staff-side create-note/invite/manage/revoke/reset-MFA views
- **Phase D (partial):** Staff manage portal UI (D5), security tests (IDOR, session isolation, XSS, auth)
- **Surveys:** Multi-page forms, auto-save, conditional sections, review page, dashboard badge
- **33 templates**, all middleware wired, all URL routing in place

## Remaining Gaps

### 1. Password Reset (A20 — completion)

**Current state:** Views and forms exist. Token generation and email sending are stubbed — the confirm view returns "not available yet."

**Design:**
- Add `password_reset_token` and `password_reset_expires` fields to ParticipantUser
- Generate a 6-digit numeric code (not a URL token — matches MFA Tier 2 UX)
- Store as hashed value (not plaintext) with 10-minute expiry
- Send via Django's email backend (same infrastructure as staff password resets)
- Rate limit: 3 reset requests per hour per email hash
- Always show "If an account exists, we've sent a code" (prevent enumeration)

### 2. Discharge Deactivation (D2)

**Current state:** No signal connects ClientFile status changes to portal account.

**Design:**
- Add a `post_save` signal on ClientFile
- When `status` changes to "discharged" or "closed", set `ParticipantUser.is_active = False`
- Log the deactivation in the audit log with `operation: "auto_deactivated_discharge"`
- Middleware already checks `is_active` — deactivated users are blocked on next request

### 3. Client Merge Portal Transfer (D3)

**Current state:** `merge.py` does not mention portal models.

**Design:**
- In `merge_clients()`, after the main merge logic:
  - If archived client has a portal account and surviving client does not: transfer the account (update `client_file` FK)
  - If both have portal accounts: deactivate the archived client's account (can't have two accounts for one client)
  - Transfer all portal journal entries, messages, corrections, staff notes to surviving client_file
- Log transfer/deactivation in audit

### 4. Erasure Extension (D4)

**Current state:** `erasure.py` does not reference any portal models.

**Design:**
- In `build_data_summary()`: add counts for portal journal entries, messages, correction requests, staff notes
- In anonymise/purge tiers: delete encrypted content from journal entries, messages, correction descriptions; deactivate portal account
- In full erasure tier: CASCADE handles deletion (portal models have `on_delete=CASCADE` to ClientFile)
- Verify CASCADE coverage in tests

### 5. 90-Day Inactivity Deactivation (D1)

**Design:**
- Management command: `deactivate_inactive_portal_accounts`
- Query: `ParticipantUser.objects.filter(is_active=True, last_login__lt=cutoff)` where cutoff = 90 days ago
- Also catch accounts that have never logged in and were created > 90 days ago
- Deactivate (set `is_active = False`), do NOT delete
- Audit log each deactivation
- Intended to run as a scheduled task (cron/Railway cron)

### 6. Staff-Assisted Login (D6)

**Design:**
- New URL: `/my/staff-login/<token>/`
- Staff generates a one-time short-session token (15-minute expiry) from the portal manage page
- Token creates a portal session with `SESSION_COOKIE_AGE` override (30 minutes max)
- No IP range validation in v1 (agencies don't reliably have static IPs) — logged for audit review instead
- Audit log: `portal_staff_assisted_login` with staff user ID + participant ID

### 7. PWA Manifest (D7)

**Design:**
- Add `manifest.json` at `/my/manifest.json` with:
  - `name`: "My Account" (generic per D20)
  - `short_name`: "My Account"
  - `start_url`: "/my/"
  - `display`: "standalone"
  - `theme_color` and `background_color`: match portal CSS
- Add `<link rel="manifest">` to `base_portal.html`
- Generic icons (no agency branding — per D20)

### 8. Portal Usage Analytics (D11)

**Design:**
- New view: `/manage/portal-analytics/` (staff-side, admin or PM only)
- Aggregate stats only (never per-participant — per D13):
  - Total active portal accounts
  - Accounts created this month
  - Total logins this month (from audit log count)
  - Journal entries created (count only)
  - Messages sent (count only)
  - Correction requests (count by status)
- Data source: count queries on portal models + audit log aggregation

### 9. WCAG 2.2 AA Review (D8)

- Verify all portal templates have proper heading hierarchy, ARIA labels, focus management
- Check colour contrast against portal CSS
- Verify all forms have associated labels
- Verify quick-exit button is keyboard accessible
- Test with screen reader (or at minimum verify semantic HTML)

### 10. French Translations

- Run `translate_strings` to extract all portal template strings
- Add French translations for any missing portal entries in the .po file
- Compile .mo file

### 11. Expanded Test Suite (D9)

New test coverage:
- Password reset flow (request, code verification, password change)
- Discharge deactivation (signal fires, account deactivated)
- Client merge (portal account transferred, data moved)
- Erasure (portal data included in all tiers)
- 90-day inactivity deactivation (management command)
- Staff-assisted login (token generation, session creation, expiry)

## Decisions

- **No IP range validation for staff-assisted login:** Agency networks are too varied. Audit logging is sufficient.
- **No push notifications:** Per D15, notifications are in-app only.
- **No group visibility:** Per D10, deferred until agencies request it.
- **Password reset uses 6-digit code, not URL token:** Matches existing MFA UX, simpler for population.
