# EVAL-GOV1 — Admin UI for Granting Evaluator Export Permission

**Status:** Ready to build
**Dependencies:** PR #617, #622, #623 merged (per-user grant enforced, admin bypass removed, regression tests in place)
**Governance source:** `tasks/eval-export-governance.md`
**DRR:** `tasks/design-rationale/evaluation-microdata-export.md`
**Related session history:** PR #617 (bug fix), #622 (simplify), #623 (tests)

## Context you need before starting

Read these first. Do not skim.

1. **`tasks/eval-export-governance.md`** — defines the governance model (two-person control: ED authorises engagement → Admin grants permission). Section "How is the permission granted?" at line 24 is the spec for this task.
2. **`tasks/design-rationale/evaluation-microdata-export.md`** sections "Access Control" and "Anti-Patterns" — the design rationale, especially why per-user grant rather than role-based.
3. **`apps/auth_app/models.py:61`** — the `evaluation_export_granted` BooleanField on User. Has a `TODO: EVAL-GOV1` comment linking here.
4. **`apps/auth_app/admin_views.py:106`** — the existing `user_edit` view that this task will extend.
5. **`apps/reports/utils.py:61`** — `can_create_evaluation_export` is now a one-line helper. Your grant UI must set `evaluation_export_granted=True`.
6. **`tests/test_export_permissions.py`** — the `EvaluatorExportPermissionTest` class. Extend this with tests for the new grant flow.

## The problem EVAL-GOV1 solves

Today, the ONLY way to grant `report.evaluation_export` to a user is via the built-in Django admin at `/admin/auth_app/user/<id>/change/`. That panel:

- Has no reason field — there's no audit trail linking the technical grant to the governance decision (e.g., "ED approved this on 2026-03-15 for Youth Employment evaluation")
- Is not accessible via the KoNote admin menu (admins can't find it without knowing the URL)
- Doesn't trigger the `_audit_user_change` immutable audit log (only the generic Django admin log)
- Has no revoke confirmation — one click can silently remove the permission
- Doesn't show who granted, when, or why in any admin view

The governance doc explicitly requires: **"the admin must enter a reason (free-text field) that links the technical act to the governance authority — e.g., 'Approved by ED for Youth Employment evaluation with Llewelyn Consulting, agreement signed 2026-03-15.'"**

The policy hole: the DRR says two-person control (ED → Admin), but without a reason field, nothing in the system records that the ED actually approved anything. An admin could grant themselves the permission with zero paper trail.

## What to build

### 1. Data model — `EvaluationExportGrant`

Add a new model in `apps/auth_app/models.py`:

```python
class EvaluationExportGrant(models.Model):
    """Per-user grant record for report.evaluation_export.

    One row per grant event (not one per user — history is preserved).
    Revocation creates a new row with active=False, leaving the
    granting row intact for audit purposes.
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="evaluation_export_grants",
    )
    granted_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name="evaluation_export_grants_issued",
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(
        help_text="Why this grant was issued — typically references "
                  "the ED's authorisation and the evaluation engagement.",
    )
    active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="evaluation_export_grants_revoked",
    )
    revoke_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-granted_at"]
        constraints = [
            # Only one active grant per user at a time
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(active=True),
                name="one_active_eval_export_grant_per_user",
            ),
        ]
```

Migration: `makemigrations auth_app -n add_evaluation_export_grant` (the next number after 0011).

### 2. Keep `User.evaluation_export_granted` as the hot-path cache

**Do not remove `evaluation_export_granted`** from User. Keep it as a denormalised cache of "is there an active grant right now" so the hot-path permission check in `can_create_evaluation_export` and the template tag stay O(1) — a single attribute read on the already-loaded user object.

Wire it via a `post_save` signal on `EvaluationExportGrant`:

```python
@receiver(post_save, sender=EvaluationExportGrant)
def sync_user_eval_export_flag(sender, instance, **kwargs):
    has_active = EvaluationExportGrant.objects.filter(
        user=instance.user, active=True
    ).exists()
    if instance.user.evaluation_export_granted != has_active:
        User.objects.filter(pk=instance.user.pk).update(
            evaluation_export_granted=has_active
        )
```

Data migration: backfill grants for every user where `evaluation_export_granted=True` with a placeholder reason ("Pre-EVAL-GOV1 grant — reason not recorded") and `granted_by=None` or a system user. Document in the migration.

### 3. Form — `EvaluationExportGrantForm`

In `apps/auth_app/forms.py` (or wherever UserEditForm lives):

```python
class EvaluationExportGrantForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        min_length=20,  # prevent drive-by grants with "ok" as reason
        label=_("Reason for granting"),
        help_text=_(
            "Required. Record the ED's authorisation, the evaluation "
            "engagement, and any agreement reference. This is logged "
            "to the immutable audit trail."
        ),
    )
```

Reject `reason` that is blank, "test", "ok", or fewer than 20 characters. The governance purpose of the field is to force the admin to think about *why* — a textarea that accepts anything is theatre.

### 4. View — grant/revoke flow

Add three views in `apps/auth_app/admin_views.py`:

- `eval_export_grant_list` (GET) — lists all users with active grants showing user, granted_by, granted_at, reason, last_export_date (join via `SecureExportLink.created_at` where `export_type="evaluation_microdata"`). This is a simplified version of EVAL-GOV3.
- `eval_export_grant_create` (GET + POST) — form to grant a specific user. GET renders the form; POST validates + creates an `EvaluationExportGrant` row + logs to audit DB.
- `eval_export_grant_revoke` (POST only, with CSRF) — marks the active grant inactive, records `revoked_by` and optionally `revoke_reason`.

All three views require `@requires_permission("user.manage", allow_admin=True)` (same as existing user management views). Follow the existing pattern in `user_edit` for error handling, redirects, and the `_audit_user_change` audit log call.

**Important**: Add a NEW audit event type for these grants — do not reuse the generic `user.update` event. The audit log schema should record:
- `event_type`: `"evaluation_export_grant_created"` or `"evaluation_export_grant_revoked"`
- `target_user_id`, `target_user_email`
- `granted_by_id`, `granted_by_email`
- `reason` (full text)
- `previous_state` / `new_state`

### 5. URLs — add routes

In `apps/auth_app/admin_urls.py`:

```python
path("evaluation-export/", admin_views.eval_export_grant_list, name="eval_export_grant_list"),
path("evaluation-export/new/", admin_views.eval_export_grant_create, name="eval_export_grant_create"),
path("evaluation-export/<int:grant_id>/revoke/", admin_views.eval_export_grant_revoke, name="eval_export_grant_revoke"),
```

### 6. Templates

- `templates/auth_app/eval_export_grant_list.html` — a simple table. Reuse Pico CSS patterns from `user_list.html`.
- `templates/auth_app/eval_export_grant_form.html` — wraps `EvaluationExportGrantForm` in a `<form method="post">`. Include a prominent warning box explaining what the permission grants and the reason requirement. Use `{% include "includes/_form_field.html" %}` for rendering fields.
- Add a "Revoke" button to the list page with a JS `confirm()` fallback plus a `formaction` intermediary confirmation page if the user prefers no-JS.

### 7. Navigation — admin menu entry

In `templates/base.html`, in the admin dropdown (around line 192 where "Team Members" lives), add a new entry:

```html
<li role="none"><a role="menuitem" href="{% url 'admin_users:eval_export_grant_list' %}">{% trans "Evaluator Export Access" %}</a></li>
```

Group it near Team Members and User Invites since it's user-permission management.

### 8. Update `user_edit` to remove direct flag editing

Find wherever `evaluation_export_granted` appears in `UserEditForm` (if anywhere — check `apps/auth_app/forms.py`) and REMOVE it. The only way to set this flag from now on is through `EvaluationExportGrant`. Direct edits bypass the audit trail and reason requirement.

Also remove it from `apps/auth_app/admin.py:17` (the Django admin `fieldsets`). Leave the field visible in the list display as read-only. Add a `readonly_fields = ("evaluation_export_granted",)` to the Django admin class with a note pointing admins to the KoNote UI.

### 9. Update demo seed

In `apps/reports/management/commands/seed_eval_export_demo.py`, the `_grant_permission` method currently writes `evaluation_export_granted=True` directly. Update it to create an `EvaluationExportGrant` row instead, with a reason like `"Demo seed: pre-authorised for DEMO_MODE evaluation export walkthrough"` and `granted_by` set to a seeded admin user. The `post_save` signal will sync the cached flag.

### 10. Tests — extend `tests/test_export_permissions.py`

Add to `EvaluatorExportPermissionTest` or a new test class:

- **Grant form validation**: reason < 20 chars → form invalid
- **Grant creation**: POST to `eval_export_grant_create` by admin → creates `EvaluationExportGrant` row + sets cached flag + writes audit entry + redirects to list
- **Grant uniqueness**: attempting to create a second active grant for the same user → form invalid with clear error
- **Grant visibility**: non-admin, non-user-manager cannot reach the grant views (403)
- **Revoke flow**: POST to revoke → grant marked inactive + cached flag cleared + audit entry written
- **Signal sync**: creating an EvaluationExportGrant via ORM directly updates `user.evaluation_export_granted`
- **View access post-grant**: user with active grant → 200 at `/reports/evaluation-export/`; after revoke → 403
- **Self-grant**: admin grants themselves → allowed but audit entry records `target == granted_by` (flag for later EVAL-GOV2 dashboard)

## Out of scope for EVAL-GOV1 (leave for later tasks)

- **EVAL-GOV2**: admin dashboard card showing "N users have access" — separate task
- **EVAL-GOV3**: full permission audit list with per-user export history — this task builds the SIMPLE list; GOV3 adds the per-user detail page and last-export timestamps
- **EVAL-GOV4/5**: export history view and agreement expiry warnings — not needed for GOV1
- **Automatic expiry of grants**: the panel explicitly rejected this; do not add it
- **Two-person approval per export**: rejected; do not add
- **Email notifications when a grant is created**: out of scope — the governance model is visibility-based, not push-notification-based
- **Internationalisation of reason text**: the reason is free-text English/French whatever the admin types; do not try to translate it

## Anti-patterns — do not build these

From `tasks/eval-export-governance.md` line 48-56:

| Do NOT build | Why |
|---|---|
| Two-person approval per export | ED often unavailable; existing safeguards sufficient |
| Automatic permission expiry | Admin burden; visibility is the better safeguard |
| Hard block on expired agreements | Agreements sometimes verbally extended; warning is enough |
| ED-only permission restriction | PMs are legitimate operators |
| Approval workflow model with queues and states | Overkill for 10-person orgs |

Also:

| Do NOT build | Why |
|---|---|
| Allow granting without a reason, even "for testing" | The governance model REQUIRES the reason. An admin who wants to test should use the demo seed or a dedicated test script. |
| Store the reason encrypted | It's not PII. It's a governance note written by the admin. Leave it as plain text in the app DB and audit DB. |
| Let PMs grant the permission to themselves | Even though PMs can hold the permission, only users with `user.manage` should be able to GRANT it. The two-person control is between the grant-holder (PM) and the granter (admin). |
| Edit an existing grant's reason after creation | Grants are append-only. If the reason was wrong, revoke and re-grant. Editing is a supply-chain risk on audit trails. |

## Acceptance criteria

Before marking EVAL-GOV1 done:

1. [ ] `EvaluationExportGrant` model + migration exists and migrates clean on a fresh DB
2. [ ] Data migration successfully backfills grants for any pre-existing `evaluation_export_granted=True` users
3. [ ] Admin can navigate **Admin → Evaluator Export Access** from the nav menu
4. [ ] Admin can grant a user the permission with a ≥20 char reason; grant appears in the list with correct metadata
5. [ ] Admin cannot grant without a reason; form rejects blank/too-short input with a clear error
6. [ ] Admin can revoke a grant; user's `evaluation_export_granted` cached flag flips to False immediately
7. [ ] After revoke, the user hits 403 on `/reports/evaluation-export/`
8. [ ] Direct `/admin/auth_app/user/<id>/` no longer allows flipping `evaluation_export_granted` manually (read-only in Django admin fieldsets)
9. [ ] Every grant/revoke creates an audit log entry with `reason`, `granted_by`, `target_user` fields queryable from the audit DB
10. [ ] Demo seed creates grants via `EvaluationExportGrant`, not direct flag writes
11. [ ] All existing tests in `EvaluatorExportPermissionTest` still pass
12. [ ] New tests cover: form validation, grant creation, revoke flow, signal sync, and view access after grant/revoke
13. [ ] Translations (`python manage.py translate_strings`) extract all new `{% trans %}` strings into the .po file and French translations are filled in
14. [ ] `tasks/eval-export-governance.md` updated to mark EVAL-GOV1 as complete; TODO.md updated accordingly
15. [ ] `konote-qa-scenarios/pages/page-inventory.yaml` updated with the new admin pages (3 new URLs)

## Development notes

- **Branch naming**: `feat/eval-gov1-grant-ui`
- **Commit discipline**: commit after each of the 10 numbered steps above, not all at once. That way the PR review can track the build in logical chunks.
- **Test runs**: `pytest tests/test_export_permissions.py::EvaluatorExportPermissionTest` for the permission tests, `pytest tests/test_auth.py` (or wherever the admin_views tests live) for the admin UI tests.
- **Migration gotchas**: the unique-active-grant constraint uses a `UniqueConstraint` with `condition=Q(active=True)`. Django requires PostgreSQL 9.5+ for this; KoNote is on 16 so fine. Test the constraint by trying to create two active grants for the same user in a shell — it should raise `IntegrityError`.
- **Backfill migration idempotency**: guard the data migration with an existence check so re-running `migrate` doesn't duplicate the placeholder grants. Pattern: `if not EvaluationExportGrant.objects.filter(user=u).exists():`.
- **Consultation gate**: this is a UI change (admin workflow), not an outcome-model change, so **no GK review required** per CLAUDE.md. Build it, merge it. GK will see it in the next demo walkthrough.
- **Run `/simplify` and `/review-session`** before wrapping up — this task has several moving parts (model, migration, views, forms, templates, signals, tests) and a review pass is worth it.

## What success looks like

An admin opens **Admin → Evaluator Export Access**, sees a list of the three seeded demo users (Casey, Morgan, Eva) with their grant reasons and grant dates. They click **New grant**, search for another user, type a 50-word reason ("Board approved evaluation with X University for the Y program, MOU signed 2026-04-15, agreement expires 2026-12-31"), and click **Grant**. The new grant appears in the list. The granted user signs in, goes to Reports → Evaluator Export (Confidential), and the form loads. Meanwhile, the audit DB has a new row tying the grant to the granting admin with the full reason text, immutable.

That's the two-person control working in software.
