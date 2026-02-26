# Phase Prompt: PERM-P5 (DV-Safe Mode) + PERM-P6 (GATED Clinical Access)

**Branch:** Create from `main` after merging `feat/wp1-field-access`
**Depends on:** PERM-P8 (per-field front desk) must be merged first
**DRR:** Read `tasks/design-rationale/access-tiers.md` before starting — it contains expert panel decisions and anti-patterns

---

## Overview

Two features remain in the Access Tiers system:

1. **PERM-P5 (DV-Safe Mode)** — When a client has a DV safety flag, hide sensitive fields (address, emergency contact) from ALL front desk users. Available at Tier 2+, prompted during setup at Tier 3.

2. **PERM-P6 (GATED Clinical Access)** — At Tier 3, program managers must document a justification before they can view clinical notes, plans, or clinical data. This creates an `AccessGrant` with a time limit (default 7 days, max 30). Active only at Tier 3.

These are independent of each other — they can be built in parallel or either order.

---

## PERM-P5: DV-Safe Mode

### What to build

#### 1. Add `is_dv_safe` flag to `ClientFile` model

In `apps/clients/models.py`, add to `ClientFile`:

```python
is_dv_safe = models.BooleanField(
    default=False,
    help_text="When True, address and emergency contact fields are hidden from front desk.",
)
```

Create a migration for this.

#### 2. DV-safe hidden fields list

Define which fields are hidden when `is_dv_safe` is True. From the DRR:
- Address (not yet a core field — may be a custom field)
- Emergency contact name
- Emergency contact phone
- Employer/school

These are custom fields in most deployments. The enforcement is:
- Custom fields: check `is_dv_safe` in addition to `front_desk_access` — if DV flag is set and user is receptionist, hide the field regardless of access config
- Core fields: no change needed (core fields don't include address/emergency contact)

#### 3. Update `get_visible_fields()` on `ClientFile`

In the `receptionist` branch, add a check: if `self.is_dv_safe`, override DV-sensitive custom fields to hidden. This may need a list constant like:

```python
DV_HIDDEN_FIELD_NAMES = {"address", "emergency_contact", "emergency_phone", "employer"}
```

Actually, since DV-sensitive fields are custom fields (not core), the DV enforcement goes on the custom field rendering logic. The DRR says custom fields use `CustomFieldDefinition.front_desk_access` — the DV flag must override that to `"none"` for DV-sensitive fields when `is_dv_safe` is True.

**Decision needed (GK):** Should DV-hidden fields be specified by field name pattern matching, by a boolean flag on `CustomFieldDefinition` (e.g., `is_dv_sensitive`), or by a hardcoded list? A `is_dv_sensitive` boolean on the model is most flexible and admin-configurable.

#### 4. Setting the DV flag

- Any worker on the case can set `is_dv_safe = True` unilaterally (safety first)
- Add a button/link on the client detail page (info tab) visible to staff+ roles
- When clicked, set the flag immediately and log an audit entry
- Show a confirmation message

#### 5. Removing the DV flag (two-person rule)

Removal uses the same pattern as alert cancellation:
1. A staff member recommends removal (`dv_recommend_remove`): records who recommended it and why
2. A PM reviews and approves removal (`dv_review_remove`): sets `is_dv_safe = False`

Create a small model or use a workflow field:

```python
class DvFlagRemovalRequest(models.Model):
    client_file = models.ForeignKey(ClientFile, on_delete=models.CASCADE)
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")
    requested_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved = models.BooleanField(null=True)  # None=pending, True=approved, False=rejected
```

#### 6. Front desk invisibility

**Critical DRR requirement:** Front desk must NOT see that the flag is set. They see fields disappear without knowing why. The `is_dv_safe` flag should not appear in any template rendered for receptionist role.

If the DV check query fails (database error), default to hiding the fields (fail closed).

#### 7. Tier gating

- Tier 1: DV-safe mode not available (hide the button/controls)
- Tier 2: Available on request (admin or staff can enable per client)
- Tier 3: Prompted during setup wizard (agency identifies DV-sensitive programs)

#### 8. Views and URLs

Add to `apps/clients/urls.py`:
- `POST /clients/<id>/dv-safe/enable/` — set the flag
- `POST /clients/<id>/dv-safe/request-remove/` — staff recommends removal
- `POST /clients/<id>/dv-safe/review-remove/<request_id>/` — PM approves/rejects

#### 9. Template changes

In `templates/clients/_tab_info.html`:
- Wrap DV-sensitive custom field sections with a check
- Show "Set DV-Safe" button for staff+ at Tier 2+ (hidden from receptionist)
- Show pending removal requests for PM

#### 10. Tests

Create `tests/test_dv_safe.py`:
- Setting DV flag hides fields from receptionist
- DV flag has no effect on staff visibility
- Removal requires two-person rule  
- Front desk cannot see DV flag status
- Fail closed on error
- DV controls hidden at Tier 1

---

## PERM-P6: GATED Clinical Access

### What to build

#### 1. Create `AccessGrant` model

In `apps/auth_app/models.py`, add:

```python
class AccessGrant(models.Model):
    """Records a PM's documented justification for viewing clinical data.
    
    Only used at Tier 3 (Clinical Safeguards). At Tiers 1-2, GATED
    permissions are relaxed to ALLOW automatically by the decorator.
    
    Two grant scopes:
    - Program-level: grants access to all clinical data in a program (routine supervision)
    - Client-level: grants access to a specific client's clinical data (cross-program)
    """
    
    REASON_CHOICES = [
        ("supervision", _("Clinical supervision")),
        ("complaint", _("Complaint investigation")),
        ("safety", _("Safety concern")),
        ("quality", _("Quality assurance")),
        ("intake", _("Intake / case assignment")),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_grants")
    program = models.ForeignKey("programs.Program", on_delete=models.CASCADE, related_name="access_grants")
    client_file = models.ForeignKey(
        "clients.ClientFile", on_delete=models.CASCADE, 
        null=True, blank=True, related_name="access_grants",
        help_text="If null, grant covers all clients in the program.",
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    justification = models.TextField(help_text="Brief description of why access is needed.")
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        app_label = "auth_app"
        db_table = "access_grants"
        ordering = ["-granted_at"]
```

Create a migration.

#### 2. Update the GATED branch in the decorator

In `apps/auth_app/decorators.py`, the GATED branch currently treats GATED as ALLOW with a log warning. Replace with real enforcement:

```python
if level == GATED:
    from apps.admin_settings.models import get_access_tier
    tier = get_access_tier()
    if tier < 3:
        # Tiers 1-2: GATED relaxed to ALLOW
        return view_func(request, *args, **kwargs)
    
    # Tier 3: Check for active AccessGrant
    from apps.auth_app.models import AccessGrant
    from django.utils import timezone
    
    now = timezone.now()
    program = getattr(request, 'user_program', None)
    
    # Check for program-level grant
    has_grant = AccessGrant.objects.filter(
        user=request.user,
        program=program,
        is_active=True,
        expires_at__gt=now,
        client_file__isnull=True,
    ).exists()
    
    if not has_grant and get_client_fn:
        # Check for client-specific grant
        try:
            client = get_client_fn(request, *args, **kwargs)
            has_grant = AccessGrant.objects.filter(
                user=request.user,
                is_active=True,
                expires_at__gt=now,
                client_file=client,
            ).exists()
        except Exception:
            pass
    
    if has_grant:
        return view_func(request, *args, **kwargs)
    
    # No grant — redirect to justification form
    return redirect(reverse("auth_app:access_grant_request") + f"?next={request.path}&permission={permission_key}")
```

**Note:** The `get_client_fn` in the snippet above refers to the parameter already passed to `requires_permission`. You'll need to extract the client from URLs where possible.

#### 3. Justification form and view

Create `apps/auth_app/access_grant_views.py`:

- **GET** `/auth/access-grant/request/` — shows the justification form (reason dropdown, justification text, duration selector: 1/3/7/14/30 days)
- **POST** — creates the `AccessGrant`, logs an audit entry, redirects to `?next=` URL
- The clinical data must NOT load until after the reason is submitted (DRR requirement)

Create `templates/auth_app/access_grant_request.html`:
- Form with: reason dropdown, justification textarea, duration selector
- "Request Access" button
- "Cancel" link back to dashboard

#### 4. Access grant list view

Create a view showing the user's active grants (for PM to see what they have access to):
- **GET** `/auth/access-grants/` — list of active grants with expiry times
- Option to revoke (deactivate) a grant early

And an admin view:
- **GET** `/admin/settings/access-grants/` — all access grants across all users (admin only)
- Shown only at Tier 3

#### 5. URL routes

Add to `apps/auth_app/urls.py`:
```python
path("access-grant/request/", access_grant_views.access_grant_request, name="access_grant_request"),
path("access-grants/", access_grant_views.access_grant_list, name="access_grant_list"),
```

#### 6. Audit logging

Two separate audit entries (DRR requirement):
1. **Grant creation:** "PM requested clinical access to [program/client] for [reason]"
2. **Individual note/plan view:** Each view of a clinical note or plan under a GATED grant already creates an AuditLog entry through existing note views — but should tag the grant ID

Add `access_grant_id` field to `AuditLog` entries where a grant was used (optional FK or integer field).

#### 7. Permission matrix updates

In `apps/auth_app/permissions.py`, update the `program_manager` section comments:
```python
"client.view_clinical": GATED,  # Tier 3: justification + time-boxing. Tiers 1-2: relaxed to ALLOW
"note.view": GATED,  # Same enforcement as client.view_clinical
"plan.view": GATED,  # Same enforcement as client.view_clinical
```

Wait — the matrix currently has `client.view_clinical` as `ALLOW` for PM. It needs to change to `GATED` for the decorator to enforce it:
```python
"client.view_clinical": GATED,  # Tier 3: requires AccessGrant. Tiers 1-2: relaxed to ALLOW by decorator.
```

Similarly, `note.view` and `plan.view` for PM need to become GATED.

**Important:** This is a matrix change. Check all views that use `note.view` and `plan.view` permissions for PM to ensure the redirect flow works.

#### 8. Dashboard card (Tier 3 only)

Add to `templates/admin_settings/dashboard.html` (only at Tier 3):
- "Access Grants" card showing count of active grants
- Link to admin grant list

#### 9. Tests

Create `tests/test_access_grants.py`:
- AccessGrant creation and expiry
- Decorator redirects PM to justification form at Tier 3 when no grant exists
- Decorator allows PM at Tier 3 with active grant
- Decorator allows PM at Tier 1-2 without grant (GATED relaxed)
- Grant list shows active grants
- Admin can see all grants
- Expired grants don't provide access
- Audit entries created for grant and for individual views

---

## Build Order

1. **PERM-P6 first** (independent of P5, more complex, higher priority per DRR)
   - AccessGrant model + migration
   - Decorator update
   - Justification form + views
   - Permission matrix update
   - Grant list views
   - Tests
   - Commit

2. **PERM-P5 second** (depends on P8 field infrastructure)
   - is_dv_safe flag + migration
   - DV-sensitive field marking (CustomFieldDefinition.is_dv_sensitive or pattern)
   - Field hiding logic
   - Set/remove workflow + views
   - Template changes
   - Tests
   - Commit

3. **Integration** (WP4)
   - Run `python manage.py translate_strings` for new user-facing strings
   - Fill French translations
   - Update CLAUDE.md with new models and conventions
   - Update TODO.md
   - Commit

---

## Key Architecture Reminders

- **Django 5, server-rendered templates, Pico CSS, HTMX** — no React/npm
- **Canadian spelling** — colour, organisation, behaviour
- **`{% load i18n %}` and `{% trans %}`** for all user-visible strings
- **`@admin_required`** from `apps/auth_app/decorators`
- **`@requires_permission`** from `apps/auth_app/decorators`
- **`get_access_tier()`** from `apps/admin_settings/models`
- **Audit log:** `AuditLog.objects.using("audit").create(...)` — separate database
- **Encrypted fields:** PII uses property accessors, not direct field access
- **Fail closed:** if a permission check can't determine access level, deny
- Read `tasks/design-rationale/access-tiers.md` for anti-patterns and deferred work
