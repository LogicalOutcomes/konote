# Implementation Plan: Dual Document Integration (SharePoint + Google Drive)

**Date:** 2026-02-27
**Status:** Draft — pending PB/SG approval of design rationale (DOC-INTEG1)
**Design rationale:** `tasks/design-rationale/document-integration.md`
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
    max_length=500, blank=True, default="",
    help_text=_("SharePoint folder URL with {record_id} placeholder. "
                "Example: https://contoso.sharepoint.com/sites/konote/YouthEmployment/{record_id}/"),
)
```

**Why on Program, not a separate model:** Each program has at most one SharePoint library. A CharField on the existing model is simpler than a new join table. The field is blank by default — programs with no SharePoint integration just leave it empty.

### B. ClientProgramEnrolment model — add Google Drive folder URL

Add to `apps/clients/models.py` → `ClientProgramEnrolment`:

```python
_document_folder_url_encrypted = models.BinaryField(
    null=True, blank=True, db_column="document_folder_url_encrypted",
)
```

With a property accessor (consistent with other PII fields):

```python
@property
def document_folder_url(self):
    if self._document_folder_url_encrypted:
        return decrypt(self._document_folder_url_encrypted)
    return ""

@document_folder_url.setter
def document_folder_url(self, value):
    if value:
        self._document_folder_url_encrypted = encrypt(value)
    else:
        self._document_folder_url_encrypted = None
```

**Why encrypted:** The URL encodes program membership (which program the client is in) and potentially contains the client's email if they use a personal Google Drive. Treat as PII — consistent with KoNote's approach to other identifying data.

**Why on enrolment, not client:** A client in two programs may have two different Google Drive folders with different resource kits. One link per enrolment keeps it clean.

### C. Global settings — deprecation path

The existing global `document_storage_provider` and `document_storage_url_template` in `InstanceSetting` will be deprecated in favour of per-program fields. Migration path:

1. If the global setting is configured and no programs have `sharepoint_url_template` set, copy the global template to all active programs (one-time migration helper)
2. Keep the global settings readable for backward compatibility during the transition
3. Remove global settings in a future cleanup phase

## Implementation Phases

### Phase A: Data Model + Admin UI (Foundation)

Must be done first. All other phases depend on this.

| Task | Summary | Details |
|------|---------|---------|
| A1 | Add `sharepoint_url_template` to Program model | CharField(max_length=500, blank=True). Run makemigrations + migrate. |
| A2 | Add `_document_folder_url_encrypted` to ClientProgramEnrolment | BinaryField(null=True, blank=True). Add property accessor with encrypt/decrypt. Run makemigrations + migrate. |
| A3 | Add SharePoint URL template field to program admin form | In `apps/programs/forms.py` (or create if needed). Only visible to program_manager and admin roles. Include URL validation (must match `https://*.sharepoint.com/*` and contain `{record_id}`). |
| A4 | Add Google Drive URL field to enrolment management | Where staff manage a client's program enrolment, add a "Google Drive Folder URL" field. Validate format: must match `https://drive.google.com/drive/folders/*`. |
| A5 | Write migration helper for global→per-program transition | Management command `migrate_document_settings` that copies global `document_storage_url_template` to all active programs' `sharepoint_url_template` if it's a SharePoint URL. Dry-run mode. |
| A6 | Tests for models and forms | Test encrypted field round-trip, URL validation (valid/invalid patterns), migration helper (both providers, edge cases). |

**Exit criteria:** Models migrated, admin forms working, all A-phase tests pass.

### Phase B: Staff UI — Per-Program SharePoint Buttons

Depends on Phase A.

| Task | Summary | Details |
|------|---------|---------|
| B1 | Update `get_document_folder_url()` helper | Change signature to `get_document_folder_url(client, program)`. Generate URL from `program.sharepoint_url_template` instead of global setting. Return None if template is empty or client has no record_id. |
| B2 | Update `get_document_storage_info()` helper | Change to return info based on whether any active programs have SharePoint templates configured, rather than global setting. |
| B3 | Update `_client_layout.html` | Replace single Documents button with per-program buttons. For each of the client's active program enrolments where the program has a `sharepoint_url_template`, show a button: "Documents ([Program Name])". If only one program has SharePoint configured, show just "Documents" (no program label needed). |
| B4 | Update client detail view context | In `apps/clients/views.py`, pass a list of `(program, url)` tuples instead of a single `document_folder_url`. Query the client's active enrolments, filter to programs with SharePoint templates, generate URLs. |
| B5 | Update context processor | Modify `document_storage()` in `konote/context_processors.py` to reflect that document storage is now per-program. The `is_configured` flag should be True if any active program has a SharePoint template. |
| B6 | Tests for staff UI | Test: button shows per program, button hidden when no template, button hidden for receptionist, multiple programs show multiple buttons, single program omits program label. |

**Exit criteria:** Staff see per-program SharePoint buttons on client records. Old global button replaced.

### Phase C: Portal UI — Google Drive Documents Card

Depends on Phase A. Can run in parallel with Phase B.

| Task | Summary | Details |
|------|---------|---------|
| C1 | Create portal documents view | New view in `apps/portal/views.py` — or add to existing dashboard context. Query participant's active enrolments, filter to those with `document_folder_url` set. Return list of `(program_name, url)`. |
| C2 | Add "Your Documents" card to portal dashboard | In `templates/portal/dashboard.html`, add a new card in the nav cards section. Show if any active enrolment has a Google Drive URL. Card links to the folder(s). If one program: direct link. If multiple: list with program labels. |
| C3 | Add Google Drive URL management for staff | In the staff-side enrolment management UI (wherever staff edit `ClientProgramEnrolment`), add the Google Drive folder URL field. Only editable by staff/program_manager roles — participants cannot change this. |
| C4 | Feature toggle | Add `portal_documents` feature toggle (default: enabled). Card only shows when toggle is on. Follows existing pattern with `features.portal_journal`, `features.portal_messaging`. |
| C5 | Portal template i18n | Add `{% trans %}` tags for all new strings. "Your [Program] Documents", "Your workspace — files, budgets, and tools shared with your [worker]", discharge messaging. |
| C6 | Tests for portal UI | Test: card shows when URL configured, card hidden when no URL, card hidden when toggle off, multiple programs show multiple links, labels include program name. |

**Exit criteria:** Participants see "Your Documents" card in portal dashboard when a Google Drive URL is configured on their enrolment.

### Phase D: Security + Discharge Workflow

Depends on Phases B and C.

| Task | Summary | Details |
|------|---------|---------|
| D1 | Extend security audit command | In `apps/audit/management/commands/security_audit.py`, add checks for per-program SharePoint URLs (HTTPS, domain allowlist, `{record_id}` placeholder) and enrolment Google Drive URLs (HTTPS, domain allowlist, folder URL format). |
| D2 | Audit logging for document link access | Log to audit DB when a staff member clicks a SharePoint link or when a participant views a Google Drive link. Include user, client, program, timestamp. |
| D3 | Add discharge checklist item | In the discharge/unenrolment workflow, add a checkbox: "I have transferred Google Drive ownership and removed my access". Display only when the enrolment has a `document_folder_url`. Include help text with link to Google's ownership transfer instructions. |
| D4 | Staff reminder on program role changes | When a staff member is added to or removed from a program (in `UserProgramRole`), show a reminder: "Remember to update SharePoint group membership for [Program Name]". Can be a Django message (flash notification). |
| D5 | URL validation management command | Extend `check_document_url` to validate per-program SharePoint templates and per-enrolment Google Drive URLs. Flag broken patterns, non-HTTPS, disallowed domains. |
| D6 | Security + workflow tests | Test: audit log written on link access, discharge checklist appears when URL exists, checklist hidden when no URL, staff reminder fires on role change, security audit catches bad URLs. |

**Exit criteria:** All security checks pass. Discharge workflow includes handoff checklist. Audit trail complete.

### Phase E: Documentation + Cleanup

Depends on all prior phases.

| Task | Summary | Details |
|------|---------|---------|
| E1 | SharePoint setup guide | Step-by-step: creating document libraries per program, folder naming by Record ID, SharePoint group configuration, Power Automate flow for automated folder creation. Add to `docs/` or admin help pages. |
| E2 | Google Drive setup guide | Shared service account option, template folder approach, starter kit guidance (4-7 resources max). Ownership transfer micro-tutorial. |
| E3 | Discharge checklist documentation | Explain the Google Drive handoff process for agency training materials. |
| E4 | Retention policy template | Template document for agencies: retention periods by document type, deletion responsibilities, audit trail requirements. Reference PHIPA s. 13. |
| E5 | Remove deprecated global settings | Remove `document_storage_provider` and `document_storage_url_template` from `InstanceSettingsForm` and seed data. Keep `InstanceSetting` rows readable for any custom integrations but remove from admin UI. |
| E6 | French translations | Run `translate_strings`, fill French translations for all new strings, recompile. |

**Exit criteria:** Documentation complete. Global settings deprecated. Translations done.

## Parallel Work Analysis

| Phase | Dependencies | Parallelisable? |
|-------|-------------|----------------|
| A (Foundation) | None | No — must go first |
| B (Staff UI) | A | Yes — parallel with C |
| C (Portal UI) | A | Yes — parallel with B |
| D (Security) | B + C | No — needs both B and C done |
| E (Docs + Cleanup) | D | No — needs everything done |

**Phases B and C can be built by parallel agents** after Phase A completes. They touch different files:
- Phase B: `apps/clients/helpers.py`, `apps/clients/views.py`, `templates/clients/_client_layout.html`, `konote/context_processors.py`
- Phase C: `apps/portal/views.py`, `templates/portal/dashboard.html`, `apps/portal/` templates

No shared file conflicts between B and C.

## Files Touched

| File | Phase | Change |
|------|-------|--------|
| `apps/programs/models.py` | A | Add `sharepoint_url_template` field |
| `apps/clients/models.py` | A | Add encrypted `document_folder_url` to `ClientProgramEnrolment` |
| `apps/programs/forms.py` | A | Add SharePoint URL template to program form |
| `apps/clients/helpers.py` | B | Update `get_document_folder_url()` for per-program |
| `apps/clients/views.py` | B | Pass per-program document URLs to template |
| `templates/clients/_client_layout.html` | B | Per-program SharePoint buttons |
| `konote/context_processors.py` | B | Update `document_storage()` |
| `apps/portal/views.py` | C | Add document URLs to dashboard context |
| `templates/portal/dashboard.html` | C | Add "Your Documents" card |
| `apps/admin_settings/forms.py` | E | Remove deprecated global fields |
| `apps/audit/management/commands/security_audit.py` | D | Extend document storage checks |
| `apps/admin_settings/management/commands/check_document_url.py` | D | Extend URL validation |
| `locale/fr/LC_MESSAGES/django.po` | E | French translations |

## Known Limitations

1. **No automatic folder creation** — KoNote cannot create SharePoint folders or Google Drive folders. Staff must create them manually (or use Power Automate for SharePoint). This is deliberate — link-broker-only architecture.
2. **No permission sync** — KoNote does not manage SharePoint groups or Google Drive sharing. Agencies must maintain these manually. The staff reminder (D4) mitigates but doesn't eliminate this gap.
3. **Google Drive ownership transfer is a training issue** — KoNote can prompt (D3) but cannot enforce that the worker actually transfers ownership. See risk registry in design rationale.
4. **Encrypted URLs cannot be searched in SQL** — If future features need to query "all enrolments with a Google Drive URL configured", this requires loading enrolments into Python and checking in memory. Acceptable at current scale.
5. **Global settings migration is one-way** — Once per-program settings are populated, the global settings become redundant. The migration helper (A5) only copies forward, not backward.
