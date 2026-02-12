"""Admin views for funder profile management — upload, preview, CRUD."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.auth_app.decorators import admin_required

from apps.reports.csv_parser import (
    generate_sample_csv,
    parse_funder_profile_csv,
    save_parsed_profile,
    validate_parsed_profile,
)
from apps.reports.models import FunderProfile
from apps.programs.models import Program


@login_required
@admin_required
def funder_profile_list(request):
    """List all funder profiles with their linked programs."""
    profiles = FunderProfile.objects.prefetch_related("programs", "breakdowns").all()
    return render(request, "admin_settings/funder_profiles/list.html", {
        "profiles": profiles,
    })


@login_required
@admin_required
def funder_profile_upload(request):
    """Upload a funder profile CSV."""
    if request.method != "POST":
        return render(request, "admin_settings/funder_profiles/upload.html")

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
    parsed, errors = parse_funder_profile_csv(csv_content)

    if errors:
        return render(request, "admin_settings/funder_profiles/upload.html", {
            "errors": errors,
            "csv_text": csv_content,
        })

    # Validate against database (check field names match, etc.)
    warnings = validate_parsed_profile(parsed)

    # Show preview for confirmation
    programs = Program.objects.filter(status="active").order_by("name")

    return render(request, "admin_settings/funder_profiles/preview.html", {
        "parsed": parsed,
        "warnings": warnings,
        "programs": programs,
        "csv_content": csv_content,
    })


@login_required
@admin_required
def funder_profile_confirm(request):
    """Confirm and save a previewed funder profile."""
    if request.method != "POST":
        return redirect("admin_settings:funder_profile_list")

    csv_content = request.POST.get("csv_content", "")
    if not csv_content:
        messages.error(request, _("No CSV data found. Please try uploading again."))
        return redirect("admin_settings:funder_profile_upload")

    # Re-parse (the preview page passes the CSV content through a hidden field)
    parsed, errors = parse_funder_profile_csv(csv_content)
    if errors:
        messages.error(request, _("CSV validation failed. Please correct errors and re-upload."))
        return redirect("admin_settings:funder_profile_upload")

    # Save to database
    profile = save_parsed_profile(parsed, created_by=request.user)

    # Link to selected programs
    program_ids = request.POST.getlist("programs")
    if program_ids:
        programs = Program.objects.filter(pk__in=program_ids, status="active")
        profile.programs.set(programs)

    messages.success(
        request,
        _('Funder profile "%(name)s" created with %(count)d demographic breakdown(s).')
        % {"name": profile.name, "count": profile.breakdowns.count()},
    )
    return redirect("admin_settings:funder_profile_detail", profile_id=profile.pk)


@login_required
@admin_required
def funder_profile_detail(request, profile_id):
    """View a funder profile's breakdowns and linked programs."""
    profile = get_object_or_404(
        FunderProfile.objects.prefetch_related("breakdowns", "programs"),
        pk=profile_id,
    )
    return render(request, "admin_settings/funder_profiles/detail.html", {
        "profile": profile,
    })


@login_required
@admin_required
def funder_profile_edit_programs(request, profile_id):
    """Edit which programs are linked to a funder profile."""
    profile = get_object_or_404(FunderProfile, pk=profile_id)

    if request.method == "POST":
        program_ids = request.POST.getlist("programs")
        programs = Program.objects.filter(pk__in=program_ids, status="active")
        profile.programs.set(programs)
        messages.success(request, _("Program assignments updated."))
        return redirect("admin_settings:funder_profile_detail", profile_id=profile.pk)

    programs = Program.objects.filter(status="active").order_by("name")
    linked_ids = set(profile.programs.values_list("pk", flat=True))
    return render(request, "admin_settings/funder_profiles/edit_programs.html", {
        "profile": profile,
        "programs": programs,
        "linked_ids": linked_ids,
    })


@login_required
@admin_required
def funder_profile_delete(request, profile_id):
    """Delete a funder profile (with confirmation)."""
    profile = get_object_or_404(FunderProfile, pk=profile_id)

    if request.method == "POST":
        name = profile.name
        profile.delete()
        messages.success(request, _('Funder profile "%(name)s" deleted.') % {"name": name})
        return redirect("admin_settings:funder_profile_list")

    return render(request, "admin_settings/funder_profiles/confirm_delete.html", {
        "profile": profile,
    })


@login_required
@admin_required
def funder_profile_download_csv(request, profile_id):
    """Download the original CSV that was used to create a profile."""
    profile = get_object_or_404(FunderProfile, pk=profile_id)

    if not profile.source_csv:
        messages.warning(request, _("No source CSV available for this profile."))
        return redirect("admin_settings:funder_profile_detail", profile_id=profile.pk)

    response = HttpResponse(profile.source_csv, content_type="text/csv; charset=utf-8")
    safe_name = profile.name.replace(" ", "_").replace("/", "_")
    response["Content-Disposition"] = f'attachment; filename="funder_profile_{safe_name}.csv"'
    return response


@login_required
@admin_required
def funder_profile_sample_csv(request):
    """Download a sample/template CSV for creating funder profiles."""
    csv_content = generate_sample_csv()
    response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="funder_profile_template.csv"'
    return response
