"""Admin settings views: dashboard, terminology, features, instance settings."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _, gettext_lazy as _lazy

from apps.auth_app.decorators import admin_required

from .forms import FeatureToggleForm, InstanceSettingsForm, TerminologyForm
from .models import DEFAULT_TERMS, FeatureToggle, InstanceSetting, TerminologyOverride


# --- Dashboard ---

@login_required
@admin_required
def dashboard(request):
    from apps.auth_app.models import User
    from apps.notes.models import ProgressNoteTemplate

    # State indicators for dashboard cards
    current_flags = FeatureToggle.get_all_flags()
    total_features = len(DEFAULT_FEATURES)
    enabled_features = sum(
        1 for key in DEFAULT_FEATURES
        if current_flags.get(key, key in FEATURES_DEFAULT_ENABLED)
    )
    terminology_overrides = TerminologyOverride.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    note_template_count = ProgressNoteTemplate.objects.count()

    # IMPROVE-1b: Instance Settings summary
    instance_settings_count = InstanceSetting.objects.count()

    # IMPROVE-1b: Demo Accounts summary
    demo_users = User.objects.filter(is_demo=True, is_active=True).count()

    return render(request, "admin_settings/dashboard.html", {
        "enabled_features": enabled_features,
        "total_features": total_features,
        "terminology_overrides": terminology_overrides,
        "active_users": active_users,
        "note_template_count": note_template_count,
        "instance_settings_count": instance_settings_count,
        "demo_users": demo_users,
    })


# --- Terminology ---

@login_required
@admin_required
def terminology(request):
    # Build lookup of current overrides from database
    overrides = {
        obj.term_key: obj
        for obj in TerminologyOverride.objects.all()
    }

    if request.method == "POST":
        # Build current terms dicts for form initialisation
        current_terms_en = {}
        current_terms_fr = {}
        for key, defaults in DEFAULT_TERMS.items():
            default_en, _default_fr = defaults
            if key in overrides:
                current_terms_en[key] = overrides[key].display_value
                current_terms_fr[key] = overrides[key].display_value_fr
            else:
                current_terms_en[key] = default_en

        form = TerminologyForm(
            request.POST,
            current_terms_en=current_terms_en,
            current_terms_fr=current_terms_fr,
        )
        if form.is_valid():
            form.save()
            messages.success(request, _("Terminology updated."))
            return redirect("admin_settings:terminology")

    # Build table data: key, defaults, current values, is_overridden
    term_rows = []
    for key, defaults in DEFAULT_TERMS.items():
        default_en, default_fr = defaults
        override = overrides.get(key)
        term_rows.append({
            "key": key,
            "default_en": default_en,
            "default_fr": default_fr,
            "current_en": override.display_value if override else default_en,
            "current_fr": override.display_value_fr if override else "",
            "is_overridden": key in overrides,
        })

    return render(request, "admin_settings/terminology.html", {
        "term_rows": term_rows,
    })


@login_required
@admin_required
def terminology_reset(request, term_key):
    """Delete an override, reverting to default."""
    if request.method == "POST":
        TerminologyOverride.objects.filter(term_key=term_key).delete()
        messages.success(request, _("Reset '%(term_key)s' to default.") % {"term_key": term_key})
    return redirect("admin_settings:terminology")


# --- Feature Toggles ---

DEFAULT_FEATURES = {
    "programs": _lazy("Programs module"),
    "custom_fields": _lazy("Custom participant fields"),
    "alerts": _lazy("Metric alerts"),
    "events": _lazy("Event tracking"),
    "funder_reports": _lazy("Funder report exports"),
    "require_client_consent": _lazy("Require participant consent before notes (PIPEDA/PHIPA)"),
}

# Features that default to enabled (most default to disabled)
FEATURES_DEFAULT_ENABLED = {"require_client_consent"}


@login_required
@admin_required
def features(request):
    if request.method == "POST":
        form = FeatureToggleForm(request.POST)
        if form.is_valid():
            feature_key = form.cleaned_data["feature_key"]
            action = form.cleaned_data["action"]
            FeatureToggle.objects.update_or_create(
                feature_key=feature_key,
                defaults={"is_enabled": action == "enable"},
            )
            if action == "enable":
                messages.success(request, _("Feature '%(feature)s' enabled.") % {"feature": feature_key})
            else:
                messages.success(request, _("Feature '%(feature)s' disabled.") % {"feature": feature_key})
            return redirect("admin_settings:features")

    # Build feature list with current state
    current_flags = FeatureToggle.get_all_flags()
    feature_rows = []
    for key, description in DEFAULT_FEATURES.items():
        # Some features default to enabled (e.g., consent requirement for PIPEDA)
        default_state = key in FEATURES_DEFAULT_ENABLED
        feature_rows.append({
            "key": key,
            "description": description,
            "is_enabled": current_flags.get(key, default_state),
        })

    return render(request, "admin_settings/features.html", {
        "feature_rows": feature_rows,
    })


# --- Instance Settings ---

@login_required
@admin_required
def instance_settings(request):
    current_settings = InstanceSetting.get_all()
    if request.method == "POST":
        form = InstanceSettingsForm(request.POST, current_settings=current_settings)
        if form.is_valid():
            form.save()
            messages.success(request, _("Settings updated."))
            return redirect("admin_settings:instance_settings")
    else:
        form = InstanceSettingsForm(current_settings=current_settings)
    return render(request, "admin_settings/instance_settings.html", {"form": form})


# --- Chart Diagnostics ---

@login_required
@admin_required
def diagnose_charts(request):
    """Diagnostic view to check why charts might be empty."""
    from apps.clients.models import ClientFile
    from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
    from apps.plans.models import MetricDefinition, PlanTarget, PlanTargetMetric

    record_id = request.GET.get("client", "DEMO-001")

    # Gather diagnostic data
    lib_metrics = MetricDefinition.objects.filter(is_library=True).count()
    total_ptm = PlanTargetMetric.objects.count()

    client = ClientFile.objects.filter(record_id=record_id).first()
    client_data = None
    chart_simulation = []

    if client:
        targets = PlanTarget.objects.filter(client_file=client, status="default")
        target_data = []
        for t in targets:
            ptm_count = PlanTargetMetric.objects.filter(plan_target=t).count()
            target_data.append({"name": t.name, "metric_count": ptm_count})

        full_notes = ProgressNote.objects.filter(
            client_file=client, note_type="full", status="default"
        ).count()
        quick_notes = ProgressNote.objects.filter(
            client_file=client, note_type="quick", status="default"
        ).count()
        pnt_count = ProgressNoteTarget.objects.filter(
            progress_note__client_file=client
        ).count()
        mv_count = MetricValue.objects.filter(
            progress_note_target__progress_note__client_file=client
        ).count()

        # Simulate exactly what the analysis view does
        for target in targets:
            ptm_links = PlanTargetMetric.objects.filter(
                plan_target=target
            ).select_related("metric_def")

            for ptm in ptm_links:
                metric_def = ptm.metric_def
                values = MetricValue.objects.filter(
                    metric_def=metric_def,
                    progress_note_target__plan_target=target,
                    progress_note_target__progress_note__client_file=client,
                    progress_note_target__progress_note__status="default",
                )
                value_count = values.count()
                numeric_count = sum(
                    1 for v in values if _is_numeric(v.value)
                )
                chart_simulation.append({
                    "target": target.name,
                    "metric": metric_def.name,
                    "values_found": value_count,
                    "numeric_values": numeric_count,
                    "would_show": numeric_count > 0,
                })

        client_data = {
            "record_id": record_id,
            "targets": target_data,
            "target_count": targets.count(),
            "full_notes": full_notes,
            "quick_notes": quick_notes,
            "pnt_count": pnt_count,
            "mv_count": mv_count,
        }

    # Count charts that would display
    charts_would_show = sum(1 for c in chart_simulation if c["would_show"])

    # Determine diagnosis
    diagnosis = None
    diagnosis_type = "info"
    if lib_metrics == 0:
        diagnosis = _("NO LIBRARY METRICS! Run: python manage.py seed")
        diagnosis_type = "error"
    elif total_ptm == 0:
        diagnosis = _("NO METRICS LINKED TO TARGETS! Run: python manage.py seed")
        diagnosis_type = "error"
    elif client_data and client_data["pnt_count"] == 0:
        diagnosis = _("No progress notes linked to targets. Full notes must record data against plan targets.")
        diagnosis_type = "warning"
    elif client_data and client_data["mv_count"] == 0:
        diagnosis = _("No metric values recorded. Enter values when creating full notes.")
        diagnosis_type = "warning"
    elif charts_would_show == 0 and client_data and client_data["mv_count"] > 0:
        diagnosis = _("BUG: %(count)s metric values exist but NO charts would display! Check chart simulation below.") % {"count": client_data['mv_count']}
        diagnosis_type = "error"
    elif charts_would_show > 0:
        diagnosis = _("Data looks good! %(count)s charts should display.") % {"count": charts_would_show}
        diagnosis_type = "success"

    return render(request, "admin_settings/diagnose_charts.html", {
        "lib_metrics": lib_metrics,
        "total_ptm": total_ptm,
        "client_data": client_data,
        "record_id": record_id,
        "diagnosis": diagnosis,
        "diagnosis_type": diagnosis_type,
        "chart_simulation": chart_simulation,
        "charts_would_show": charts_would_show,
    })


def _is_numeric(value):
    """Check if a value can be converted to float."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


# --- Demo Account Directory ---

@login_required
@admin_required
def demo_directory(request):
    """List all demo users and demo clients in one place."""
    from apps.auth_app.models import User
    from apps.clients.models import ClientFile, ClientProgramEnrolment
    from apps.programs.models import UserProgramRole

    demo_users = User.objects.filter(is_demo=True).order_by("-is_admin", "display_name")
    demo_clients = ClientFile.objects.demo().order_by("record_id")

    # Attach roles to each demo user
    user_roles = {}
    for role in UserProgramRole.objects.filter(user__is_demo=True, status="active").select_related("program"):
        user_roles.setdefault(role.user_id, []).append(role)

    user_data = []
    for user in demo_users:
        roles = user_roles.get(user.pk, [])
        role_display = ", ".join(
            f"{r.get_role_display()} ({r.program.name})" for r in roles
        )
        if user.is_admin:
            role_display = _("Administrator") + (f", {role_display}" if role_display else "")
        user_data.append({
            "user": user,
            "roles": role_display or _("No roles assigned"),
        })

    # Attach program enrolments to each demo client
    enrolments = {}
    for enrol in ClientProgramEnrolment.objects.filter(
        client_file__is_demo=True, status="enrolled"
    ).select_related("program"):
        enrolments.setdefault(enrol.client_file_id, []).append(enrol.program.name)

    client_data = []
    for client in demo_clients:
        client_data.append({
            "client": client,
            "programs": ", ".join(enrolments.get(client.pk, [])) or _("Not enrolled"),
        })

    return render(request, "admin_settings/demo_directory.html", {
        "user_data": user_data,
        "client_data": client_data,
        "demo_user_count": len(user_data),
        "demo_client_count": len(client_data),
    })
