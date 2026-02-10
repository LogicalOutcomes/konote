# Completed Tasks Archive

Tasks moved from TODO.md after 10+ items in Recently Done.

---

## Completed 2026-02-10

### Moved from Recently Done (2026-02-10 cleanup)

- [x] Front Desk permissions hardening — hide Groups nav, block clinical data on dashboard — 2026-02-08 (UI-PERM1)
- [x] Fix BLOCKER-1 skip link — auto-focus main content per expert panel consensus — 2026-02-08 (QA-FIX1)
- [x] Playwright tests for BLOCKER-1/2 — focus verification automated — 2026-02-08 (QA-VERIFY1)
- [x] QA Round 2c — 6 bug fixes: accent search, French names, untranslated strings, button permissions, audit CSS — 2026-02-08 (QA-W9 through QA-W18)
- [x] Fix BUG-7, BUG-9, BUG-10 — 404 after create, language cookie, autofocus — 2026-02-08 (BUG-7, BUG-9, BUG-10)
- [x] Participant suggestion field + AI feedback insights — encrypted suggestions, priority levels, categorised feedback — 2026-02-08 (VOICE1)
- [x] QA process improvements — pre-flight, console capture, duplicate detection, action verification, DITL coverage, report naming, 404 fix, aria-live — 2026-02-08 (QA-W1 through QA-W8)

---

## Completed 2026-02-09

- [x] QA scenario runner full coverage — 4 test users, 6 clients, 7 action types, 22 scenarios, LLM evaluator — 2026-02-08 (QA-DATA1 through QA-EVAL3)

---

## Completed 2026-02-08

### Moved from Recently Done (2026-02-08 cleanup #3)

- [x] Fix 14 pre-existing test failures + 4 errors — missing form fields, wrong assertions, missing DB declarations, template bugs, Playwright skip fix — 2026-02-07 (TEST-FIX1)
- [x] Fix language bleed on shared browser — clear cookie on logout, set cookie on login to match user preference — 2026-02-07 (BUG-4)
- [x] French translations complete — translated 93 remaining strings to Canadian French, 100% coverage (2146/2146 entries), .mo compiled, validation passed — 2026-02-07 (I18N-TRANS1)

### Moved from Recently Done (2026-02-08 cleanup #2)

- [x] Code review MEDIUM remaining — admin_required decorator across all views (QUAL8), translated access denied messages (I18N-8), modal focus trap (A11Y-2), 20 JS strings translatable (I18N-4), 29 audit log view tests (TEST-4) — 2026-02-07
- [x] Code review MEDIUM fixes — QUAL5-7, A11Y-1, I18N-1/2/3/5/6/7/9/10: dev cookie fix, group forms, dedup client fields, scope on th, PDF/email/form/CSV translations, breadcrumbs, privacy.html blocktrans — 2026-02-07
- [x] Code review HIGH fixes — audit "cancel" action, consolidated `_get_client_ip()` and `admin_required`, dead JS code removed, encryption key rotation + lockout tests — 2026-02-07 (QUAL1-4, TEST1-2)
- [x] Code review CRITICAL fixes — demo/real data isolation in client HTMX views, admin_required on registration views, plan template + submission merge bypasses — 2026-02-07 (SEC1-4)
- [x] Per-Program Roles cleanup — audit logging, dead code removal, ROLE_RANK constants, help.html blocktrans, admin notices, query caching — 2026-02-07 (ROLE1-8)

### Scenario Evaluation Fixes (from `qa/2026-02-08-improvement-tickets.md`)

- [x] Skip-to-content link — improved CSS, added `clip-path` for robustness — 2026-02-08 (BLOCKER-1)
- [x] Focus after login — JS auto-focuses `<main>` on page load — 2026-02-08 (BLOCKER-2)
- [x] Executive redirect — `_login_redirect()` sends executives to aggregate dashboard — 2026-02-08 (BUG-5)
- [x] Language preference — moved middleware after auth, overrides cookie with user profile — 2026-02-08 (BUG-4)
- [x] Offline banner — `role="alert"` banner with "Try again" button — 2026-02-08 (BUG-6)
- [x] Audit log "Auth" → "Account", filter grid widened — 2026-02-08 (BUG-3b)
- [x] Settings cards — all 6 now show summary stats — 2026-02-08 (IMPROVE-1b)
- [x] Search "no results" shows correct empty state — 2026-02-07 (BUG-1)
- [x] Create buttons hidden for roles without permission — 2026-02-07 (BUG-2)
- [x] Audit log badges show "Created"/"Logged in", IP hidden behind toggle — 2026-02-07 (BUG-3)
- [x] Pre-select program when user has only one — 2026-02-07 (IMPROVE-2)
- [x] 403 page warmer language — 2026-02-07 (IMPROVE-3)
- [x] Dashboard "last updated" timestamp — 2026-02-07 (IMPROVE-4)
- [x] 4 of 6 settings cards now show summary stats — 2026-02-07 (IMPROVE-1)

### QA Infrastructure Phase 3 (from konote-qa-scenarios)

- [x] Automate objective scoring dimensions — axe-core for accessibility, action count for efficiency, doc lang for language — 2026-02-08 (QA-T10)
- [x] CI/CD gate — GitHub Actions workflow runs scenarios on push to main, `qa_gate.py` fails build on BLOCKER scores — 2026-02-08 (QA-T11)
- [x] Track satisfaction gap over time — `track_satisfaction.py` appends to history JSON, `chart_satisfaction.py` generates trend table — 2026-02-08 (QA-T12)
- [x] Bidirectional ticket status — GitHub Actions workflow parses `QA:` in commit messages — 2026-02-08 (QA-T14)
- [x] Test isolation for scenario runner — fresh browser context per scenario, locale from persona data, auto-login — 2026-02-08 (QA-ISO1)
- [x] Screenshot naming improvement — URL slug appended to filenames for route traceability — 2026-02-08 (QA-T20)
- [x] CAL-006 inter-rater reliability automation — runs CAL-001 to CAL-005 with variant configs, computes ICC(2,1) — 2026-02-08 (QA-IRR1)

### QA Scenario Runner — Full Coverage

- [x] Add 4 test users: DS1c (Casey/ADHD), DS4 (Riley/voice), PM1 (Morgan/cross-program), E2 (Kwame/admin) — 2026-02-08 (QA-DATA1-4)
- [x] Add 6 test clients: Benoit, Sofia, Priya, Li Wei, Fatima, Derek — 2026-02-08 (QA-DATA5)
- [x] 5 new action types: voice_command, dictate, intercept_network, close/open tab, go_back/screenshot — 2026-02-08 (QA-ACT1-5)
- [x] 7 new test classes covering 22 scenarios (daily, periodic, cross-role, edge case, accessibility, DITL) — 2026-02-08 (QA-TEST1-7)
- [x] LLM evaluator prompt enhancements: cognitive_load_checks, mechanical_checks, task_completion_criteria — 2026-02-08 (QA-EVAL1-3)

### Moved from Recently Done (2026-02-08 cleanup)

- [x] Demo site setup — merged to main, registration link seeded, GitHub Pages verified, live demo tested — 2026-02-07 (DEMO1-4)
- [x] CONF9 follow-ups — logger.exception() for audit, flash message on context switch, request-level cache for needs_program_selector, soft-filter vs hard-boundary docs — 2026-02-07 (CONF9a-d)

---

## Completed 2026-02-07

### Moved from Recently Done (2026-02-07 cleanup #3)

- [x] Erasure hardening — all 7 expert-panel recommendations implemented: PDF receipt scoping, audit-before-erasure, receipt download tracking, rejection notifications, deduplication fix, race condition fix, pagination — 2026-02-06 (ERASE-H1–H7)
- [x] Duplicate merge tool — admin-only side-by-side comparison, transfers notes/events/plans/enrolments/fields, 32 tests — 2026-02-06 (MATCH4)
- [x] Phase H complete — confidential programs, duplicate detection, merge tool, DV documentation — 2026-02-06 (CONF1-8, MATCH1-6)
- [x] Translation reliability — `translate_strings` command, startup detection, CLAUDE.md workflow rule — 2026-02-06 (I18N-CMD1)
- [x] Full integration test pass — 1,000+ tests passing — 2026-02-06 (TEST3)

### Moved from Recently Done (2026-02-07 cleanup #2)

- [x] FullHost deployment verified — HTTPS working via Let's Encrypt, demo data live — 2026-02-06 (OPS5, OPS-FH2)
- [x] Multi-role staff program context switcher — session-based active program for mixed Standard/Confidential users, forced selection on login, nav dropdown, 39 tests — 2026-02-06 (CONF9)

### Moved from Recently Done (2026-02-07 cleanup)

- [x] French translation hardening — 108 unwrapped strings, Help/Privacy pages, demo banner — 2026-02-06 (I18N-FIX2-3)
- [x] Security, privacy, accessibility review fixes — encrypted PlanTarget fields, MultiFernet rotation, aria-live, data tables — 2026-02-06 (SEC-FIX1-2, PRIV-FIX1-2, A11Y-FIX1-3)
- [x] Client voice, qualitative progress, groups app (Phases A-D) — 2026-02-06 (CV1-4)

---

## Completed 2026-02-06

### Moved from Recently Done (2026-02-06 cleanup #3)

- [x] Wrap 108 unwrapped strings across 10 apps in `_()` + 78 new French translations — forms, models, choices, placeholders — 2026-02-06 (I18N-FIX2)
- [x] Add French translations for Help and Privacy Policy pages — ~200 new strings, both pages were showing English — 2026-02-06 (I18N-FIX3)
- [x] Phase H.5 documentation — user-facing confidential programs guide, annual security review checklist, updated Phase H.4 warning in template, docs index links — 2026-02-06 (MATCH6, CONF8)
- [x] Confidential program hardening Phase H.4 — Django admin filtering with object-level permissions, immutable audit logging (403 tracking, confidential tagging, PM audit view), small-cell suppression in reports, 17 new tests — 2026-02-06 (CONF4-6)
- [x] Name + DOB secondary duplicate detection — fallback matching when phone unavailable, single-pass iterator, brittleness fixes (hx-params removal, date parsing, race condition prevention), 12 new tests — 2026-02-06 (MATCH3)
- [x] Cross-program client matching Phase H.1 + H.2 — confidential program isolation, phone field, duplicate detection, security fixes (edit form bug, PDF export, registration links, group views), test suite — 2026-02-06 (CONF1-3, MATCH1-2, CONF7)
- [x] Verify deployment end-to-end with production-like config — FullHost tested, HTTPS working, demo data live — 2026-02-06 (OPS5)
- [x] Lock in .mo translation strategy — commit .mo to git, no compilation in Docker, freshness check in validate_translations.py — 2026-02-06 (I18N-FIX1)
- [x] Fix 4 UX walkthrough crashes + 6 test failures — 2026-02-06 (UX-FIX1)
- [x] Add translation lint script to catch unwrapped user-facing strings — 2026-02-06 (I18N-LINT1)
- [x] Security, privacy, accessibility review fixes — encrypted PlanTarget fields, MultiFernet rotation, aria-live timer, data tables for charts, Privacy Officer settings, retention expiry alerts — 2026-02-06 (SEC-FIX1-2, PRIV-FIX1-2, A11Y-FIX1-3)
- [x] Fix 3 review bugs — AuditLog crash on metric import, group re-add constraint, ghost revisions — 2026-02-06 (QR-FIX4-6)
- [x] Fix 4 group view bugs — attendance name mismatch, membership form, role handling, demo separation — 2026-02-06 (QR-FIX1-3)
- [x] Client voice, qualitative progress, groups app (Phases A-D) — encrypted client_goal on targets, progress descriptors, engagement observation, 7-model groups app, 3 demo groups — 2026-02-06 (CV1-4)

### Moved from Recently Done (2026-02-06 cleanup #2)

- [x] Expand demo from 2 programs / 10 clients to 5 programs / 15 clients — 2026-02-06 (DEMO-EXP1)
- [x] Independent code reviews (security, privacy, accessibility, deployment) — 2026-02-06 (SEC-REV1-4)

### Moved from Recently Done (2026-02-06 cleanup)

- [x] Demo Account Directory page + is_demo_context audit flag — 2026-02-06 (DEMO9, DEMO12)
- [x] Parking lot quick wins — aria-describedby, test deps, email errors, field rename — 2026-02-06 (UX-A11Y1, REV2-DEPS1, REV2-EMAIL2, DB-TERM1)
- [x] Fix 5 review follow-ups — erasure emails, tier validation, history ordering, French filters, phone tests — 2026-02-06 (REV2-EMAIL1, REV2-TEST1, REV2-ORDER1, TESTFIX1, TESTFIX2)
- [x] Review follow-ups — email warnings, SQL-optimised PM filtering, PIPEDA aging — 2026-02-06 (REV-W3, REV-W1, REV-PIPEDA1)

### Completed Review Fix Sections (all from SEC-REV1-3)

- [x] Encrypt PlanTarget.name, .description, .status_reason fields + PlanTargetRevision equivalents (SEC-FIX1)
- [x] Add MultiFernet key rotation support to konote/encryption.py (SEC-FIX2)
- [x] Change decryption error return from "[decryption error]" to empty string (SEC-FIX3)
- [x] Create daily management command to alert admins about expired retention dates (PRIV-FIX1)
- [x] Add Privacy Officer name/email to InstanceSettings and expose in templates (PRIV-FIX2)
- [x] Add data table alternatives for Chart.js charts (A11Y-FIX1)
- [x] Add aria-live to session timer + "Extend Session" button (A11Y-FIX2)
- [x] Add aria-describedby to full note form error messages (A11Y-FIX3)
- [x] Increase auto-dismiss delay from 3s to 8-10s (A11Y-FIX4)
- [x] Create 404.html and 500.html error pages extending base.html (A11Y-FIX5)

---

## Completed 2026-02-05

### French i18n, Canadian Localisation, i18n Reliability (all complete)

- [x] Complete French defaults for all 24 terminology terms — 2026-02-05 (I18N3)
- [x] Wrap form labels, errors, help text in gettext_lazy for French — 2026-02-05 (I18N4a-forms)
- [x] Audit empty states, dates, placeholders for French — 2026-02-05 (I18N4a-remaining)
- [x] Test complete user journey in French — 2026-02-05 (I18N4b)
- [x] Postal code accepts both "A1A 1A1" and "A1A1A1" — normalize on save — 2026-02-05 (I18N5)
- [x] Address labels use "Province or Territory" not "State" — 2026-02-05 (I18N5a)
- [x] Phone fields accept multiple Canadian formats — 2026-02-05 (I18N5b)
- [x] Verify date/currency formatting respects language locale — 2026-02-05 (I18N5c)
- [x] Add `*.mo` to railway.json watchPatterns — 2026-02-05 (I18N-R1)
- [x] Fix SafeLocaleMiddleware canary — now tests "Funder Report Export" — 2026-02-05 (I18N-R2)
- [x] Create `check_translations` management command — 2026-02-05 (I18N-R3)
- [x] Add git pre-commit hook — block commits where .po is newer than .mo — 2026-02-05 (I18N-R4)
- [x] Build template string extraction script — 2026-02-05 (I18N-R5)
- [x] Create `update_translations` wrapper — 2026-02-05 (I18N-R6)

### Individual Client Export + Hardening (all complete)

- [x] Create single-client export view — 2026-02-05 (EXP2x)
- [x] Include all client data: info, notes, plans, metrics — 2026-02-05 (EXP2y)
- [x] Generate PDF format option — 2026-02-05 (EXP2z)
- [x] Add export button to client detail page — 2026-02-05 (EXP2aa)
- [x] Fix duplicate audit log — 2026-02-05 (EXP-FIX1)
- [x] Add CSV injection protection — 2026-02-05 (EXP-FIX2)
- [x] Add server-side receptionist block — 2026-02-05 (EXP-FIX3)
- [x] Harden filename sanitisation — 2026-02-05 (EXP-FIX4)
- [x] Add receptionist-blocked tests — 2026-02-05 (EXP-FIX5)

### Export Documentation + Cleanup (all complete)

- [x] Document SecureExportLink lifecycle — 2026-02-05 (DOC-EXP1)
- [x] Create export runbook — 2026-02-05 (DOC-EXP2)
- [x] Fix `{% trans %}` with HTML in `pdf_unavailable.html` — 2026-02-05 (I18N-EXP2)
- [x] Wrap `ExportRecipientMixin` strings in `gettext_lazy()` — 2026-02-05 (I18N-EXP3)
- [x] Extract `<strong>` from `{% blocktrans %}` in export/funder report templates — 2026-02-05 (I18N-EXP4)

### Secure Export Foundation (all complete)

- [x] Fix demo/real separation in client_data_export, metric, funder report views — 2026-02-05 (EXP0a-d)
- [x] Add recipient field + audit logging to all export views — 2026-02-05 (EXP2a-d)
- [x] Add warning dialogs — client count, PII warnings, required recipient — 2026-02-05 (EXP2e-g)
- [x] Add tests, fix i18n in export templates, verify WCAG contrast, aria-hidden on emojis — 2026-02-05 (TEST-EXP1, I18N-EXP1, A11Y-EXP1-2)
- [x] Secure links — model, views, templates, cleanup command, revocation — 2026-02-05 (EXP2h-p)
- [x] Export permission alignment — PM scoped exports, creator downloads, 35 tests, role matrix — 2026-02-05 (PERM1-10)

### Moved from Recently Done (2026-02-05 cleanup)

- [x] Secure export foundation complete — security bug fix, audit logging, warnings, secure links, revocation — 2026-02-05 (EXP0a-p)
- [x] Multilingual Phases 1A–1C — 636 French translations, bilingual login, [EN|FR] toggle — 2026-02-05 (I18N1-2b)
- [x] Harden seed system — remove fragile guard, deduplicate data, add warnings — 2026-02-05 (SEED1)
- [x] Progress note encryption + MFA documentation — 2026-02-05 (SEC1, SEC2)
- [x] Deployment Workflow Phase 1 — demo/real data separation — 2026-02-05 (DEMO1-8)
- [x] Azure deployment guide — 2026-02-04 (DOC20)
- [x] Documentation improvements — staff guide, archive reorg — 2026-02-03 (DOC18, DOC19)
- [x] PIPEDA/PHIPA consent workflow + note follow-up dates — 2026-02-03 (PRIV1, FU1)

### Security & Multilingual

- [x] Progress note encryption — CLOUD Act protection — 2026-02-05 (SEC1)
- [x] MFA documentation — 2026-02-05 (SEC2)
- [x] Fix French translations not loading — LOCALE_PATHS + EN/FR switcher styling — 2026-02-05 (I18N-FIX1)
- [x] Multilingual Phases 1A–1C — 636 translations, bilingual login, [EN|FR] toggle — 2026-02-05 (I18N1-2b, TEST-I18N1)
- [x] Harden seed system — remove fragile guard, deduplicate data — 2026-02-05 (SEED1)
- [x] Deployment Workflow Phase 1 — demo/real data separation — 2026-02-05 (DEMO1-8)
- [x] Azure deployment guide — 2026-02-04 (DOC20)

### Previously in Recently Done

- [x] Create "Quick Start for Staff" training doc — 2026-02-03 (DOC18)
- [x] Fix test suite configuration error — 2026-02-03 (TEST2)
- [x] PIPEDA/PHIPA consent workflow — block note entry until client consent recorded — 2026-02-03 (PRIV1)
- [x] Note follow-up dates on home page — 2026-02-03 (FU1)
- [x] Add CSV export for all client data — 2026-02-03 (EXP1)
- [x] Mobile responsiveness pass — 2026-02-03 (UI1)
- [x] Note auto-save / draft recovery — 2026-02-03 (UX21)
- [x] Add client search filters (program, status, date) — 2026-02-03 (UX19)
- [x] Add backup automation examples to docs — 2026-02-03 (OPS1)

## Completed 2026-02-03

- [x] Add consent checkbox to note entry — 2026-02-03 (PRIV2)
- [x] Iframe embed support for registration forms — 2026-02-03 (REG8)
- [x] Phase E: Self-service registration complete (REG1-REG7) — 2026-02-03
- [x] Add "What You'll Need" pre-flight checklist to getting-started.md — 2026-02-03 (DOC12)
- [x] Add "What just happened?" explanations after key generation steps — 2026-02-03 (DOC13)
- [x] Add expected output examples showing what success looks like — 2026-02-03 (DOC14)
- [x] Add glossary section: terminal, repository, migration, container — 2026-02-03 (DOC15)
- [x] Create "Before You Enter Real Data" checkpoint document — 2026-02-03 (DOC16)
- [x] Fix placeholders to obviously fake values like REPLACE_THIS — 2026-02-03 (DOC17)
- [x] French UI translation — Django i18n setup + ~500 strings — 2026-02-03 (I18N1)
- [x] Document folder button — link to client folder in SharePoint/Google Drive — 2026-02-03 (DOC5)
- [x] Terminology override by language — extend model for fr/en terms — 2026-02-03 (I18N2)
- [x] Create getting-started.md — complete local dev setup with Docker option — 2026-02-03 (DOC8)
- [x] Create security-operations.md — security tests, audit logs, key rotation — 2026-02-03 (DOC9)
- [x] Enhance README Quick Start — add key generation commands — 2026-02-03 (DOC10)
- [x] Add inline comments to .env.example — explain each variable — 2026-02-03 (DOC11)
- [x] "What KoNote Is and Isn't" documentation page — set scope expectations — 2026-02-03 (DOC6)
- [x] Show custom fields in read-only mode by default with edit toggle — 2026-02-03 (UX12)
- [x] Add date-only toggle to event form — 2026-02-03 (UX13)
- [x] Style permission error pages with navigation and helpful text — 2026-02-03 (UX14)
- [x] Add status and program filters to client list page — 2026-02-03 (UX15)
- [x] Auto-dismiss success messages after 3 seconds; keep errors persistent — 2026-02-03 (UX16)

## Completed 2026-02-02

- [x] Harden startup: raise ImproperlyConfigured if secrets missing; remove hardcoded fallbacks — 2026-02-02 (CR1)
- [x] Fix CSS bug: `align-items: centre` -> `center` — 2026-02-02 (CR8)
- [x] Add encryption ceiling note to agency-setup.md — 2026-02-02 (CR5)
- [x] Add `role="alert"` and `aria-live="polite"` to templates (18 files) — 2026-02-02 (CR9)
- [x] Create ModelForm classes for login, feature toggle, custom fields, AI endpoints — 2026-02-02 (CR4)
- [x] Add tests for auth views, plan CRUD, and AI endpoints (60 tests) — 2026-02-02 (CR6)
- [x] Code review: DEBUG, CSRF, migrations, empty states verified — 2026-02-02 (CR2, CR3, CR7, CR10)
- [x] Staff dashboard with recent clients, alerts, quick stats, needs-attention list — 2026-02-02 (UX1)
- [x] HTMX-powered client detail tabs (no full page reloads) — 2026-02-02 (UX2)
- [x] Target selection checkboxes on note form — 2026-02-02 (UX3)
- [x] Notes list filtering (type, date, author) and pagination — 2026-02-02 (UX4)
- [x] Fix N+1 queries in client search/list with prefetch_related — 2026-02-02 (UX5)
- [x] Fix note collapse to use HTMX instead of location.reload() — 2026-02-02 (UX6)
- [x] Add hx-confirm to destructive plan actions — 2026-02-02 (UX7)
- [x] Group admin nav items under dropdown menu — 2026-02-02 (UX8)
- [x] Autofocus search input on home page — 2026-02-02 (UX9)
- [x] Select All / Deselect All for metric export checkboxes — 2026-02-02 (UX10)
- [x] Error toasts persist until dismissed; added close button — 2026-02-02 (UX11)
- [x] PDF exports: individual client progress reports + bulk funder reports (WeasyPrint) — 2026-02-02 (RPT2)
- [x] Phase 7: Audit DB lockdown, CSP tuning, rate limiting, key rotation command, deployment guides (Azure, Elest.io, Railway), agency setup guide, backup/restore docs — 2026-02-02 (SEC1, SEC4, SEC5, SEED1, DOC1, DOC2, DOC3, DOC4, OPS2)
- [x] Phase 6: Terminology, feature toggles, instance settings, user management admin UIs, cache invalidation signals — 2026-02-02 (CUST1, CUST2, CUST3, USR1)
- [x] Phase 5: Charts, events, alerts, combined timeline, funder report export, audit log viewer — 2026-02-02 (VIZ1, EVT1, EVT2, VIZ2, RPT1, AUD1)
- [x] Phase 4: Quick notes, full structured notes, metric recording, templates admin, timeline, cancellation — 2026-02-02 (NOTE1-NOTE5)
- [x] Phase 3: Plan sections, targets, metrics, templates, apply-to-client, revision history — 2026-02-02 (PLAN1-PLAN6)
- [x] Phase 2: Program CRUD, role assignment, client CRUD, enrolment, custom fields, search — 2026-02-02 (PROG1-CLI3)
- [x] Create theme.css with design tokens (swappable per agency) — 2026-02-02 (DES1)
- [x] Replace badge colours with semantic token classes — 2026-02-02 (DES2)
- [x] Redesign login page with wordmark and brand colour — 2026-02-02 (DES3)
- [x] Add skip-nav, aria-live regions, branded focus style — 2026-02-02 (A11Y1)
- [x] Create empty state, loading bar, and toast patterns — 2026-02-02 (DES4)
- [x] Move login inline styles to CSS class — 2026-02-02 (DES5)
- [x] Generate Django migrations for all 8 apps — 2026-02-02 (FIX1)
- [x] Create test suite: 15 tests for RBAC + PII encryption — 2026-02-02 (TEST1)
- [x] Add HTMX global error handler + toast to app.js — 2026-02-02 (FIX2)
- [x] Register all models in admin.py (8 apps) + enable Django admin — 2026-02-02 (FIX3)
- [x] Phase 1: Django project scaffold, settings, Docker — 2026-02-02 (FOUND1)
- [x] Phase 1: Security middleware (RBAC, audit, CSP, CSRF) — 2026-02-02 (FOUND2)
- [x] Phase 1: All data models (clients, plans, notes, events, metrics) — 2026-02-02 (FOUND3)
- [x] Phase 1: Azure AD + local auth with Argon2 — 2026-02-02 (FOUND4)
- [x] Phase 1: PII encryption utilities (Fernet) — 2026-02-02 (FOUND5)
- [x] Phase 1: Metric library seed data (24 metrics) — 2026-02-02 (FOUND6)
- [x] Phase 1: Base templates (Pico CSS, HTMX) — 2026-02-02 (FOUND7)
