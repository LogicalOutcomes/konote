"""Setup wizard views for first-run guided configuration."""
import json

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from apps.auth_app.decorators import admin_required

from .management.commands.apply_setup import apply_setup_config
from .models import DEFAULT_TERMS, FeatureToggle, InstanceSetting
from .views import DEFAULT_FEATURES, FEATURES_DEFAULT_ENABLED


# Step definitions for the wizard
WIZARD_STEPS = [
    ("instance_settings", _("Instance Settings")),
    ("terminology", _("Terminology")),
    ("features", _("Feature Toggles")),
    ("programs", _("Programs")),
    ("metrics", _("Metrics")),
    ("plan_templates", _("Plan Templates")),
    ("custom_fields", _("Custom Fields")),
    ("review", _("Review & Apply")),
]


def _get_wizard_data(request):
    """Get wizard data from session, initialising if needed."""
    return request.session.get("setup_wizard", {})


def _set_wizard_data(request, data):
    """Save wizard data to session."""
    request.session["setup_wizard"] = data
    request.session.modified = True


def _get_step_index(step_name):
    """Get the index of a step by name."""
    for i, (name, _label) in enumerate(WIZARD_STEPS):
        if name == step_name:
            return i
    return 0


def _get_metric_library():
    """Load the metric library from the JSON seed file."""
    import json
    from pathlib import Path
    seed_file = Path(__file__).resolve().parent.parent.parent / "seeds" / "metric_library.json"
    try:
        with open(seed_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


@login_required
@admin_required
def setup_wizard(request, step=None):
    """Main wizard view - routes to the correct step."""
    if step is None:
        step = "instance_settings"

    step_index = _get_step_index(step)
    wizard_data = _get_wizard_data(request)

    # Build step navigation context
    steps_context = []
    for i, (name, label) in enumerate(WIZARD_STEPS):
        steps_context.append({
            "name": name,
            "label": label,
            "number": i + 1,
            "is_current": name == step,
            "is_completed": name in wizard_data,
        })

    context = {
        "steps": steps_context,
        "current_step": step,
        "step_number": step_index + 1,
        "total_steps": len(WIZARD_STEPS),
        "wizard_data": wizard_data,
        "nav_active": "admin",
    }

    # Dispatch to step-specific handler
    handler = STEP_HANDLERS.get(step)
    if handler is None:
        return redirect("admin_settings:setup_wizard")

    return handler(request, context, wizard_data)


def _handle_instance_settings(request, context, wizard_data):
    """Step 1: Instance settings (product name, support email, etc.)."""
    if request.method == "POST":
        wizard_data["instance_settings"] = {
            "product_name": request.POST.get("product_name", "KoNote"),
            "support_email": request.POST.get("support_email", ""),
            "logo_url": request.POST.get("logo_url", ""),
            "date_format": request.POST.get("date_format", "YYYY-MM-DD"),
            "access_tier": request.POST.get("access_tier", "1"),
        }
        _set_wizard_data(request, wizard_data)
        return redirect("admin_settings:setup_wizard_step", step="terminology")

    current = wizard_data.get("instance_settings", {})
    context["current_data"] = current
    return render(request, "admin_settings/setup_wizard/instance_settings.html", context)


def _handle_terminology(request, context, wizard_data):
    """Step 2: Terminology overrides."""
    if request.method == "POST":
        terms = {}
        for key in DEFAULT_TERMS:
            value = request.POST.get(f"term_{key}", "").strip()
            if value:
                terms[key] = value
        wizard_data["terminology"] = terms
        _set_wizard_data(request, wizard_data)
        return redirect("admin_settings:setup_wizard_step", step="features")

    current = wizard_data.get("terminology", {})
    context["current_data"] = current
    context["default_terms"] = DEFAULT_TERMS
    return render(request, "admin_settings/setup_wizard/terminology.html", context)


def _handle_features(request, context, wizard_data):
    """Step 3: Feature toggles."""
    if request.method == "POST":
        features = {}
        for key in DEFAULT_FEATURES:
            features[key] = request.POST.get(f"feature_{key}") == "on"
        wizard_data["features"] = features
        _set_wizard_data(request, wizard_data)
        return redirect("admin_settings:setup_wizard_step", step="programs")

    current = wizard_data.get("features", {})
    feature_rows = []
    for key, description in DEFAULT_FEATURES.items():
        default_state = key in FEATURES_DEFAULT_ENABLED
        feature_rows.append({
            "key": key,
            "description": description,
            "is_enabled": current.get(key, default_state),
        })
    context["feature_rows"] = feature_rows
    return render(request, "admin_settings/setup_wizard/features.html", context)


def _handle_programs(request, context, wizard_data):
    """Step 4: Programs."""
    if request.method == "POST":
        programs = []
        names = request.POST.getlist("program_name")
        descriptions = request.POST.getlist("program_description")
        colours = request.POST.getlist("program_colour")
        for i, name in enumerate(names):
            if name.strip():
                programs.append({
                    "name": name.strip(),
                    "description": descriptions[i].strip() if i < len(descriptions) else "",
                    "colour_hex": colours[i] if i < len(colours) else "#3B82F6",
                })
        wizard_data["programs"] = programs
        _set_wizard_data(request, wizard_data)
        return redirect("admin_settings:setup_wizard_step", step="metrics")

    context["current_data"] = wizard_data.get("programs", [])
    return render(request, "admin_settings/setup_wizard/programs.html", context)


def _handle_metrics(request, context, wizard_data):
    """Step 5: Metrics - enable/disable from the library."""
    metric_lib = _get_metric_library()

    if request.method == "POST":
        enabled = []
        disabled = []
        for m in metric_lib:
            name = m["name"]
            if request.POST.get(f"metric_{name}") == "on":
                enabled.append(name)
            else:
                disabled.append(name)
        wizard_data["metrics_enabled"] = enabled
        wizard_data["metrics_disabled"] = disabled
        _set_wizard_data(request, wizard_data)
        return redirect("admin_settings:setup_wizard_step", step="plan_templates")

    current_enabled = wizard_data.get("metrics_enabled", [m["name"] for m in metric_lib])
    metrics_with_state = []
    for m in metric_lib:
        metrics_with_state.append({
            "name": m["name"],
            "definition": m["definition"],
            "category": m["category"],
            "is_enabled": m["name"] in current_enabled,
        })
    context["metrics"] = metrics_with_state
    return render(request, "admin_settings/setup_wizard/metrics.html", context)


def _handle_plan_templates(request, context, wizard_data):
    """Step 6: Plan templates."""
    if request.method == "POST":
        templates = []
        template_names = request.POST.getlist("template_name")
        template_descs = request.POST.getlist("template_description")
        for i, name in enumerate(template_names):
            if name.strip():
                templates.append({
                    "name": name.strip(),
                    "description": template_descs[i].strip() if i < len(template_descs) else "",
                    "sections": [],  # Sections can be added in a future enhancement
                })
        wizard_data["plan_templates"] = templates
        _set_wizard_data(request, wizard_data)
        return redirect("admin_settings:setup_wizard_step", step="custom_fields")

    context["current_data"] = wizard_data.get("plan_templates", [])
    return render(request, "admin_settings/setup_wizard/plan_templates.html", context)


def _handle_custom_fields(request, context, wizard_data):
    """Step 7: Custom fields."""
    if request.method == "POST":
        groups = []
        group_titles = request.POST.getlist("group_title")
        for i, title in enumerate(group_titles):
            if title.strip():
                groups.append({
                    "title": title.strip(),
                    "fields": [],  # Fields can be added in a future enhancement
                })
        wizard_data["custom_field_groups"] = groups
        _set_wizard_data(request, wizard_data)
        return redirect("admin_settings:setup_wizard_step", step="review")

    context["current_data"] = wizard_data.get("custom_field_groups", [])
    return render(request, "admin_settings/setup_wizard/custom_fields.html", context)


def _handle_review(request, context, wizard_data):
    """Step 8: Review and apply."""
    if request.method == "POST":
        # Build the config from wizard data
        config = {}
        if "instance_settings" in wizard_data:
            config["instance_settings"] = wizard_data["instance_settings"]
        if "terminology" in wizard_data:
            config["terminology"] = wizard_data["terminology"]
        if "features" in wizard_data:
            config["features"] = wizard_data["features"]
        if "programs" in wizard_data:
            config["programs"] = wizard_data["programs"]
        if "metrics_enabled" in wizard_data:
            config["metrics_enabled"] = wizard_data["metrics_enabled"]
        if "metrics_disabled" in wizard_data:
            config["metrics_disabled"] = wizard_data["metrics_disabled"]
        if "plan_templates" in wizard_data:
            config["plan_templates"] = wizard_data["plan_templates"]
        if "custom_field_groups" in wizard_data:
            config["custom_field_groups"] = wizard_data["custom_field_groups"]

        try:
            summary = apply_setup_config(config)
            # Clear wizard data from session
            if "setup_wizard" in request.session:
                del request.session["setup_wizard"]
            request.session["setup_wizard_summary"] = summary
            messages.success(request, _("Setup configuration applied successfully."))
            return redirect("admin_settings:setup_wizard_complete")
        except Exception as e:
            logging.getLogger("konote.setup").exception("Setup wizard apply failed")
            messages.error(request, _("Error applying configuration. Please check the logs and try again."))

    # Preview what will be applied
    preview = apply_setup_config(wizard_data, dry_run=True)
    context["preview"] = preview
    context["wizard_data_json"] = json.dumps(wizard_data, indent=2)
    return render(request, "admin_settings/setup_wizard/review.html", context)


@login_required
@admin_required
def setup_wizard_complete(request):
    """Success page shown after wizard completes."""
    summary = request.session.pop("setup_wizard_summary", {})
    return render(request, "admin_settings/setup_wizard/complete.html", {
        "summary": summary,
        "nav_active": "admin",
    })


@login_required
@admin_required
def setup_wizard_reset(request):
    """Reset the wizard and start over."""
    if "setup_wizard" in request.session:
        del request.session["setup_wizard"]
    messages.info(request, _("Setup wizard reset. You can start over."))
    return redirect("admin_settings:setup_wizard")


# Map step names to handler functions
STEP_HANDLERS = {
    "instance_settings": _handle_instance_settings,
    "terminology": _handle_terminology,
    "features": _handle_features,
    "programs": _handle_programs,
    "metrics": _handle_metrics,
    "plan_templates": _handle_plan_templates,
    "custom_fields": _handle_custom_fields,
    "review": _handle_review,
}

