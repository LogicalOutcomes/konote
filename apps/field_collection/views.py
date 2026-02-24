"""Admin views for field collection configuration."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone as tz
from django.utils.translation import gettext as _

from apps.admin_settings.models import FeatureToggle
from apps.audit.models import AuditLog
from apps.auth_app.decorators import admin_required
from apps.programs.models import Program

from .forms import ProgramFieldConfigForm
from .models import ProgramFieldConfig, SyncRun


def _require_field_collection(request):
    """Raise 404 if the field_collection feature toggle is disabled."""
    flags = FeatureToggle.get_all_flags()
    if not flags.get("field_collection"):
        raise Http404


@login_required
@admin_required
def field_collection_list(request):
    """List all programs with their field collection status."""
    _require_field_collection(request)

    programs = Program.objects.filter(status="active").select_related(
        "field_config"
    ).order_by("name")

    program_configs = []
    for program in programs:
        config = getattr(program, "field_config", None)
        program_configs.append({
            "program": program,
            "config": config,
        })

    # Recent sync runs for the dashboard
    recent_syncs = SyncRun.objects.order_by("-started_at")[:10]

    return render(request, "field_collection/list.html", {
        "program_configs": program_configs,
        "recent_syncs": recent_syncs,
    })


@login_required
@admin_required
def field_collection_edit(request, program_id):
    """Edit field collection settings for a single program."""
    _require_field_collection(request)

    program = get_object_or_404(Program, pk=program_id)
    config, _created = ProgramFieldConfig.objects.get_or_create(program=program)

    if request.method == "POST":
        form = ProgramFieldConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()

            # Audit log: PII tier and config changes are security-relevant
            try:
                AuditLog.objects.using("audit").create(
                    event_timestamp=tz.now(),
                    user_id=request.user.pk,
                    user_display=getattr(request.user, "display_name", str(request.user)),
                    action="update",
                    resource_type="field_collection_config",
                    resource_id=config.pk,
                    program_id=program.pk,
                    metadata={
                        "program_name": program.name,
                        "changed_fields": list(form.changed_data),
                    },
                )
            except Exception:
                pass  # Audit DB may be unavailable in tests

            messages.success(request, _("Field collection settings updated for %(program)s.") % {"program": program.name})
            return redirect("field_collection:list")
    else:
        form = ProgramFieldConfigForm(instance=config)

    tier_descriptions = {
        "restricted": _("Only KoNote ID on device. For DV shelters and high-risk programs."),
        "standard": _("ID + first name. Sufficient for most programs with small caseloads."),
        "field": _("ID + first name + last initial. For large caseloads with name collisions. Requires device PIN."),
        "field_contact": _("ID + name + last initial + phone. For home visiting with appointment scheduling. Requires PIN + device policy."),
    }

    profile_descriptions = {
        "group": _("Session Attendance form only. For drop-in programs, workshops, and recreation."),
        "home_visiting": _("Visit Note form only. For individual outreach, coaching, and check-ins."),
        "circle": _("Visit Note + Circle Observation. For family and care network monitoring."),
        "full_field": _("All forms. For programs doing both group sessions and individual visits."),
    }

    return render(request, "field_collection/edit.html", {
        "program": program,
        "config": config,
        "form": form,
        "tier_descriptions": tier_descriptions,
        "profile_descriptions": profile_descriptions,
    })
