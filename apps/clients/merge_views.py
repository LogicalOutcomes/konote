"""Views for the duplicate client merge workflow."""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.programs.views import admin_required

from .forms import MergeConfirmForm
from .merge import (
    _validate_merge_preconditions,
    build_comparison,
    execute_merge,
    find_merge_candidates,
)
from .models import ClientFile
from .views import get_client_queryset

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    """Get client IP, respecting X-Forwarded-For from reverse proxy."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


@login_required
@admin_required
def merge_candidates_list(request):
    """Show list of potential duplicate client pairs."""
    results = find_merge_candidates(request.user)

    context = {
        "phone_pairs": results["phone"],
        "name_dob_pairs": results["name_dob"],
        "phone_count": results["phone_count"],
        "name_dob_count": results["name_dob_count"],
        "total_count": results["phone_count"] + results["name_dob_count"],
        "too_many": results["too_many"],
        "nav_active": "admin",
    }
    return render(request, "clients/merge/merge_candidates.html", context)


@login_required
@admin_required
def merge_compare(request, client_a_id, client_b_id):
    """Side-by-side comparison of two clients with merge form."""
    base_qs = get_client_queryset(request.user)
    client_a = get_object_or_404(base_qs, pk=client_a_id)
    client_b = get_object_or_404(base_qs, pk=client_b_id)

    # Validate preconditions before showing the comparison
    errors = _validate_merge_preconditions(client_a, client_b)
    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect("merge_candidates_list")

    comparison = build_comparison(client_a, client_b)

    if request.method == "POST":
        form = MergeConfirmForm(
            request.POST,
            pii_fields=comparison["pii_fields"],
            field_conflicts=comparison["field_conflicts"],
            client_a_pk=client_a.pk,
            client_b_pk=client_b.pk,
        )
        if form.is_valid():
            primary_pk = form.cleaned_data["primary"]

            # Determine which is kept and which is archived
            if primary_pk == client_a.pk:
                kept, archived = client_a, client_b
            else:
                kept, archived = client_b, client_a

            # Build pii_choices from form data — field names + "kept"/"archived" only
            pii_choices = {}
            for field_info in comparison["pii_fields"]:
                if not field_info["differs"]:
                    continue
                form_field = f"pii_{field_info['field_name']}"
                chosen_pk = int(form.cleaned_data.get(form_field, primary_pk))
                pii_choices[field_info["field_name"]] = "kept" if chosen_pk == kept.pk else "archived"

            # Build field_resolutions from form data
            field_resolutions = {}
            for conflict in comparison["field_conflicts"]:
                form_field = f"custom_{conflict['field_def_id']}"
                chosen_pk = int(form.cleaned_data.get(form_field, primary_pk))
                field_resolutions[str(conflict["field_def_id"])] = (
                    "kept" if chosen_pk == kept.pk else "archived"
                )

            try:
                execute_merge(
                    kept=kept,
                    archived=archived,
                    pii_choices=pii_choices,
                    field_resolutions=field_resolutions,
                    user=request.user,
                    ip_address=_get_client_ip(request),
                )
                messages.success(
                    request,
                    _("Records merged successfully. All data has been combined into this record."),
                )
                return redirect("clients:client_detail", client_id=kept.pk)
            except ValueError as e:
                messages.error(request, str(e))
                return redirect("merge_candidates_list")
    else:
        form = MergeConfirmForm(
            pii_fields=comparison["pii_fields"],
            field_conflicts=comparison["field_conflicts"],
            client_a_pk=client_a.pk,
            client_b_pk=client_b.pk,
            initial={"primary": client_a.pk},
        )

    # Calculate totals for impact summary
    total_a = sum(v for k, v in comparison["counts_a"].items() if isinstance(v, int))
    total_b = sum(v for k, v in comparison["counts_b"].items() if isinstance(v, int))

    context = {
        "client_a": client_a,
        "client_b": client_b,
        "comparison": comparison,
        "form": form,
        "total_records_a": total_a,
        "total_records_b": total_b,
        "nav_active": "admin",
    }
    return render(request, "clients/merge/merge_compare.html", context)
