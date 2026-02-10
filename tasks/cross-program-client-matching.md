# Cross-Program Client Matching & Confidential Program Isolation

**Status:** Design complete (4 expert panels). Ready for implementation planning.
**Created:** 2026-02-06
**Task IDs:** MATCH1-6, CONF1-7

---

## The Problem

When one staff member creates a client in their program, another staff member in a different program has no way to know that client already exists. They may create a duplicate record. But solving this creates a dangerous privacy problem: in multi-service agencies, a person might have a casual sports membership AND be receiving addiction counselling or domestic violence support. The front desk staff checking them in for basketball must never learn they are in a sensitive program.

## Design Decision (From 4 Expert Panels)

Two features, designed together:

1. **Duplicate detection for Standard programs** — phone + name + DOB matching on client creation, with banners showing possible matches
2. **Confidential program isolation** — sensitive programs (counselling, addiction, mental health, DV) are completely invisible to staff in other programs, with no cross-program matching whatsoever

### Why One System, Not Two

The expert panels initially recommended DV programs use a separate system. The product owner challenged this. After analysis:

- **Penelope, HIFIS, and Apricot** all serve DV programs alongside other services in the same database today. This is established sector practice in Canada.
- A "separate system" in a 15-person agency usually means a password-protected Excel on a laptop — far less secure than a properly implemented confidential tier.
- One system with proper isolation is more secure, more reliable, and more maintainable than two systems where one gets neglected.
- Legally defensible under PHIPA, PIPEDA, and FIPPA, provided safeguards are in place.

**Separate KoNote instance** is recommended only for the rare case where a known threat actor has administrative access to the agency's hosting platform itself.

---

## Two Program Types

### Standard Programs
- Gym, sports, employment, settlement, housing, food bank, tutoring, youth programs
- Cross-program matching: **enabled automatically**
- Staff in any Standard program can discover clients in other Standard programs via matching
- No consent form required — matching is a notification, not a request

### Confidential Programs
- Counselling, mental health, addiction, sexual health, HIV/AIDS, DV support, youth justice
- Cross-program matching: **completely disabled**
- Clients are invisible to all staff outside the specific confidential program
- Cannot be searched, matched, merged, or discovered through any system path
- No banners, no match counts, no "results may be incomplete" hints
- Superuser/admin cannot browse confidential client records
- Client-initiated linking only (verbal, through their counsellor)

---

## Data Model Changes

### New field on Program model

```python
class Program(models.Model):
    # ... existing fields ...
    is_confidential = models.BooleanField(
        default=False,
        help_text="Confidential programs are invisible to staff in other programs."
    )
```

- Set at program creation via guided question (not a raw checkbox)
- Can only be changed from Standard to Confidential, never the reverse (without formal PIA)
- Default is Standard (False), but the system suggests Confidential when program name contains keywords like counselling, mental health, addiction, sexual health, support, outreach

### Guided setup question (admin UI)

> **Is this a confidential program?**
> Confidential programs are for sensitive services like counselling, mental health, addiction, or domestic violence support. Clients in confidential programs will not appear in searches or records from other programs.
> [ ] Yes, this is a confidential program

### Matching fields (Standard programs only)

Matching runs against the client's own `ClientFile` record only:
- Phone number (exact match — primary)
- First name + date of birth (first 3 chars of first name, case-insensitive — secondary)

**Explicitly excluded from matching** (to prevent family-member disclosure):
- Emergency contact names and phone numbers
- Case note content
- Custom field values
- Addresses
- Any related-record fields

### Query filtering changes

`get_client_queryset()` must be updated to be tier-aware:

```python
def get_client_queryset(user, active_role=None):
    """Return clients visible to this user in their current role."""
    role = active_role or user.current_role
    accessible_programs = get_user_programs(user, role)

    # Staff in non-confidential programs never see confidential clients
    if not any(p.is_confidential for p in accessible_programs):
        accessible_programs = accessible_programs.filter(is_confidential=False)

    client_ids = ClientProgramEnrolment.objects.filter(
        program__in=accessible_programs,
        status="enrolled"
    ).values_list("client_file_id", flat=True)

    return get_base_queryset(user).filter(pk__in=client_ids)
```

The matching query adds an additional filter:
```python
# Only match against Standard program clients
.exclude(clientprogramenrolment__program__is_confidential=True)
```

---

## Duplicate Detection UX (Standard Programs Only)

### On client create form

| Step | What happens | What staff see |
|------|-------------|----------------|
| Staff enters phone number | System checks phone against all Standard-program clients | Background, no UI yet |
| Match found (same phone) | Banner appears | "A client with this phone number already has a record. [View existing record] or [Create new anyway]" |
| Staff enters name + DOB (no phone match) | System checks first name + DOB against Standard clients | Same banner if match found |
| No match | Nothing — zero friction | Normal create flow |
| Client is in a Confidential program | **Invisible. Never matched.** | Staff sees nothing |

### Banner design

Non-blocking. Not a modal. A gentle notice at the top of the form:

> "A client with this phone number already has a record in [Program Name]."
> [View existing record] [Create new record anyway]

If the match is name+DOB (weaker signal):

> "A client with a similar name and date of birth already has a record."
> [Check existing records] [Continue creating new record]

### Merge tool (Phase 4 — later)

For Standard program admins only. Shows possible duplicate pairs. Side-by-side comparison. Merged record keeps all notes, events, enrolments. Archived record marked "merged into [Record ID]."

The merge tool's candidate query explicitly excludes confidential programs — it physically cannot propose a merge involving a confidential client.

---

## Confidential Program Safeguards

### 5 Non-Negotiable Conditions

These must ALL be met before confidential programs can be used for DV or other high-stakes services:

**1. Superuser/admin cannot see confidential client records.**

Custom Django admin class filters confidential records:
```python
class ClientFileAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not user_has_confidential_access(request.user):
            qs = qs.exclude(programs__is_confidential=True)
        return qs
```

The admin/ED can see that a confidential program *exists* (name only) and aggregate client count (if >= 10 clients; otherwise shows "< 10" to prevent inference). They cannot browse individual records.

**2. Every access to a confidential client record is logged.**

Immutable audit trail in the separate audit database:
- Who accessed (user ID, username, role)
- When (timestamp)
- Which record (client ID)
- What action (view, edit, create, delete)
- Not deletable by the person being audited
- DV program manager can pull an access report for any client at any time

**3. Comprehensive test suite proves the boundary holds.**

A dedicated test file: `tests/test_confidential_isolation.py`

Must test EVERY code path:
- Client list view excludes confidential clients
- Client search excludes confidential clients
- Client detail returns 403 for non-confidential users
- Duplicate matching excludes confidential clients
- Merge tool candidates exclude confidential clients
- Django admin excludes confidential clients
- API endpoints (if any) exclude confidential clients
- Aggregate reports use small-cell suppression
- No timing differences between searches with/without confidential matches

This test file is marked as critical — CI blocks deployment if any test fails.

**4. PIA template ships with the feature.**

A pre-filled Privacy Impact Assessment template that walks the agency through:
1. What data does KoNote collect? (Pre-filled from configuration)
2. Who has access? (Pre-filled from user roles and program assignments)
3. What are the safeguards? (Pre-filled: encryption, audit logging, confidential isolation)
4. What are the residual risks? (Pre-filled honestly: hosting provider access, credential compromise)
5. What mitigations are in place? (Pre-filled: encrypted fields, query-level filtering, annual review)

**5. Documentation is honest about boundaries.**

States clearly what the system does and doesn't protect against:
- Protects against: system-level disclosure via search, matching, merging, admin browsing
- Does NOT protect against: physical co-location risks, credential theft, hosting provider access
- Separate instance recommended when: threat actor has hosting platform admin access

---

## Edge Cases Resolved by the Design

### Family members across tiers
A mother in DV counselling (Confidential), her child in after-school (Standard). The after-school worker enters the mother's phone as emergency contact. Because emergency contacts are excluded from matching, and because matching never searches Confidential clients, no disclosure occurs.

### Client graduating between tiers
A client completes addiction counselling (Confidential) and moves to employment support (Standard). Their record must be manually migrated — the client actively participates in this decision. The counsellor and employment worker coordinate with the client present.

### Multi-role staff
A person who is both an addiction counsellor and a basketball referee has two roles. When they log in, they select which role they're working in. The UI, search results, and client list reflect that single role. Switching requires an explicit action.

### Absence of results reveals nothing
If a staff member searches for "Jane Smith" and gets zero results, the UI simply says "No results found." Never: "No results found (some programs may not be included)" or any hint that hidden data exists.

### Neutral program names
DV programs can be named "Community Support Services" or any neutral name. Since confidential clients are invisible to other programs, the program name is never shown outside its own staff anyway.

---

## Consent Model

### Standard programs: No consent form needed
Matching is automatic. The worker sees a notification:
> "This client is being enrolled in [Employment Services]. The system will check if they already have a record in other standard programs. No information from confidential programs will be checked or shared."

### Confidential programs: No matching, no consent needed for matching
The worker sees:
> "This client is being enrolled in [Counselling Services], which is a confidential program. Their record will not appear in any searches from other programs."

### Cross-tier linking: Client-initiated only
If a client wants their addiction counsellor to know about their employment program record, the client tells their counsellor verbally. The counsellor contacts the other program. The system does not facilitate this — the client's own voice does.

No consent checkbox. No consent form for matching. The only consent that matters is a human conversation in a trust relationship.

---

## What Existing Systems Do (Comparison)

| System | Same-DB DV support? | Matching | Confidential isolation |
|--------|---------------------|----------|----------------------|
| Penelope | Yes | Name + DOB search on intake, manual | "Confidential program" visibility flag |
| HIFIS | Yes | Manual merge by admin | Consent directives |
| Apricot | Yes | Master client index (admin-only) | Form-level permissions |
| EMHware | N/A (clinical only) | None (clinician-managed caseloads) | Per-clinician isolation |
| **KoNote (proposed)** | **Yes** | **Automatic phone + name + DOB** | **Query-level filtering + admin isolation + audit** |

KoNote's duplicate detection would be more sophisticated than any current Canadian nonprofit case management system. The confidential program isolation matches sector standard (Penelope) and exceeds it with admin filtering, audit logging, and comprehensive testing.

---

## Legal & Regulatory Basis (Ontario)

- **PHIPA (Personal Health Information Protection Act):** Requires access controls commensurate with sensitivity, audit logging, breach notification. Met by the design.
- **PIPEDA:** Requires limiting collection, use, and disclosure. Met by program-scoped access.
- **FIPPA:** Requires reasonable safeguards against unauthorized access. Met by query-level filtering + encryption.
- **No Ontario statute requires a physically separate database for DV programs.** The requirement is adequate safeguards, which this design provides.
- **A Privacy Impact Assessment is required** when introducing new technology for personal health information. KoNote ships a PIA template.

---

## Build Phases

| Phase | Tasks | Priority | IDs |
|-------|-------|----------|-----|
| **1: Foundation** | `Program.is_confidential` field, guided setup, query filtering | Must-have | CONF1-3 |
| **2: Matching** | Phone-based duplicate detection on Standard client create | Must-have | MATCH1-2 |
| **3: Secondary matching** | Name + DOB matching as fallback | Should-have | MATCH3 |
| **4: Merge tool** | Duplicate merge for Standard program admins | Should-have | MATCH4 |
| **5: Audit + admin isolation** | Immutable audit logging, admin view filtering, small-cell suppression | Must-have (before DV use) | CONF4-5 |
| **6: DV readiness** | PIA template, documentation, annual review checklist, test suite | Must-have (before DV use) | CONF6-7, MATCH5-6 |
| **7: Role selector** | Multi-role staff session switching | Nice-to-have | CONF8 |

---

## Implementation Rules

1. **`is_confidential` is one-way.** Can move Standard to Confidential, never the reverse without formal PIA.
2. **Default for new programs is Standard.** Confidential is suggested when name contains sensitive keywords.
3. **No "god mode" admin.** No single account can browse across confidential tier boundaries.
4. **Absence of results is normal.** UI never hints at hidden data.
5. **Merge tool enforces tier boundaries at the code level.** Cannot even propose a merge involving a confidential client.
6. **Emergency contacts excluded from matching.** Prevents family-member disclosure.
7. **Address never used as matching field.** Too many shared within households.
8. **Tests are the security contract.** `test_confidential_isolation.py` blocks deployment if any test fails.

---

## Documentation to Ship

### For agencies (in-app help or user guide)

> **Confidential Programs**
>
> KoNote supports confidential programs for sensitive services including counselling, mental health, addiction, sexual health, and domestic violence support. Clients in confidential programs are completely invisible to all staff outside that program — they cannot be searched, matched, merged, or discovered through any part of the system.
>
> This design aligns with how leading Canadian case management systems handle sensitive programs and meets Ontario privacy law requirements (PHIPA, PIPEDA).
>
> Before activating a confidential program, your agency should complete a Privacy Impact Assessment. KoNote provides a template pre-filled with your configuration.
>
> For the rare case where a known threat actor has administrative access to your agency's hosting platform, we recommend a separate KoNote instance with independent hosting credentials.

### For developers (in CLAUDE.md or technical docs)

Security invariant: Confidential program clients must NEVER appear in any query, search, match, merge, admin view, report, or error message accessible to users without explicit confidential program access. This is enforced by query-level filtering and verified by `tests/test_confidential_isolation.py`. This test file must never be deleted or have tests skipped.
