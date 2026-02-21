"""Admin views for report template management — upload, preview, CRUD."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.auth_app.decorators import admin_required

from apps.reports.csv_parser import (
    generate_sample_csv,
    parse_report_template_csv,
    save_parsed_profile,
    validate_parsed_profile,
)
from apps.reports.models import Partner, ReportTemplate
from apps.programs.models import Program


@login_required
@admin_required
def report_template_list(request):
    """List all report templates with their linked programs (via partner)."""
    profiles = ReportTemplate.objects.select_related("partner").prefetch_related("breakdowns").all()
    return render(request, "admin_settings/funder_profiles/list.html", {
        "profiles": profiles,
    })


@login_required
@admin_required
def report_template_upload(request):
    """Upload a report template CSV."""
    if request.method != "POST":
        partners = Partner.objects.filter(is_active=True).order_by("name")
        if not partners.exists():
            messages.warning(request, _("Please create a partner first before uploading a report template."))
            return redirect("admin_settings:partner_list")
        return render(request, "admin_settings/funder_profiles/upload.html", {
            "partners": partners,
        })

    csv_file = request.FILES.get("csv_file")
    csv_text = request.POST.get("csv_text", "").strip()

    # Accept either file upload or pasted text
    if csv_file:
        try:
            csv_content = csv_file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            messages.error(request, _("Could not read file. Please upload a UTF-8 CSV file."))
            return render(request, "admin_settings/funder_profiles/upload.html")
    elif csv_text:
        csv_content = csv_text
    else:
        messages.error(request, _("Please upload a CSV file or paste CSV content."))
        return render(request, "admin_settings/funder_profiles/upload.html")

    # Parse the CSV
    parsed, errors = parse_report_template_csv(csv_content)

    if errors:
        return render(request, "admin_settings/funder_profiles/upload.html", {
            "errors": errors,
            "csv_text": csv_content,
        })

    # Validate against database (check field names match, etc.)
    warnings = validate_parsed_profile(parsed)

    # Show preview for confirmation
    programs = Program.objects.filter(status="active").order_by("name")
    partners = Partner.objects.filter(is_active=True).order_by("name")

    return render(request, "admin_settings/funder_profiles/preview.html", {
        "parsed": parsed,
        "warnings": warnings,
        "programs": programs,
        "partners": partners,
        "csv_content": csv_content,
    })


@login_required
@admin_required
def report_template_confirm(request):
    """Confirm and save a previewed report template."""
    if request.method != "POST":
        return redirect("admin_settings:report_template_list")

    csv_content = request.POST.get("csv_content", "")
    if not csv_content:
        messages.error(request, _("No CSV data found. Please try uploading again."))
        return redirect("admin_settings:report_template_upload")

    # Re-parse (the preview page passes the CSV content through a hidden field)
    parsed, errors = parse_report_template_csv(csv_content)
    if errors:
        messages.error(request, _("CSV validation failed. Please correct errors and re-upload."))
        return redirect("admin_settings:report_template_upload")

    # Save to database
    profile = save_parsed_profile(parsed, created_by=request.user)

    # Link to selected partner
    partner_id = request.POST.get("partner")
    if partner_id:
        partner = Partner.objects.filter(pk=partner_id, is_active=True).first()
        if partner:
            profile.partner = partner
            profile.save(update_fields=["partner"])

    messages.success(
        request,
        _('Report template "%(name)s" created with %(count)d demographic breakdown(s).')
        % {"name": profile.name, "count": profile.breakdowns.count()},
    )
    return redirect("admin_settings:report_template_detail", profile_id=profile.pk)


@login_required
@admin_required
def report_template_detail(request, profile_id):
    """View a report template's breakdowns and partner details."""
    profile = get_object_or_404(
        ReportTemplate.objects.select_related("partner").prefetch_related("breakdowns"),
        pk=profile_id,
    )
    return render(request, "admin_settings/funder_profiles/detail.html", {
        "profile": profile,
    })


@login_required
@admin_required
def report_template_edit_programs(request, profile_id):
    """Programs are now managed on the Partner entity — redirect there."""
    profile = get_object_or_404(ReportTemplate.objects.select_related("partner"), pk=profile_id)

    if profile.partner:
        messages.info(request, _("Programs are now managed on the partner. Redirecting."))
        return redirect("admin_settings:partner_detail", partner_id=profile.partner.pk)

    messages.warning(request, _("This template has no partner assigned. Please assign a partner first."))
    return redirect("admin_settings:report_template_detail", profile_id=profile.pk)


@login_required
@admin_required
def report_template_delete(request, profile_id):
    """Delete a report template (with confirmation)."""
    profile = get_object_or_404(ReportTemplate, pk=profile_id)

    if request.method == "POST":
        name = profile.name
        profile.delete()
        messages.success(request, _('Report template "%(name)s" deleted.') % {"name": name})
        return redirect("admin_settings:report_template_list")

    return render(request, "admin_settings/funder_profiles/confirm_delete.html", {
        "profile": profile,
    })


@login_required
@admin_required
def report_template_download_csv(request, profile_id):
    """Download the original CSV that was used to create a profile."""
    profile = get_object_or_404(ReportTemplate, pk=profile_id)

    if not profile.source_csv:
        messages.warning(request, _("No source CSV available for this profile."))
        return redirect("admin_settings:report_template_detail", profile_id=profile.pk)

    response = HttpResponse(profile.source_csv, content_type="text/csv; charset=utf-8")
    safe_name = profile.name.replace(" ", "_").replace("/", "_")
    response["Content-Disposition"] = f'attachment; filename="report_template_{safe_name}.csv"'
    return response


@login_required
@admin_required
def report_template_sample_csv(request):
    """Download a sample/template CSV for creating report templates."""
    csv_content = generate_sample_csv()
    response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="report_template_sample.csv"'
    return response
