# Session 3: Safe Tasks Execution Plan

**Created:** 2026-03-02
**Context:** PRs #208 (accessibility sweep) and #209 (funder report approval) are open and block certain work. This plan covers tasks that have NO overlap with those PRs.

## Blocking PRs (DO NOT TOUCH these files)

- **PR #208** touches: `base.html`, `static/css/main.css`, `static/css/theme.css`, various admin/auth templates, `tests/test_a11y_ci.py`, `tests/test_clients.py`
- **PR #209** touches: `apps/reports/`, `apps/clients/dashboard_views.py`, `templates/clients/executive_dashboard.html`, `templates/reports/`, `tests/test_reports.py`, `tests/test_clients.py`

---

## Task 1: QA-R8-I18N1 — Fix French Navigation (Bug Fix)

**Priority:** High — blocks French-speaking staff
**Branch:** `fix/french-nav-create`
**Effort:** Small (30 min)

### Problem
Two bugs from QA Round 8:
- **BUG-7:** French "Créer un participant" navigation link doesn't work for receptionist
- **BUG-25:** French `/clients/create/` URL returns 404

### Root Cause Investigation
1. Read `apps/clients/urls.py` — the URL route is `path("create/", views.client_create, name="client_create")`
2. The app URL prefix is `/participants/` (defined in `konote/urls.py`), so the correct URL is `/participants/create/`
3. Check `templates/base.html` nav section — look for hardcoded `/clients/create/` instead of `{% url 'clients:client_create' %}`
4. Check `locale/fr/LC_MESSAGES/django.po` for "Create" / "Créer" translations

### Fix Steps
1. `git pull origin develop && git checkout -b fix/french-nav-create`
2. Find the nav link for "Create Participant" — it likely uses a hardcoded path instead of `{% url %}` tag
3. Replace with `{% url 'clients:client_create' %}` if hardcoded
4. Verify French translation exists for "Create Participant" → "Créer un participant"
5. Run `python manage.py translate_strings` if needed
6. Test: navigate in French, confirm `/participants/create/` loads
7. Run `pytest tests/test_clients.py -k create`

### CAUTION
- `base.html` is also in PR #208. **Only modify the nav link**, do not touch other parts of base.html. If the nav link is in a partial/include template, even better — modify only that file.
- If the fix requires `base.html` changes that would conflict with PR #208, **defer this task** until #208 merges.

### Acceptance Criteria
- French receptionist can navigate to create participant form
- URL resolves correctly in both EN and FR
- No broken links in either language

---

## Task 2: QA-R8-UX10 — Fix Form Resubmission → Help Page (Bug Fix)

**Priority:** High — data entry workflow broken
**Branch:** `fix/form-resubmission-redirect`
**Effort:** Small (30 min)

### Problem
**BUG-34:** When a user corrects validation errors on the create participant form and resubmits, the form redirects to `/help/` instead of completing the creation.

### Root Cause Investigation
1. Read `apps/clients/views.py` — find `client_create` view function
2. Check what happens on POST success — should redirect to `clients:client_detail`
3. Check form `action` attribute in `templates/clients/client_create.html`
4. Look for any HTMX-specific redirect behaviour (HX-Redirect header)
5. Check if there's a referrer/next parameter being mishandled

### Fix Steps
1. `git pull origin develop && git checkout -b fix/form-resubmission-redirect`
2. Identify the redirect logic in the view
3. Fix the redirect to go to client detail page after successful creation
4. Ensure form action points to the correct URL on validation error re-render
5. Run `pytest tests/test_clients.py -k create`

### Acceptance Criteria
- Create form → submit with errors → fix errors → resubmit → lands on client detail page
- No redirect to /help/ under any circumstances during form submission

---

## Task 3: QA-PA-TEST1 + QA-PA-TEST2 — Seed Test Data (QA Scenarios Repo)

**Priority:** Medium — unblocks QA scenario evaluation
**Branch:** work in `konote-qa-scenarios` repo
**Effort:** Medium (1-2 hours)

### Problem
Two QA scenarios need richer seed data:
- **QA-PA-TEST1:** `groups-attendance` page needs 8+ group members and 12+ logged sessions
- **QA-PA-TEST2:** `comm-my-messages` page needs actual messages in the populated state

### Context
- These are in the **konote-qa-scenarios** repo (`C:\Users\gilli\GitHub\konote-qa-scenarios`), completely separate from the main KoNote codebase
- The seed data lives in scenario YAML files or setup scripts
- Check `konote-qa-scenarios/pages/page-inventory.yaml` for the page definitions:
  - `groups-attendance`: "Empty: new group. Default: 12 sessions logged."
  - `comm-my-messages`: needs populated state with actual messages

### Steps
1. Identify where seed data is configured for page state capture
2. For QA-PA-TEST1:
   - Find the groups-attendance scenario setup
   - Add seed data creating 8+ CircleMembers and 12+ group sessions with attendance records
   - Verify the attendance report page shows populated data
3. For QA-PA-TEST2:
   - Find the comm-my-messages scenario setup
   - Add seed data creating staff messages (InternalMessage model)
   - Verify the inbox shows populated messages

### Acceptance Criteria
- `groups-attendance` page shows 8+ members and 12+ session records when captured
- `comm-my-messages` page shows actual message threads when captured

---

## Task 4: WEBSITE-UPDATE1 — Update konote-website (Separate Repo)

**Priority:** Medium — marketing alignment
**Branch:** work in `konote-website` repo (`C:\Users\gilli\GitHub\konote-website`)
**Effort:** Medium (1-2 hours)

### Context
The website is a static HTML site on Netlify. Current pages:
- `index.html` (homepage)
- `features.html` (feature overview)
- `getting-started.html` (user guide)
- `documentation.html` (technical docs)
- `demo.html` (demo/walkthrough)
- `security.html` (security/privacy)
- `services.html` (services/support)
- `evidence.html` (case studies)
- `faq.html`

### What to Update
1. Read all HTML pages to understand current content
2. Cross-reference with current KoNote features (from codebase):
   - Funder reporting (new in recent PRs)
   - CIDS compliance (PR #131)
   - Portal features (surveys, resources)
   - Demo mode
   - Individual data export
   - Group circles
3. Update `features.html` to reflect new capabilities
4. Update `security.html` if PHIPA/privacy features have expanded
5. Check branding matches (org name changes from PR #198)
6. Ensure WCAG 2.2 AA compliance on all pages
7. Deploy: `netlify deploy --dir=. --prod`

### CAUTION
- Do NOT hardcode feature details that might change — keep descriptions at the capability level
- Maintain the existing design language and CSS
- All pages must have `<meta name="robots" content="noindex, nofollow">` and `robots.txt`

### Acceptance Criteria
- Website reflects current KoNote feature set
- All pages accessible (WCAG 2.2 AA)
- Deployed to Netlify

---

## Task 5: DOC-DEMO1 — Demo Data Engine Guide (Documentation)

**Priority:** Low — needed for agency onboarding, not urgent
**Branch:** `docs/demo-data-guide` (in konote repo)
**Effort:** Medium (1 hour)

### Context
The demo data engine already exists. The guide needs to be written/finalized for agency deployment teams. Reference file: `tasks/demo-data-engine-guide.md`

### Key Files to Review
- `apps/admin_settings/demo_engine.py` — core engine
- `apps/admin_settings/management/commands/generate_demo_data.py` — CLI command
- `seeds/demo_data_profile_example.json` — example profile
- `templates/admin_settings/demo_data.html` — admin UI
- `apps/admin_settings/views.py` (function `demo_data_management`) — admin view

### Steps
1. Read all key files to understand current implementation
2. Review `tasks/demo-data-engine-guide.md` for accuracy
3. Write a client-facing guide (Markdown first, then convert to .docx with beautiful-docx)
4. Include: purpose, admin UI walkthrough, CLI usage, profile JSON format, troubleshooting
5. Place in `docs/` directory

### Acceptance Criteria
- Guide is accurate against current codebase
- Suitable for non-technical agency admin to follow
- Screenshots or step descriptions for admin UI flow

---

## Execution Strategy

### Parallelism
These tasks can be organized for efficient execution:

**Parallel Group A (KoNote repo — can use agents in worktrees):**
- Task 1 (QA-R8-I18N1) — bug fix, small
- Task 2 (QA-R8-UX10) — bug fix, small
- Task 5 (DOC-DEMO1) — documentation only

**Parallel Group B (Other repos — zero conflict):**
- Task 3 (QA-PA-TEST1/2) — qa-scenarios repo
- Task 4 (WEBSITE-UPDATE1) — konote-website repo

### Recommended Order
1. **Start with Tasks 1 & 2** (bug fixes) — highest value, smallest effort, quick PRs
2. **Then Task 5** (documentation) — builds on existing reference doc
3. **Then Tasks 3 & 4** (separate repos) — can run in parallel with each other

### Agent Strategy
- Tasks 1 and 2 can run as **parallel agents in worktrees** (independent branches, different files)
- Task 3 works in a completely separate repo
- Task 4 works in a completely separate repo
- Task 5 is documentation and unlikely to conflict with anything

### PR Targets
- Tasks 1, 2, 5 → PR to `develop` (konote repo)
- Task 3 → PR in `konote-qa-scenarios` repo
- Task 4 → direct deploy to Netlify (or PR if the repo has that workflow)
