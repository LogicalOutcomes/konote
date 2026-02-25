"""Admin view for configuring front desk field access (PERM-P8)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.admin_settings.models import get_access_tier
from apps.audit.models import AuditLog
from apps.auth_app.decorators import admin_required
from apps.clients.models import CustomFieldDefinition, FieldAccessConfig


# Human-readable labels for core fields shown in the admin UI.
CORE_FIELD_LABELS = {
    "phone": _("Phone Number"),
    "email": _("Email Address"),
    "preferred_name": _("Preferred Name"),
    "birth_date": _("Date of Birth"),
}


@login_required
@admin_required
def field_access(request):
    """Show / save per-field front desk access configuration.

    Two sections:
    1. Core fields (from FieldAccessConfig) — phone, email, preferred_name, birth_date
    2. Custom fields (from CustomFieldDefinition.front_desk_access)

    Only available at Tier 2+. At Tier 1, safe defaults apply automatically
    and this page is not accessible.
    """
    tier = get_access_tier()
    if tier < 2:
        messages.warning(request, _("Field access configuration requires Tier 2 or higher."))
        return redirect("admin_settings:dashboard")

    access_choices = FieldAccessConfig.ACCESS_CHOICES

    if request.method == "POST":
        # Handle "Reset to Defaults" action
        if request.POST.get("action") == "reset_defaults":
            FieldAccessConfig.objects.all().delete()
            CustomFieldDefinition.objects.filter(status="active").update(front_desk_access="none")
            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=request.user.pk,
                user_display=str(request.user),
                ip_address=request.META.get("REMOTE_ADDR"),
                action="update",
                resource_type="settings",
                metadata={"setting": "field_access", "change": "reset_to_defaults"},
            )
            messages.success(request, _("Field access settings reset to safe defaults."))
            return redirect("admin_settings:field_access")

        # Track changes for audit logging
        old_access = FieldAccessConfig.get_all_access()
        changes = {}

        # Save core field access settings
        for field_name in CORE_FIELD_LABELS:
            new_access = request.POST.get(f"core_{field_name}", "none")
            if new_access not in ("none", "view", "edit"):
                new_access = "none"
            old_val = old_access.get(field_name, "none")
            if new_access != old_val:
                changes[field_name] = {"old": old_val, "new": new_access}
            obj, _created = FieldAccessConfig.objects.update_or_create(
                field_name=field_name,
                defaults={"front_desk_access": new_access},
            )

        # Save custom field access settings
        custom_fields = CustomFieldDefinition.objects.filter(status="active")
        for cf in custom_fields:
            new_access = request.POST.get(f"custom_{cf.pk}", "none")
            if new_access not in ("none", "view", "edit"):
                new_access = "none"
            old_val = cf.front_desk_access
            if new_access != old_val:
                changes[f"custom:{cf.name}"] = {"old": old_val, "new": new_access}
            cf.front_desk_access = new_access
            cf.save(update_fields=["front_desk_access"])

        # Audit log — record what changed
        if changes:
            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=request.user.pk,
                user_display=str(request.user),
                ip_address=request.META.get("REMOTE_ADDR"),
                action="update",
                resource_type="settings",
                metadata={"setting": "field_access", "changes": changes},
            )

        messages.success(request, _("Field access settings saved."))
        return redirect("admin_settings:field_access")

    # Build core fields context
    access_map = FieldAccessConfig.get_all_access()
    core_fields = []
    for field_name, label in CORE_FIELD_LABELS.items():
        core_fields.append({
            "name": field_name,
            "label": label,
            "access": access_map.get(field_name, "none"),
        })

    # Build custom fields context, grouped by their section
    custom_fields = CustomFieldDefinition.objects.filter(
        status="active"
    ).select_related("group").order_by("group__sort_order", "sort_order", "name")
    grouped_custom_fields = {}
    for cf in custom_fields:
        group_name = cf.group.title
        if group_name not in grouped_custom_fields:
            grouped_custom_fields[group_name] = []
        grouped_custom_fields[group_name].append({
            "pk": cf.pk,
            "name": cf.name,
            "access": cf.front_desk_access,
        })

    return render(request, "admin_settings/field_access.html", {
        "core_fields": core_fields,
        "grouped_custom_fields": grouped_custom_fields,
        "access_choices": access_choices,
    })
