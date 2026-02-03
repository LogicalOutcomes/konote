"""Admin settings views: dashboard, terminology, features, instance settings."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from .forms import InstanceSettingsForm, TerminologyForm
from .models import DEFAULT_TERMS, FeatureToggle, InstanceSetting, TerminologyOverride


def admin_required(view_func):
    """Decorator: 403 if user is not an admin."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin:
            return HttpResponseForbidden("Access denied. Admin privileges required.")
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# --- Dashboard ---

@login_required
@admin_required
def dashboard(request):
    return render(request, "admin_settings/dashboard.html")


# --- Terminology ---

@login_required
@admin_required
def terminology(request):
    if request.method == "POST":
        current_terms = TerminologyOverride.get_all_terms()
        form = TerminologyForm(request.POST, current_terms=current_terms)
        if form.is_valid():
            form.save()
            messages.success(request, "Terminology updated.")
            return redirect("admin_settings:terminology")

    # Build table data: key, default, current value, is_overridden
    overrides = dict(TerminologyOverride.objects.values_list("term_key", "display_value"))
    term_rows = []
    for key, default in DEFAULT_TERMS.items():
        term_rows.append({
            "key": key,
            "default": default,
            "current": overrides.get(key, default),
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
        messages.success(request, f"Reset '{term_key}' to default.")
    return redirect("admin_settings:terminology")


# --- Feature Toggles ---

DEFAULT_FEATURES = {
    "programs": "Programs module",
    "custom_fields": "Custom client fields",
    "alerts": "Metric alerts",
    "events": "Event tracking",
    "funder_reports": "Funder report exports",
}


@login_required
@admin_required
def features(request):
    if request.method == "POST":
        feature_key = request.POST.get("feature_key")
        action = request.POST.get("action")
        if feature_key and action in ("enable", "disable"):
            FeatureToggle.objects.update_or_create(
                feature_key=feature_key,
                defaults={"is_enabled": action == "enable"},
            )
            state = "enabled" if action == "enable" else "disabled"
            messages.success(request, f"Feature '{feature_key}' {state}.")
            return redirect("admin_settings:features")

    # Build feature list with current state
    current_flags = FeatureToggle.get_all_flags()
    feature_rows = []
    for key, description in DEFAULT_FEATURES.items():
        feature_rows.append({
            "key": key,
            "description": description,
            "is_enabled": current_flags.get(key, False),
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
            messages.success(request, "Settings updated.")
            return redirect("admin_settings:instance_settings")
    else:
        form = InstanceSettingsForm(current_settings=current_settings)
    return render(request, "admin_settings/instance_settings.html", {"form": form})
