# PHIPA Cross-Program Consent Enforcement — Design

Task ID: PHIPA-ENFORCE1
Date: 2026-02-20
Status: Approved design (expert panel review)

---

## Problem

When a client is enrolled in multiple programs and a staff member has access to more than one of those programs, clinical notes from ALL shared programs are visible on the notes timeline. Under PHIPA (Ontario's Personal Health Information Protection Act), clinical information should only be shared across program boundaries when appropriate consent exists.

The `cross_program_sharing_consent` field already exists on `ClientFile` but is **not enforced** in any view.

## Expert Panel Findings

An expert panel (healthcare privacy, security architecture, Django architecture, systems thinking) identified these key points:

1. **PHIPA does not mandate per-client consent for intra-agency sharing.** The agency is a single health information custodian. Cross-program sharing within one agency is internal use, not disclosure. Per-client consent is a best-practice enhancement, not a legal requirement.

2. **Per-client-only enforcement is too complex** for nonprofit staff. Default-False means agencies that never configure the setting accidentally over-restrict their own staff, generating confusion.

3. **The right design is an agency-level toggle (default: share) with per-client overrides** for exceptional cases. One decision by the admin, rare per-client overrides.

4. **Enforcement must be at the query layer**, not templates. Every code path that displays note content needs the same filter.

5. **De-identified aggregates and self-authored notes are exempt.** Dashboard counts aren't PHI. Follow-ups authored by the current user are in the same circle of care.

## Design

### Agency-Level Setting

Add `cross_program_note_sharing` to the existing `FeatureToggle` system:
- Added to `DEFAULT_FEATURES` in `apps/admin_settings/views.py`
- Added to `FEATURES_DEFAULT_ENABLED` (default ON — notes shared across programs)
- Toggled via the existing Features admin page
- Cached via existing `_get_feature_flags()` (300s TTL)

### Per-Client Override

Change `ClientFile.cross_program_sharing_consent` from BooleanField to CharField with three states:

```python
SHARING_CHOICES = [
    ("default", _("Follow agency setting")),
    ("consent", _("Share across programs")),
    ("restrict", _("Restrict to one program")),
]
cross_program_sharing = models.CharField(
    max_length=20, choices=SHARING_CHOICES, default="default",
    help_text="Controls whether notes are visible across programs for this client.",
)
```

Data migration: `False` → `"default"`, `True` → `"consent"`.

### Enforcement Logic

```python
def should_share_across_programs(client, agency_shares_by_default):
    if client.cross_program_sharing == "consent":
        return True   # Explicit opt-in, always share
    if client.cross_program_sharing == "restrict":
        return False  # Explicit opt-out, never share
    return agency_shares_by_default  # "default" → follow agency toggle
```

When sharing is OFF for a client, the "viewing program" is determined by:
1. CONF9 context switcher (if active with a specific program) → use that program
2. Fallback → `get_author_program(user, client)` (picks highest-ranked shared program)

### Helper Function

In `apps/programs/access.py`:

```python
def apply_consent_filter(notes_qs, client, user, user_program_ids):
    """Apply PHIPA cross-program consent filtering to a notes queryset.

    Returns (filtered_queryset, viewing_program_name_or_None).
    viewing_program_name is set when filtering is active (for template indicator).
    """
    from apps.clients.dashboard_views import _get_feature_flags
    flags = _get_feature_flags()
    agency_shares = flags.get("cross_program_note_sharing", True)

    if should_share_across_programs(client, agency_shares):
        return notes_qs, None  # No additional filtering

    # Determine viewing program
    viewing_program = get_author_program(user, client)
    if viewing_program:
        filtered = notes_qs.filter(
            Q(author_program=viewing_program) | Q(author_program__isnull=True)
        )
        return filtered, viewing_program.name
    return notes_qs, None
```

### Enforcement Points

| View | Action | Rationale |
|------|--------|-----------|
| `note_list()` in `apps/notes/views.py` | Apply `apply_consent_filter()` | Primary clinical content display |
| Note detail views (direct URL access) | Verify note's author_program is accessible | Prevent URL bypass |
| Home dashboard counts | No filter | Counts aren't PHI |
| `pending_follow_ups` on home | No filter | User is the author |
| Executive dashboard | No filter | De-identified aggregates |
| Plan views | No filter | Already program-scoped via PlanSection.program |

### Template Indicator

When filtering is active, show a banner on the notes timeline:

```html
{% if consent_viewing_program %}
<div class="notice" role="status">
    {% blocktrans with program=consent_viewing_program %}
    Showing notes from {{ program }} only. Cross-program sharing has not been enabled for this client.
    {% endblocktrans %}
</div>
{% endif %}
```

### What We're NOT Building

- Safety alert exception (no `safety_alert` field exists yet — deferred)
- Cross-agency sharing (that's SCALE-ROLLUP1, different custodians)
- Plan/target filtering (already program-scoped)
- Report filtering (de-identified aggregates)

### Tests

1. Agency=ON, client=default → notes from all programs visible
2. Agency=ON, client=restrict → notes filtered to viewing program
3. Agency=OFF, client=default → notes filtered to viewing program
4. Agency=OFF, client=consent → notes from all programs visible
5. Single shared program → filter is a no-op regardless of settings
6. Null author_program notes → always visible
7. Direct URL to note from another program when restricted → 403
8. Template indicator shown when filtering is active
9. Template indicator hidden when sharing is ON

### Key Files

| File | Change |
|------|--------|
| `apps/admin_settings/views.py` | Add `cross_program_note_sharing` to DEFAULT_FEATURES and FEATURES_DEFAULT_ENABLED |
| `apps/clients/models.py` | Change field from BooleanField to CharField with 3 choices, rename field |
| `apps/clients/forms.py` | Update ClientFileForm for new field type |
| `apps/clients/views.py` | Update intake view for new field |
| `apps/programs/access.py` | Add `should_share_across_programs()` and `apply_consent_filter()` |
| `apps/notes/views.py` | Apply consent filter in `note_list()` |
| `templates/notes/note_list.html` | Add consent indicator banner |
| `apps/clients/migrations/00XX_*.py` | Schema change + data migration |
| `tests/test_cross_program_security.py` | Add 9 consent enforcement tests |

### Known Limitation

"Information laundering" — a staff member in both programs who reads notes in one context may reference that information when creating a note in another context. PHIPA does not attempt to control what clinicians remember; it controls what the system discloses. This is documented, not solvable in software.
