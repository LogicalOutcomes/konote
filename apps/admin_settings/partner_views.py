"""Admin views for partner management — CRUD and program linking."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.auth_app.decorators import admin_required
from apps.programs.models import Program
from apps.reports.forms import PartnerForm
from apps.reports.models import Partner


@login_required
@admin_required
def partner_list(request):
    """List all partners with their linked programs and report templates."""
    partners = Partner.objects.prefetch_related("programs", "report_templates").all()
    return render(request, "admin_settings/partners/list.html", {
        "partners": partners,
    })


@login_required
@admin_required
def partner_create(request):
    """Create a new partner."""
    if request.method == "POST":
        form = PartnerForm(request.POST)
        if form.is_valid():
            partner = form.save()
            messages.success(
                request,
                _('Partner "%(name)s" created.') % {"name": partner.name},
            )
            return redirect("admin_settings:partner_detail", partner_id=partner.pk)
    else:
        form = PartnerForm()

    return render(request, "admin_settings/partners/create.html", {
        "form": form,
    })


@login_required
@admin_required
def partner_detail(request, partner_id):
    """View a partner's details, linked programs, and report templates."""
    partner = get_object_or_404(
        Partner.objects.prefetch_related("programs", "report_templates__breakdowns"),
        pk=partner_id,
    )
    return render(request, "admin_settings/partners/detail.html", {
        "partner": partner,
    })


@login_required
@admin_required
def partner_edit(request, partner_id):
    """Edit an existing partner."""
    partner = get_object_or_404(Partner, pk=partner_id)

    if request.method == "POST":
        form = PartnerForm(request.POST, instance=partner)
        if form.is_valid():
            partner = form.save()
            messages.success(
                request,
                _('Partner "%(name)s" updated.') % {"name": partner.name},
            )
            return redirect("admin_settings:partner_detail", partner_id=partner.pk)
    else:
        form = PartnerForm(instance=partner)

    return render(request, "admin_settings/partners/edit.html", {
        "form": form,
        "partner": partner,
    })


@login_required
@admin_required
def partner_edit_programs(request, partner_id):
    """Manage the many-to-many relationship between a partner and programs."""
    partner = get_object_or_404(Partner, pk=partner_id)

    if request.method == "POST":
        program_ids = request.POST.getlist("program_ids")
        programs = Program.objects.filter(pk__in=program_ids, status="active")
        partner.programs.set(programs)
        messages.success(
            request,
            _('Programs updated for partner "%(name)s".') % {"name": partner.name},
        )
        return redirect("admin_settings:partner_detail", partner_id=partner.pk)

    # GET — show all active programs with checkboxes
    all_programs = Program.objects.filter(status="active").order_by("name")
    linked_ids = set(partner.programs.values_list("pk", flat=True))

    return render(request, "admin_settings/partners/edit_programs.html", {
        "partner": partner,
        "all_programs": all_programs,
        "linked_ids": linked_ids,
    })


@login_required
@admin_required
def partner_delete(request, partner_id):
    """Delete a partner (with confirmation)."""
    partner = get_object_or_404(Partner, pk=partner_id)

    if request.method == "POST":
        name = partner.name
        partner.delete()
        messages.success(request, _('Partner "%(name)s" deleted.') % {"name": name})
        return redirect("admin_settings:partner_list")

    return render(request, "admin_settings/partners/confirm_delete.html", {
        "partner": partner,
    })
