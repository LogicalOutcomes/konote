# Implementation Plan: Dual Document Integration (SharePoint + Google Drive)

**Date:** 2026-02-27
**Status:** Draft — pending PB/SG approval of design rationale (DOC-INTEG1)
**Design rationale:** `tasks/design-rationale/document-integration.md`
**Expert review:** Design reviewed by 5-expert panel (2026-02-27). Implementation plan reviewed by 4-expert panel (SharePoint Platform Architect, Django Integration Engineer, Nonprofit Technology Operations Manager, Systems Thinker — 2026-02-27). Changes incorporated below.
**Depends on:** Nothing — can start after design approval

## What We're Building

Two separate document folder integrations:

1. **SharePoint buttons on the staff-side client record** — one per program, linking to that program's SharePoint document library. Replaces the current single global document button.
2. **Google Drive link in the participant portal** — per program enrolment, showing participants a link to their own working documents folder.

KoNote is a **link broker only** — it stores folder URLs and generates links. It never touches, stores, or transmits document contents. No OAuth, no API integration.

## Pre-Build Checklist

| Gate | Description | Status |
|------|-------------|--------|
| PB-1 | PB approves design rationale (DOC-INTEG1) | Pending |
| PB-2 | SG approves design rationale (DOC-INTEG1) | Pending |
| PB-3 | GK approves as product owner (data access patterns, portal purpose) | Pending |

## Current State

The existing document integration is a **single-provider, global URL template** approach:

- `InstanceSetting` stores `document_storage_provider` (none/sharepoint/google_drive) and `document_storage_url_template` (with `{record_id}` placeholder)
- `apps/clients/helpers.py` has `get_document_folder_url(client)` — generates a URL from the global template
- `templates/clients/_client_layout.html` shows a single "Documents" button using that URL
- Context processor `document_storage()` in `konote/context_processors.py` provides template variables
- Admin form in `apps/admin_settings/forms.py` has the provider/template fields
- Security audit checks domain allowlist (sharepoint.com, drive.google.com, onedrive.live.com)

**What changes:**
- SharePoint moves from global config → per-program config
- Google Drive moves from staff-side → portal-side, per program enrolment
- Staff client record shows per-program SharePoint buttons (not one global button)
- Portal dashboard gets a new "Your Documents" card

## Data Model Changes

### A. Program model — add SharePoint URL template

Add to `apps/programs/models.py` → `Program`:

```python
sharepoint_url_template = models.CharField(
    max_length=1000, blank=True, default="",
    help_text=_("SharePoint folder URL with {record_id} placeholder. "
                "Example: https://contoso.sharepoint.com/sites/konote/YouthEmployment/{record_id}/"),
)
```

**Why max_length=1000:** SharePoint URLs with URL-encoded French characters, deep path structures, and view parameters can exceed 500 characters. Expert panel confirmed 500 is insufficient for production SharePoint URLs.

**Why on Program, not a separate model:** Each program has at most one SharePoint library. A CharField on the existing model is simpler than a new join table. The field is blank by default — programs with no SharePoint integration just leave it empty.

**Model-level validation** (`clean()` method on Program):
- Must start with `https://`
- Must contain `{record_id}` placeholder
- Must NOT contain `-my.sharepoint.com` or `/personal/` (these are OneDrive URLs, not SharePoint — staff will paste them by mistake)
- Domain allowlist enforcement stays in the security audit command, not form validation (to support custom domains, GCC tenants, and vanity URLs)

### B. ClientProgramEnrolment model — add Google Drive folder URL

Add to `apps/clients/models.py` → `ClientProgramEnrolment`:

```python
document_folder_url = models.URLField(
    max_length=500, blank=True, default="",
    help_text=_("Google Drive folder URL for this participant's working documents."),
)
```

**Why NOT encrypted:** The expert panel unanimously agreed encryption is unnecessary here. The Google Drive URL (`https://drive.google.com/drive/folders/1aBcDeFg...`) is an opaque identifier that reveals nothing about the client or program. The enrolment record itself (which links client to program) is already access-controlled by KoNote's RBAC. Encrypting prevents useful SQL queries (e.g., "how many enrolments have documents configured?") and adds complexity without meaningful security benefit. Anyone who obtains this URL still needs Google Drive permissions to access the folder.

**Model-level validation** (`clean()` method on ClientProgramEnrolment):
- If set, must start with `https://drive.google.com/drive/folders/`
- Must NOT be a Google Doc/Sheet/Slides URL (common paste mistake)

**Why on enrolment, not client:** A client in two programs may have two different Google Drive folders with different resource kits. One link per enrolment keeps it clean.

### C. Record ID format validation

Add a model-level validator on `ClientFile.record_id` that rejects URL-unsafe characters:

```python
import re
RECORD_ID_PATTERN = re.compile(r'^[A-Za-z0-9\-_.]+$')

def validate_record_id(value):
    if value and not RECORD_ID_PATTERN.match(value):
        raise ValidationError(
            _("Record ID may only contain letters, numbers, hyphens, underscores, and dots.")
        )
```

**Why:** Record IDs are inserted directly into SharePoint URLs. Characters like spaces, accents, slashes, or `#` produce broken or ambiguous URLs. Validating at creation time prevents encoding issues by construction rather than patching them after the fact. The expert panel flagged this as a "Heisenbug" risk — broken URLs that appear and disappear depending on browser encoding behaviour.

### D. Global settings — atomic deprecation

The existing global `document_storage_provider` and `document_storage_url_template` in `InstanceSetting` will be deprecated. **The transition must be atomic** to avoid a confusing window where both global and per-program settings exist:

1. Phase A: Migration helper copies global template to all active programs
2. Phase B: Global document settings are **hidden from admin UI immediately** (not deferred to Phase E)
3. Global `InstanceSetting` rows remain in the database for backward compatibility but are not editable

**Why atomic:** If both settings are visible, staff will update the wrong one and wonder why nothing changed. The expert panel flagged this as a coupling risk.

## Implementation Phases

### Phase A: Data Model + Admin UI (Foundation)

Must be done first. All other phases depend on this. **Phase A must be fully merged and tested before starting B and C.**

| Task | Summary | Details |
|------|---------|---------|
| A1 | Add `sharepoint_url_template` to Program model | CharField(max_length=1000, blank=True). Add `clean()` method: HTTPS required, `{record_id}` required, reject OneDrive URLs (`-my.sharepoint.com`, `/personal/`). Run makemigrations + migrate. |
| A2 | Add `document_folder_url` to ClientProgramEnrolment | URLField(max_length=500, blank=True). Add `clean()` method: must match `https://drive.google.com/drive/folders/*`. Run makemigrations + migrate. |
| A3 | Add Record ID format validation | Add validator on `ClientFile.record_id` — only letters, numbers, hyphens, underscores, dots. No spaces, slashes, accents, or special characters. |
| A4 | Add SharePoint URL template field to program admin form | In `apps/programs/forms.py` (or create if needed). Only visible to program_manager and admin roles. Include "Test URL" button that opens the rendered template with a sample Record ID in a new tab so admin can verify setup. OneDrive-specific rejection message: "This looks like a OneDrive personal link. Please use a SharePoint site URL (it should contain /sites/ or /teams/ in the path)." |
| A5 | Add Google Drive URL field to enrolment management | Where staff manage a client's program enrolment, add a "Google Drive Folder URL" field. Validate format in both form and model. |
| A6 | Write migration helper for global→per-program transition | Management command `migrate_document_settings`: copy global `document_storage_url_template` to all active programs' `sharepoint_url_template` if provider is SharePoint. Skip archived programs. Skip programs that already have a template set (never overwrite). If global provider is Google Drive, log a warning. Require `--dry-run` first; `--apply` to execute. Print summary of actions taken. |
| A7 | Tests for models and forms | Test: URL validation (valid/invalid patterns including OneDrive rejection, custom domains, GCC tenants), Record ID format validation, migration helper (both providers, edge cases, skip-if-exists, archived programs). |

**Exit criteria:** Models migrated, admin forms working with "Test URL" button, OneDrive rejection working, Record ID validator in place, all A-phase tests pass.

### Phase B: Staff UI — Per-Program SharePoint Buttons

Depends on Phase A. Can run in parallel with Phase C.

| Task | Summary | Details |
|------|---------|---------|
| B1 | Add `get_document_folder_urls(client)` helper | New function that returns a list of `(program, url)` tuples. For each of the client's active enrolments where the program has a `sharepoint_url_template`, generate the URL using `urllib.parse.quote(client.record_id)` for URL encoding. Keep the old `get_document_folder_url(client)` as a compatibility wrapper that returns the first match (avoids breaking existing call sites during transition). |
| B2 | Update `get_document_storage_info()` helper | Change to return info based on whether any active programs have SharePoint templates configured, rather than global setting. |
| B3 | Update `_client_layout.html` | Replace single Documents button with per-program buttons. For each of the client's active program enrolments where the program has a `sharepoint_url_template`, show a button: "Documents ([Program Name])". If only one program has SharePoint configured, show just "Documents" (no program label needed). |
| B4 | Update client detail view context | In `apps/clients/views.py`, pass a list of `(program, url)` tuples instead of a single `document_folder_url`. Call `get_document_folder_urls(client)`. |
| B5 | Update context processor | Modify `document_storage()` in `konote/context_processors.py` to reflect that document storage is now per-program. The `is_configured` flag should be True if any active program has a SharePoint template. |
| B6 | Hide global document settings from admin UI | Remove `document_storage_provider` and `document_storage_url_template` from `InstanceSettingsForm` SETTING_KEYS list. Keep database rows for backward compatibility. This makes the transition atomic — no confusing window with both settings visible. |
| B7 | Add "client folder checklist" admin action | On the program admin page, add a "Download folder checklist" action that generates a printable list: Record ID, Client Name, for all active clients in that program. Program managers use this to cross-reference against SharePoint and create any missing folders. Low-tech fallback for agencies without Power Automate. |
| B8 | Add "participants without document folders" indicator | On the program dashboard (or program detail page), show a count of active enrolments where the Google Drive URL is blank: "X participants without document folders." Visible to program managers. Links to the list. |
| B9 | Tests for staff UI | Test: button shows per program, button hidden when no template, button hidden for receptionist, multiple programs show multiple buttons, single program omits program label, URL-encoded Record IDs work correctly, global settings hidden from admin, folder checklist generates correctly. |

**Exit criteria:** Staff see per-program SharePoint buttons on client records. Old global button replaced. Global settings hidden from admin. Folder checklist available. Data quality indicator shows missing document folders.

### Phase C: Portal UI — Google Drive Documents Card

Depends on Phase A. Can run in parallel with Phase B.

| Task | Summary | Details |
|------|---------|---------|
| C1 | Add document URLs to portal dashboard context | In `apps/portal/views.py` dashboard view, query participant's active enrolments, filter to those with `document_folder_url` set. Return list of `(program_display_name, url)`. Use `program.portal_display_name` if set, else `program.translated_name`. |
| C2 | Add "Your Documents" card to portal dashboard | In `templates/portal/dashboard.html`, add a new card in the nav cards section. Show if any active enrolment has a Google Drive URL. If one program: direct link with label "Your [Program Name] Documents". If multiple: show multiple cards or a card with sub-links, each labelled by program. Include brief description: "Your workspace — files, budgets, and tools shared with your [worker_term]." |
| C3 | Add Google Drive URL management for staff | In the staff-side enrolment management UI (wherever staff edit `ClientProgramEnrolment`), add the Google Drive folder URL field. Only editable by staff/program_manager roles — participants cannot change this. |
| C4 | Feature toggle | Add `portal_documents` feature toggle (default: enabled). Card only shows when toggle is on. Follows existing pattern with `features.portal_journal`, `features.portal_messaging`. |
| C5 | Portal template i18n | Add `{% trans %}` tags for all new strings. "Your [Program] Documents", "Your workspace — files, budgets, and tools shared with your [worker]", discharge messaging. |
| C6 | Tests for portal UI | Test: card shows when URL configured, card hidden when no URL, card hidden when toggle off, multiple programs show multiple links, labels include program name, correct program_display_name used. |

**Exit criteria:** Participants see "Your Documents" card in portal dashboard when a Google Drive URL is configured on their enrolment.

### Phase D: Security + Discharge Workflow

Depends on Phases B and C.

| Task | Summary | Details |
|------|---------|---------|
| D1 | Extend security audit command | In `apps/audit/management/commands/security_audit.py`, add checks for per-program SharePoint URLs (HTTPS, domain allowlist, `{record_id}` placeholder, no OneDrive URLs) and enrolment Google Drive URLs (HTTPS, domain allowlist, folder URL format). Domain allowlist is the enforcement point for custom domains and GCC tenants. |
| D2 | Audit logging for document link access | Log to audit DB when a staff member clicks a SharePoint link or when a participant views a Google Drive link. Include user, client, program, timestamp. Use HTMX-enhanced link: opens URL in new tab AND sends lightweight POST to KoNote for the audit log. |
| D3 | Add discharge checklist item | In the discharge/unenrolment workflow, add a checkbox: "I have transferred Google Drive ownership and removed my access". Display only when the enrolment has a `document_folder_url`. Include help text with micro-tutorial or link to Google's ownership transfer instructions. |
| D4 | Staff reminder on program role changes | When a staff member is added to or removed from a program (in `UserProgramRole`), show a reminder: "Remember to update SharePoint group membership for [Program Name]". Can be a Django message (flash notification). |
| D5 | URL validation management command | Extend `check_document_url` to validate per-program SharePoint templates and per-enrolment Google Drive URLs. Flag broken patterns, non-HTTPS, disallowed domains. Optional `--check-reachable` flag to HTTP HEAD rendered URLs with a known Record ID. |
| D6 | Security + workflow tests | Test: audit log written on link access, discharge checklist appears when URL exists, checklist hidden when no URL, staff reminder fires on role change, security audit catches bad URLs (including OneDrive, non-HTTPS). |

**Exit criteria:** All security checks pass. Discharge workflow includes handoff checklist. Audit trail complete.

### Phase E: Documentation + Cleanup

Depends on all prior phases.

| Task | Summary | Details |
|------|---------|---------|
| E1 | SharePoint setup guide | Step-by-step: creating document libraries per program, folder naming by Record ID, **use short English-only names for SharePoint library URL paths** (display name can be French — path should be English to avoid URL-encoding issues), SharePoint group configuration. Power Automate flow for automated folder creation: clearly state this is **strongly recommended from day one**, include licensing requirements (standard connectors, included in most nonprofit M365 plans). Include "What to do if your SharePoint site URL changes" — update all program templates via admin UI. |
| E2 | Google Drive setup guide | **Shared service account** (`clientdocs@agency.org`) marked as **strongly recommended** for agencies with >20% annual staff turnover (which is most Ontario nonprofits). Template folder approach: program manager creates master folder, workers copy per participant. Starter kit guidance: start with 4–7 key resources, add based on individual client needs. Include "Ask the participant to add the shared folder to their My Drive" step during intake (avoids the "Shared with me" trap where participants lose track of the folder). Ownership transfer micro-tutorial with screenshots or link to Google support. |
| E3 | Discharge checklist documentation | Explain the Google Drive handoff process for agency training materials. Include: transfer ownership (step-by-step), remove worker access, verify participant can still access. Note: checkbox is self-reported compliance — automated follow-up is a future enhancement. |
| E4 | Retention policy template | Template document for agencies: retention periods by document type (7-year minimum for PHIPA health information custodians), who is responsible for deletion after retention period, how deletion is documented (audit trail). Reference PHIPA s. 13. |
| E5 | Troubleshooting decision tree | "Staff can't see documents" → SharePoint or Google Drive? → SharePoint: check group membership, verify URL template, check folder exists → Google Drive: check sharing settings, check ownership. Prevents "call KoNote support for a SharePoint problem" pattern. |
| E6 | French translations | Run `translate_strings`, fill French translations for all new strings, recompile. |

**Exit criteria:** Documentation complete, including SharePoint and Google Drive setup guides with operational recommendations. Global settings fully deprecated. Translations done.

## Parallel Work Analysis

| Phase | Dependencies | Parallelisable? |
|-------|-------------|----------------|
| A (Foundation) | None | No — must go first, must be fully merged before B/C start |
| B (Staff UI) | A | Yes — parallel with C |
| C (Portal UI) | A | Yes — parallel with B |
| D (Security) | B + C | No — needs both B and C done |
| E (Docs + Cleanup) | D | No — needs everything done |

**Phases B and C can be built by parallel agents** after Phase A is fully merged and tested. They touch different files:
- Phase B: `apps/clients/helpers.py`, `apps/clients/views.py`, `templates/clients/_client_layout.html`, `konote/context_processors.py`, `apps/admin_settings/forms.py`
- Phase C: `apps/portal/views.py`, `templates/portal/dashboard.html`, `apps/portal/` templates

No shared file conflicts between B and C.

## Files Touched

| File | Phase | Change |
|------|-------|--------|
| `apps/programs/models.py` | A | Add `sharepoint_url_template` field, `clean()` validation |
| `apps/clients/models.py` | A | Add `document_folder_url` URLField to `ClientProgramEnrolment`, `clean()` validation; add Record ID format validator to `ClientFile` |
| `apps/programs/forms.py` | A | Add SharePoint URL template to program form with "Test URL" button |
| `apps/clients/helpers.py` | B | Add `get_document_folder_urls(client)`, keep old function as wrapper, add `urllib.parse.quote()` for Record ID encoding |
| `apps/clients/views.py` | B | Pass per-program document URLs to template |
| `templates/clients/_client_layout.html` | B | Per-program SharePoint buttons |
| `konote/context_processors.py` | B | Update `document_storage()` |
| `apps/admin_settings/forms.py` | B | Hide deprecated global document settings |
| `apps/portal/views.py` | C | Add document URLs to dashboard context |
| `templates/portal/dashboard.html` | C | Add "Your Documents" card |
| `apps/audit/management/commands/security_audit.py` | D | Extend document storage checks |
| `apps/admin_settings/management/commands/check_document_url.py` | D | Extend URL validation |
| `locale/fr/LC_MESSAGES/django.po` | E | French translations |

## URL Validation Summary

Validation is applied at **two levels** — model-level `clean()` methods (enforced everywhere) and the security audit command (enforced at audit time).

| Check | Where | What |
|-------|-------|------|
| HTTPS required | Model `clean()` | Both SharePoint templates and Google Drive URLs |
| `{record_id}` placeholder required | Model `clean()` | SharePoint templates only |
| OneDrive rejection | Model `clean()` | Reject `-my.sharepoint.com` and `/personal/` with clear error message |
| Google Drive folder format | Model `clean()` | Must start with `https://drive.google.com/drive/folders/` |
| Record ID format | Model validator | Only letters, numbers, hyphens, underscores, dots |
| Domain allowlist | Security audit | sharepoint.com, drive.google.com, onedrive.live.com + custom domains |
| URL reachability | Management command | Optional `--check-reachable` flag |

**Why validation is split:** Form validation rejects common mistakes (OneDrive URLs, missing placeholders). Domain allowlist stays in the security audit because agencies may use custom SharePoint domains, GCC/GCCHigh tenants (`*.sharepoint.us`), or vanity URLs. Hardcoding `*.sharepoint.com` in form validation would reject legitimate configurations.

## Known Limitations

1. **No automatic folder creation** — KoNote cannot create SharePoint folders or Google Drive folders. Staff must create them manually (or use Power Automate for SharePoint). The "client folder checklist" admin action (B7) is the fallback for agencies without Power Automate.
2. **No permission sync** — KoNote does not manage SharePoint groups or Google Drive sharing. Agencies must maintain these manually. The staff reminder (D4) mitigates but doesn't eliminate this gap.
3. **No broken link detection** — KoNote doesn't know when a SharePoint folder has been renamed, moved, or deleted. The management command with `--check-reachable` (D5) can detect this at audit time, but there's no real-time feedback. Future enhancement: nightly health check.
4. **Google Drive ownership transfer is self-reported** — The discharge checklist (D3) is a checkbox. KoNote cannot verify that the worker actually transferred ownership. Future enhancement: automated 7-day follow-up reminder.
5. **One SharePoint library per program** — If a program needs multiple SharePoint libraries (e.g., intake documents vs. case notes), they must use a parent folder. Documented as a known limitation; revisit if agencies request it.
6. **SharePoint site migrations break all URLs** — If an agency moves their SharePoint site to a new URL, all program templates must be updated manually. Documentation (E1) includes "What to do if your SharePoint site URL changes."

## Expert Panel Findings Summary

The implementation plan was reviewed by a 4-expert panel. Key changes incorporated:

| Finding | Source | Change Made |
|---------|--------|-------------|
| Don't encrypt Google Drive URL — it's an opaque ID, not PII | Django Integration Engineer | Changed from encrypted BinaryField to URLField |
| Increase max_length to 1000 for SharePoint URLs | SharePoint Platform Architect | Changed from 500 to 1000 |
| Don't hardcode `*.sharepoint.com` — custom domains, GCC tenants exist | SharePoint Platform Architect | Moved domain check to security audit; model validates HTTPS + `{record_id}` + no OneDrive |
| Reject OneDrive URLs with specific error message | Nonprofit IT Operations Manager | Added OneDrive detection (`-my.sharepoint.com`, `/personal/`) to model validation |
| URL-encode Record IDs before URL substitution | SharePoint Platform Architect + Systems Thinker | Added `urllib.parse.quote()` to helper; added Record ID format validator |
| Add model-level validation, not just form validation | Django Integration Engineer | Added `clean()` methods to Program and ClientProgramEnrolment |
| Make global→per-program transition atomic | Systems Thinker | Hide global settings in Phase B (not E); migration helper in Phase A |
| Add "Test URL" button for admin verification | SharePoint Platform Architect | Added to Phase A4 |
| Add data quality indicator for missing document folders | Systems Thinker | Added as Phase B8 |
| Add client folder checklist admin action | Django Integration Engineer + Operations Manager | Added as Phase B7 |
| Keep old helper as compatibility wrapper | Django Integration Engineer | Added to Phase B1 |
| Advise English-only SharePoint library URL paths | Nonprofit IT Operations Manager | Added to Phase E1 documentation |
| Mark shared Google account as strongly recommended | Nonprofit IT Operations Manager | Added to Phase E2 documentation |
| Add troubleshooting decision tree | Systems Thinker | Added as Phase E5 |
