"""Views for GATED clinical access — justification + grant management."""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _

from datetime import timedelta

from apps.admin_settings.models import get_access_tier, InstanceSetting
from apps.audit.models import AuditLog
from apps.auth_app.decorators import admin_required

from .forms import AccessGrantForm, AccessGrantReasonForm
from .models import AccessGrant


@login_required
def access_grant_request(request):
    """Show justification form (GET) or create an AccessGrant (POST).

    Only available at Tier 3. At Tiers 1-2 the decorator never redirects
    here, but guard against direct URL access.
    """
    tier = get_access_tier()
    if tier < 3:
        return HttpResponseForbidden(_("Access grants are only required at Tier 3."))

    next_url = request.GET.get("next", request.POST.get("next", "/"))
    permission_key = request.GET.get("permission", request.POST.get("permission", ""))

    if request.method == "POST":
        form = AccessGrantForm(request.POST)
        if form.is_valid():
            grant = form.save(commit=False)
            grant.user = request.user

            # Determine program from the next URL or user's current program
            program = _resolve_program(request, next_url)
            if program is None:
                form.add_error(None, _("Unable to determine which program this access is for."))
            else:
                grant.program = program
                grant.expires_at = timezone.now() + timedelta(
                    days=form.cleaned_data["duration_days"]
                )
                grant.save()

                # Audit log
                AuditLog.objects.using("audit").create(
                    event_timestamp=timezone.now(),
                    user_id=request.user.pk,
                    user_display=str(request.user),
                    action="create",
                    resource_type="access_grant",
                    resource_id=grant.pk,
                    program_id=program.pk,
                    new_values={
                        "reason": str(grant.reason),
                        "justification": grant.justification,
                        "duration_days": form.cleaned_data["duration_days"],
                        "expires_at": grant.expires_at.isoformat(),
                        "permission_key": permission_key,
                    },
                )

                if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    next_url = "/"
                return redirect(next_url)
    else:
        form = AccessGrantForm()

    return render(request, "auth_app/access_grant_request.html", {
        "form": form,
        "next_url": next_url,
        "permission_key": permission_key,
    })


def _resolve_program(request, next_url):
    """Try to determine the program from the URL being accessed.

    Falls back to user's first assigned program if we can't parse the URL.
    """
    from apps.programs.models import UserProgramRole

    # Try to find a client ID in the next_url and get their program
    import re
    match = re.search(r"/clients/(\d+)/", next_url)
    if match:
        from apps.clients.models import ClientFile
        try:
            client = ClientFile.objects.get(pk=match.group(1))
            # Get user's role in a program that this client belongs to
            user_program_ids = set(
                UserProgramRole.objects.filter(
                    user=request.user, status="active"
                ).values_list("program_id", flat=True)
            )
            client_program_ids = set(
                client.enrolments.filter(
                    status="active", program_id__in=user_program_ids
                ).values_list("program_id", flat=True)
            )
            if client_program_ids:
                from apps.programs.models import Program
                return Program.objects.get(pk=min(client_program_ids))
        except (ClientFile.DoesNotExist, Exception):
            pass

    # Fallback: user's first active program
    role = UserProgramRole.objects.filter(
        user=request.user, status="active"
    ).select_related("program").first()
    if role:
        return role.program
    return None


@login_required
def access_grant_list(request):
    """Show the current user's active and recent grants."""
    now = timezone.now()
    active_grants = AccessGrant.objects.filter(
        user=request.user,
        is_active=True,
        expires_at__gt=now,
    ).select_related("program", "reason", "client_file")

    expired_grants = AccessGrant.objects.filter(
        user=request.user,
    ).exclude(
        pk__in=active_grants.values_list("pk", flat=True)
    ).select_related("program", "reason", "client_file").order_by("-granted_at")[:20]

    return render(request, "auth_app/access_grant_list.html", {
        "active_grants": active_grants,
        "expired_grants": expired_grants,
        "now": now,
    })


@login_required
def access_grant_revoke(request, grant_id):
    """Revoke (deactivate) an access grant early."""
    grant = get_object_or_404(AccessGrant, pk=grant_id, user=request.user)

    if request.method == "POST":
        grant.is_active = False
        grant.save(update_fields=["is_active"])

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.pk,
            user_display=str(request.user),
            action="update",
            resource_type="access_grant",
            resource_id=grant.pk,
            program_id=grant.program_id,
            new_values={"action": "revoked"},
        )

        return redirect("auth_app:access_grant_list")

    return render(request, "auth_app/access_grant_revoke_confirm.html", {
        "grant": grant,
    })


@login_required
@admin_required
def access_grant_admin_list(request):
    """Admin view: all access grants across all users. Only at Tier 3."""
    tier = get_access_tier()
    if tier < 3:
        return HttpResponseForbidden(_("Access grants are only used at Tier 3."))

    now = timezone.now()
    grants = AccessGrant.objects.select_related(
        "user", "program", "reason", "client_file"
    ).order_by("-granted_at")[:100]

    return render(request, "admin_settings/access_grant_admin_list.html", {
        "grants": grants,
        "now": now,
    })


@login_required
@admin_required
def access_grant_reasons_admin(request):
    """Admin view: manage configurable grant reasons. Only at Tier 3."""
    tier = get_access_tier()
    if tier < 3:
        return HttpResponseForbidden(_("Access grant reasons are only used at Tier 3."))

    from .models import AccessGrantReason

    reasons = AccessGrantReason.objects.all()
    add_form = AccessGrantReasonForm()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            add_form = AccessGrantReasonForm(request.POST)
            if add_form.is_valid():
                max_order = reasons.aggregate(
                    m=models.Max("sort_order")
                )["m"] or 0
                AccessGrantReason.objects.create(
                    label=add_form.cleaned_data["label"],
                    label_fr=add_form.cleaned_data["label_fr"],
                    sort_order=max_order + 1,
                )
                return redirect("admin_settings:access_grant_reasons")
            # Fall through to re-render with form errors

        elif action == "toggle":
            reason_id = request.POST.get("reason_id")
            try:
                reason = AccessGrantReason.objects.get(pk=reason_id)
                reason.is_active = not reason.is_active
                reason.save(update_fields=["is_active"])
            except AccessGrantReason.DoesNotExist:
                pass
            return redirect("admin_settings:access_grant_reasons")

    return render(request, "admin_settings/access_grant_reasons.html", {
        "reasons": reasons,
        "add_form": add_form,
    })


# Import models at module level for the admin view
from django.db import models
