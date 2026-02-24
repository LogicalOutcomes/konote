"""Admin views for field collection configuration."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.auth_app.decorators import admin_required
from apps.programs.models import Program

from .forms import ProgramFieldConfigForm
from .models import ProgramFieldConfig, SyncRun


@login_required
@admin_required
def field_collection_list(request):
    """List all programs with their field collection status."""
    programs = Program.objects.filter(status="active").order_by("name")

    # Get or create configs for all active programs
    program_configs = []
    for program in programs:
        config, _created = ProgramFieldConfig.objects.get_or_create(program=program)
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
    program = get_object_or_404(Program, pk=program_id)
    config, _created = ProgramFieldConfig.objects.get_or_create(program=program)

    if request.method == "POST":
        form = ProgramFieldConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
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
