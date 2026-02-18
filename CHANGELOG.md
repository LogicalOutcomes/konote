# Changelog

All notable changes to KoNote are documented here. This log is written for agency staff and administrators — not developers. For technical details, see `docs/technical-documentation.md`.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [2.2.0] — 2026-02-18

### Added

**Suggestion tracking & Outcome Insights**
- Capture participant suggestions and reflections in every progress note
- Theme and linking system for categorising recurring feedback across participants
- Two-tier automation: keyword-based auto-linking on note creation, plus AI-generated themes during Outcome Insights analysis
- Responsiveness tracking with status workflow (open → in progress → addressed)
- Theme management at /manage/suggestions/ for program managers
- Executive dashboard shows top suggestion themes per program
- Contextual toast notification on note save when new suggestions are linked to themes

**Goal Builder**
- Combined goal creation form with section assignment, target naming, and three-tier universal metrics (Confidence, Progress, Wellbeing)
- Metric autocomplete from the library

**PM self-service administration**
- Program managers can manage plan templates, note templates, event types, metrics, registration links, and suggestion themes under /manage/
- No system admin access needed for programme-level configuration

**Staff messaging**
- Staff-to-staff messages about participants with My Messages dashboard
- Unread badge in navigation
- Front desk can leave messages; staff and program managers read messages for their programs

**Client transfer workflow**
- Move participants between programs with a dedicated transfer form
- Permission key (`client.transfer`) with role-based access
- Cross-program consent tracking and full audit trail
- Confidential program enrolments are preserved during transfer

**Portal staff management**
- Invite participants to the portal, manage and revoke access, reset MFA — all from the client detail page

**Automated scheduling**
- `send_reminders` management command sends SMS/email reminders for meetings in the next 36 hours, with automatic retry for failures
- `send_export_summary` management command emails admins a weekly digest of all export activity for privacy oversight

**System health monitoring**
- Staff-visible warning banners (yellow/red) on the Meetings page when SMS or email delivery is failing
- Admin alert emails after 24 hours of sustained delivery failures

**Onboarding interview guide**
- Session split into Discovery and Decisions sessions
- Privacy prerequisites document for agencies to complete before configuration
- Between-sessions homework with terminology and role alignment exercises

**First-run setup wizard**
- 8-step guided configuration UI for new instances
- `apply_setup` management command to configure an instance from a YAML/JSON configuration file

### Changed

- **URL restructuring** — PM-accessible management pages moved from /admin/ to /manage/ (plan templates, note templates, event types, metrics, users, audit logs, suggestions, registration). Old /admin/ URLs redirect permanently.
- **Client URL prefix** — Changed from /clients/ to /participants/ throughout the application, with redirects from old URLs
- **Executive dashboard redesigned** — Batch queries replace per-program loops; suggestion theme counts and top themes displayed per program
- **Actions menu consolidated** — Edit, Transfer, and all client actions merged into a single dropdown
- **Tab renames** — "Timeline" renamed to "History"; "Note" renamed to "Notes"
- **Template-driven chart interpretations** — Progress charts now include AI-generated narrative summaries when configured

### Fixed

- Mobile touch targets now meet 44px WCAG 2.2 AA minimum with explicit padding on nav, breadcrumbs, tabs, buttons, and selects
- Dark mode contrast on breadcrumbs, filter bars, add-link elements, and executive dashboard cards
- French translation improvements: explicit preferred_language for test users, translated programme names, metric names in analysis view
- Program manager privilege escalation via user edit form blocked
- HTMX cache bugs resolved with Vary: HX-Request middleware
- Heading level accessibility (h1→h3 skip corrected)
- Disabled buttons now use aria-disabled, tabindex, and aria-describedby for screen reader compatibility
- Back-button cache handling for plan editing pages
- Blue border/outline around main page content removed

---

## [2.1.0] — 2026-02-13

### Added

**Messaging & communications**
- Log phone calls, emails, SMS, and in-person contacts on the client timeline
- Quick-log buttons for common interactions (phone call, email, in-person visit)
- Full communication form for detailed logging with notes and follow-up flags

**Meeting scheduling**
- Schedule meetings with clients and track status (scheduled, completed, cancelled, no-show)
- Send SMS or email reminders when messaging is configured and the client has consented

**Calendar feed (iCal)**
- Subscribe to your KoNote meetings in Outlook, Google Calendar, or Apple Calendar
- Privacy-safe summaries show initials and record ID only — no client names in external calendars

**Consent management**
- CASL-compliant consent tracking for SMS and email on each client record
- Express and implied consent types with date tracking
- Consent withdrawal tracking and signed, time-limited unsubscribe links for clients

**Alert safety workflow**
- Two-person rule for alert cancellation: staff recommend cancellation with an assessment, program managers review and approve or reject

**Funder profiles & reporting**
- Upload demographic breakdown definitions as CSV
- Generate funder reports with custom age bins, merged categories, and small-cell suppression to protect participant privacy

**Permission matrix enforcement**
- 48 permission keys across 4 roles (receptionist, staff, program manager, executive)
- Enforced consistently across all views by decorators and middleware

**Scoped audit logs**
- Program managers see only audit entries for their own programmes
- Executives and admins see all entries

**Messaging health monitoring**
- Staff see warning banners if SMS or email delivery is failing
- Admins receive email alerts after repeated delivery failures

**Demo & testing support**
- `DEMO_EMAIL_BASE` environment variable routes demo user emails to tagged addresses for safe testing

**UX improvements**
- HTMX loading indicators with `aria-live` announcements for screen readers
- Form error summary with focus management and `role="alert"`
- Role-aware 403 ("access denied") page that explains what happened and what to do
- Touch targets meet 24x24px minimum for mobile and tablet use
- Success toast announcements for screen readers on form submissions

### Changed

- **Events tab redesigned** — now shows communications, meetings, alerts, and events on a unified timeline with filtering controls
- **Meeting permission keys** — meeting views now use `meeting.create` and `meeting.edit` instead of `event.create`, fixing a bug where program managers could not schedule meetings
- **Client detail page** — added consent indicators, contact information, and communication history sections

### Fixed

- Form error summaries now have `role="alert"` and auto-focus for screen readers
- HTMX search results announce updates to screen readers via `aria-live`
- Dark mode contrast on filter bar summary
- Heading level skip (h1 to h3) on Events tab corrected
- French translation coverage — 26 new strings extracted and translated
- Executive test user programme assignments in demo seed data

---

## [2.0.0] — 2026-02-05

### Added

**French language support**
- Full bilingual interface with over 2,100 translated strings
- Language switcher in the header following Canada.ca convention
- Cookie-based language persistence across sessions

**Client data erasure**
- Multi-PM approval workflow for PIPEDA/GDPR right-to-erasure requests
- Three erasure tiers: anonymise, purge, and delete
- Requires approval from all relevant program managers before execution
- Audit-logged with record counts only — no personal data in logs
- PDF receipts for completed erasure requests

**Self-service registration**
- Public registration forms with capacity limits and deadline dates
- Duplicate detection to prevent accidental re-enrolment
- Auto-approve option for streamlined intake

**Export hardening**
- CSV injection protection on all exports
- Elevated export monitoring and audit logging
- Secure, time-limited download links

**Confidential programmes**
- Sensitive programme isolation with separate audit logging
- Cross-programme duplicate detection that respects confidentiality boundaries
- DV-ready documentation and guided setup

**Demo mode**
- Safe evaluation environment with 5 demo users (one per role) and sample clients
- Demo data is invisible to real staff accounts

**Canadian localisation**
- Postal code format validation (A1A 1A1)
- Canadian phone number formatting
- Province/territory dropdowns
- Date and currency formatting by locale

**Outcome Insights**
- Programme-level and client-level progress trends
- Engagement pattern analysis
- Participant quotes with categorised feedback

**Metric library**
- Built-in outcome metrics for common programme areas
- CSV import/export for bulk metric management

**Custom client fields**
- Configurable field groups with text, number, date, dropdown, and checkbox types
- Admin interface for creating and organising fields

**Plan templates**
- Reusable outcome plan structures with sections, targets, and metrics

**Progress note templates**
- Configurable note types: standard session, brief check-in, crisis intervention, and more

**Invite links**
- Single-use registration links with pre-assigned roles and programme access

**AI integration (optional)**
- Metric suggestions and outcome improvement ideas via OpenRouter API
- All personally identifiable information scrubbed before any AI request

**PDF reports**
- Client progress reports via WeasyPrint (optional dependency)

**Groups & projects**
- Session logs, attendance tracking, highlights, milestones, and outcomes
- Group-level outcome reporting

**Duplicate detection & merge**
- Phone number and name/date-of-birth matching
- Cross-programme deduplication
- Admin merge tool with full data transfer between records

### Security

- Fernet (AES) encryption for all personally identifiable information fields
- Separate audit database with INSERT-only access
- Argon2 password hashing
- Azure AD single sign-on support
- Role-based access control with programme-scoped permissions
- CSRF, HSTS, Content Security Policy, and secure cookie configuration
- Programme-scoped access and field-level visibility controls
- ClientAccessBlock for cross-programme consent boundaries

### Changed

- Reporting redesigned with funder-specific profiles, fiscal year support, and aggregated demographics
- Documentation expanded with deployment guides for Azure, Railway, Elest.io, and FullHost

---

## [1.0.0] — 2025-12-01

### Added

- Core application: clients, outcome plans, progress notes, events, and charts
- Admin settings: agency terminology, feature toggles, and branding
- Client voice features: client-goal fields, progress descriptors, engagement observation, participant reflection, and suggestions with priority
- Qualitative summary for programme reporting
- WCAG 2.2 AA accessibility: semantic HTML, colour contrast, alt text, and ARIA attributes
- Docker Compose deployment for self-hosting
