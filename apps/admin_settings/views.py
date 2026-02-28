"""Admin settings views: dashboard, terminology, features, instance settings."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _, gettext_lazy as _lazy

from apps.auth_app.decorators import admin_required

from .forms import (
    BackupReminderForm, DemoDataForm, FeatureToggleForm, InstanceSettingsForm,
    MessagingSettingsForm, OrganizationProfileForm, TerminologyForm,
)
from .models import (
    DEFAULT_TERMS, TERM_HELP_TEXT,
    FeatureToggle, InstanceSetting, OrganizationProfile, TerminologyOverride,
)


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

    # Partners and report templates count
    from apps.reports.models import Partner, ReportTemplate
    partner_count = Partner.objects.count()
    report_template_count = ReportTemplate.objects.count()

    # Messaging profile for dashboard card
    current_settings = InstanceSetting.get_all()
    messaging_profile = current_settings.get("messaging_profile", "record_keeping")

    # Field access card (Tier 2+ only)
    from apps.admin_settings.models import get_access_tier
    from apps.clients.models import CustomFieldDefinition, FieldAccessConfig
    access_tier = get_access_tier()
    field_access_count = 0
    if access_tier >= 2:
        # Count core fields with view or edit access
        access_map = FieldAccessConfig.get_all_access()
        field_access_count += sum(1 for v in access_map.values() if v in ("view", "edit"))
        # Count custom fields with view or edit access
        field_access_count += CustomFieldDefinition.objects.filter(
            status="active", front_desk_access__in=["view", "edit"]
        ).count()

    # Access grants card (Tier 3 only)
    active_grant_count = 0
    active_reason_count = 0
    if access_tier >= 3:
        from apps.auth_app.models import AccessGrant, AccessGrantReason
        from django.utils import timezone as tz
        active_grant_count = AccessGrant.objects.filter(
            is_active=True, expires_at__gt=tz.now()
        ).count()
        active_reason_count = AccessGrantReason.objects.filter(is_active=True).count()

    return render(request, "admin_settings/dashboard.html", {
        "enabled_features": enabled_features,
        "total_features": total_features,
        "terminology_overrides": terminology_overrides,
        "active_users": active_users,
        "note_template_count": note_template_count,
        "instance_settings_count": instance_settings_count,
        "demo_users": demo_users,
        "partner_count": partner_count,
        "report_template_count": report_template_count,
        "messaging_profile": messaging_profile,
        "access_tier": access_tier,
        "field_access_count": field_access_count,
        "active_grant_count": active_grant_count,
        "active_reason_count": active_reason_count,
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
            "help_text": TERM_HELP_TEXT.get(key, ""),
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
    "programs": {
        "label": _lazy("Programs"),
        "description": _lazy("Organise services into separate programs with their own staff, templates, and metrics."),
        "when_on": [_lazy("Staff see a program selector when viewing participants"), _lazy("Participants can be enrolled in multiple programs"), _lazy("Templates and metrics can be scoped per program")],
        "when_off": [_lazy("All participants appear in a single list"), _lazy("Program enrolments are hidden but data is preserved")],
        "depends_on": [],
        "used_by": ["program_reports", "cross_program_note_sharing"],
    },
    "custom_fields": {
        "label": _lazy("Custom Participant Fields"),
        "description": _lazy("Add extra data fields to participant files (funding source, referral date, etc.)."),
        "when_on": [_lazy("Staff see custom field groups on participant files"), _lazy("Custom fields appear in registration forms")],
        "when_off": [_lazy("Custom field sections are hidden"), _lazy("Existing field data is preserved")],
        "depends_on": [],
        "used_by": [],
    },
    "alerts": {
        "label": _lazy("Metric Alerts"),
        "description": _lazy("Notify staff when outcome metrics hit configurable thresholds."),
        "when_on": [_lazy("Alert badges appear on participant files when metrics cross thresholds"), _lazy("Staff see alert counts on the dashboard")],
        "when_off": [_lazy("Alert badges and notifications are hidden"), _lazy("Threshold configurations are preserved")],
        "depends_on": [],
        "used_by": [],
    },
    "events": {
        "label": _lazy("Event Tracking"),
        "description": _lazy("Record significant events like intake, discharge, crisis, and milestones on participant timelines."),
        "when_on": [_lazy("Staff can record events on participant files"), _lazy("Events appear on the participant timeline")],
        "when_off": [_lazy("Event recording is hidden"), _lazy("Existing events are preserved on timelines")],
        "depends_on": [],
        "used_by": [],
    },
    "program_reports": {
        "label": _lazy("Program Reports"),
        "description": _lazy("Generate formatted outcome reports for funders with demographic breakdowns."),
        "when_on": [_lazy("Executives and PMs can generate and export program reports"), _lazy("Report template management is available")],
        "when_off": [_lazy("Report generation menu is hidden"), _lazy("Existing reports remain downloadable")],
        "depends_on": [],
        "used_by": [],
    },
    "require_client_consent": {
        "label": _lazy("Consent Requirement"),
        "description": _lazy("Require documented participant consent before creating progress notes (PIPEDA/PHIPA compliance)."),
        "when_on": [_lazy("Staff see a consent checkbox on every progress note"), _lazy("Notes cannot be saved without confirming consent")],
        "when_off": [_lazy("Consent checkbox is hidden"), _lazy("Notes can be saved without consent confirmation")],
        "depends_on": [],
        "used_by": [],
    },
    "messaging_email": {
        "label": _lazy("Email Messaging"),
        "description": _lazy("Send email reminders and messages to participants who have consented."),
        "when_on": [_lazy("Staff can send email reminders from the meetings page"), _lazy("Automated email reminders can be scheduled")],
        "when_off": [_lazy("Email sending is disabled"), _lazy("Communication logs are still available for record-keeping")],
        "depends_on": [],
        "used_by": [],
        "requires_config": ["EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD"],
    },
    "messaging_sms": {
        "label": _lazy("SMS Messaging"),
        "description": _lazy("Send text message reminders to participants who have consented (requires Twilio)."),
        "when_on": [_lazy("Staff can send SMS reminders from the meetings page"), _lazy("Automated SMS reminders can be scheduled")],
        "when_off": [_lazy("SMS sending is disabled"), _lazy("Communication logs are still available for record-keeping")],
        "depends_on": [],
        "used_by": [],
        "requires_config": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"],
    },
    "participant_portal": {
        "label": _lazy("Participant Portal"),
        "description": _lazy("Secure portal where participants view their goals, progress, and journal entries."),
        "when_on": [_lazy("Staff can invite participants to the portal"), _lazy("Portal features (journal, messaging, surveys) become available")],
        "when_off": [_lazy("Portal invitation and access is disabled"), _lazy("Existing portal accounts are deactivated")],
        "depends_on": [],
        "used_by": ["portal_journal", "portal_messaging", "portal_resources"],
    },
    "portal_journal": {
        "label": _lazy("Portal Journal"),
        "description": _lazy("Private journal feature in the participant portal."),
        "when_on": [_lazy("Participants see a Journal section in their portal")],
        "when_off": [_lazy("Journal section is hidden from the portal"), _lazy("Existing journal entries are preserved")],
        "depends_on": ["participant_portal"],
        "used_by": [],
    },
    "portal_messaging": {
        "label": _lazy("Portal Messaging"),
        "description": _lazy("Secure messaging between participants and their workers through the portal."),
        "when_on": [_lazy("Participants can send messages to their worker from the portal"), _lazy("Workers see portal messages in the staff messaging view")],
        "when_off": [_lazy("Messaging section is hidden from the portal"), _lazy("Existing messages are preserved")],
        "depends_on": ["participant_portal"],
        "used_by": [],
    },
    "surveys": {
        "label": _lazy("Surveys"),
        "description": _lazy("Structured feedback forms with trigger rules, shareable links, and scoring."),
        "when_on": [_lazy("Surveys menu appears in the navigation bar"), _lazy("Staff can assign and enter surveys on participant files"), _lazy("Surveys appear in the participant portal")],
        "when_off": [_lazy("Surveys menu and tab are hidden"), _lazy("Existing survey data is preserved")],
        "depends_on": [],
        "used_by": [],
    },
    "ai_assist": {
        "label": _lazy("AI Assist"),
        "description": _lazy("AI-powered features including goal builder and narrative generation."),
        "when_on": [_lazy("AI Goal Builder appears on the plan page"), _lazy("AI narrative generation is available in reports")],
        "when_off": [_lazy("AI features are hidden"), _lazy("No data is sent to AI services")],
        "depends_on": [],
        "used_by": [],
    },
    "groups": {
        "label": _lazy("Groups"),
        "description": _lazy("Group sessions and attendance tracking."),
        "when_on": [_lazy("Groups menu appears in the navigation bar"), _lazy("Staff can create groups, record sessions, and track attendance")],
        "when_off": [_lazy("Groups menu is hidden"), _lazy("Existing group data is preserved")],
        "depends_on": [],
        "used_by": [],
    },
    "quick_notes": {
        "label": _lazy("Quick Notes"),
        "description": _lazy("Lightweight contact logging for phone calls, texts, emails, and brief interactions."),
        "when_on": [_lazy("Quick note buttons appear on participant files"), _lazy("Staff can log brief contacts without a full note form")],
        "when_off": [_lazy("Quick note buttons are hidden"), _lazy("Existing quick notes are preserved")],
        "depends_on": [],
        "used_by": [],
    },
    "analysis_charts": {
        "label": _lazy("Analysis Charts"),
        "description": _lazy("Progress visualisation charts on participant files showing metric trends over time."),
        "when_on": [_lazy("Analysis tab with charts appears on participant files")],
        "when_off": [_lazy("Analysis tab is hidden"), _lazy("Metric data is still recorded in notes")],
        "depends_on": [],
        "used_by": [],
    },
    "shift_summaries": {
        "label": _lazy("Shift Summaries"),
        "description": _lazy("End-of-shift summary generation for team handoffs."),
        "when_on": [_lazy("Shift summary feature is available")],
        "when_off": [_lazy("Shift summary feature is hidden")],
        "depends_on": [],
        "used_by": [],
    },
    "client_avatar": {
        "label": _lazy("Participant Avatars"),
        "description": _lazy("Display participant initials or photos as avatars in lists and file headers."),
        "when_on": [_lazy("Avatar circles appear next to participant names")],
        "when_off": [_lazy("Avatars are hidden")],
        "depends_on": [],
        "used_by": [],
    },
    "plan_export_to_word": {
        "label": _lazy("Plan Export to Word"),
        "description": _lazy("Export participant outcome plans as formatted Word documents."),
        "when_on": [_lazy("Export to Word button appears on plan pages")],
        "when_off": [_lazy("Export button is hidden")],
        "depends_on": [],
        "used_by": [],
    },
    "cross_program_note_sharing": {
        "label": _lazy("Cross-Program Note Sharing"),
        "description": _lazy("Share clinical notes across programs for shared participants."),
        "when_on": [_lazy("Staff can see notes from other programs for participants enrolled in multiple programs")],
        "when_off": [_lazy("Notes are only visible within the program they were created in")],
        "depends_on": ["programs"],
        "used_by": [],
    },
    "field_collection": {
        "label": _lazy("Field Collection"),
        "description": _lazy("Offline mobile data collection for field staff using ODK Central."),
        "when_on": [_lazy("Per-program field collection settings become available"), _lazy("Admin can configure ODK Central sync for attendance and visit notes")],
        "when_off": [_lazy("Field collection settings are hidden"), _lazy("Existing sync configurations are preserved")],
        "depends_on": [],
        "used_by": [],
        "requires_config": ["ODK_CENTRAL_URL"],
    },
    "circles": {
        "label": _lazy("Circles"),
        "description": _lazy("Track families, households, and support networks as circles of connected people."),
        "when_on": [
            _lazy("Circles menu appears in the navigation bar"),
            _lazy("Staff can create circles and manage members"),
            _lazy("Circle membership shows on participant files"),
            _lazy("Notes can be tagged to a circle"),
            _lazy("DV safety: circles with blocked members and fewer than 4 visible members are automatically hidden"),
        ],
        "when_off": [_lazy("Circles menu is hidden — existing circle data is preserved")],
        "depends_on": [],
        "used_by": [],
    },
    "portal_resources": {
        "label": _lazy("Portal Resources"),
        "description": _lazy("Show a Resources page in the participant portal with helpful links to websites."),
        "when_on": [_lazy("Participants see a Resources page in their portal with helpful links"), _lazy("Staff can manage resource links per program and per participant")],
        "when_off": [_lazy("Resources page is hidden from the portal"), _lazy("Existing resource links are preserved")],
        "depends_on": ["participant_portal"],
        "used_by": [],
    },
}

# Features that default to enabled (most default to disabled)
FEATURES_DEFAULT_ENABLED = {"require_client_consent", "portal_journal", "portal_messaging", "cross_program_note_sharing", "portal_resources"}


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
    for key, info in DEFAULT_FEATURES.items():
        # Some features default to enabled (e.g., consent requirement for PIPEDA)
        default_state = key in FEATURES_DEFAULT_ENABLED
        feature_rows.append({
            "key": key,
            "label": info["label"],
            "description": info["description"],
            "when_on": info["when_on"],
            "when_off": info["when_off"],
            "depends_on": info.get("depends_on", []),
            "used_by": info.get("used_by", []),
            "requires_config": info.get("requires_config", []),
            "is_enabled": current_flags.get(key, default_state),
        })

    return render(request, "admin_settings/features.html", {
        "feature_rows": feature_rows,
    })


@login_required
@admin_required
def feature_toggle_confirm(request, feature_key):
    """Return an HTMX partial showing impact info and confirm/cancel buttons."""
    info = DEFAULT_FEATURES.get(feature_key)
    if not info:
        return render(request, "admin_settings/_feature_toggle_confirm.html", {
            "error": _("Unknown feature: %(key)s") % {"key": feature_key},
        })

    current_flags = FeatureToggle.get_all_flags()
    default_state = feature_key in FEATURES_DEFAULT_ENABLED
    is_enabled = current_flags.get(feature_key, default_state)
    action = "disable" if is_enabled else "enable"

    # Resolve dependency labels for display
    dep_labels = [
        str(DEFAULT_FEATURES[k]["label"])
        for k in info.get("depends_on", [])
        if k in DEFAULT_FEATURES
    ]
    used_by_labels = [
        str(DEFAULT_FEATURES[k]["label"])
        for k in info.get("used_by", [])
        if k in DEFAULT_FEATURES
    ]

    return render(request, "admin_settings/_feature_toggle_confirm.html", {
        "feature_key": feature_key,
        "label": info["label"],
        "action": action,
        "impact_items": info["when_off"] if is_enabled else info["when_on"],
        "depends_on": dep_labels,
        "used_by": used_by_labels,
        "requires_config": info.get("requires_config", []),
        "is_enabled": is_enabled,
    })


@login_required
@admin_required
def feature_toggle_action(request, feature_key):
    """Perform the toggle and return an HTMX success partial."""
    if request.method != "POST":
        return redirect("admin_settings:features")

    info = DEFAULT_FEATURES.get(feature_key)
    if not info:
        return redirect("admin_settings:features")

    current_flags = FeatureToggle.get_all_flags()
    default_state = feature_key in FEATURES_DEFAULT_ENABLED
    was_enabled = current_flags.get(feature_key, default_state)
    new_state = not was_enabled

    FeatureToggle.objects.update_or_create(
        feature_key=feature_key,
        defaults={"is_enabled": new_state},
    )

    return render(request, "admin_settings/_feature_toggle_success.html", {
        "feature_key": feature_key,
        "label": info["label"],
        "is_enabled": new_state,
        "action_taken": _("enabled") if new_state else _("disabled"),
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


# --- Messaging Settings ---

@login_required
@admin_required
def messaging_settings(request):
    """Messaging configuration: profile cards, Safety-First, templates, channel status."""
    from apps.communications.models import SystemHealthCheck

    current_settings = InstanceSetting.get_all()
    current_flags = FeatureToggle.get_all_flags()

    if request.method == "POST":
        form = MessagingSettingsForm(request.POST, current_settings=current_settings)
        if form.is_valid():
            form.save()

            from apps.audit.models import AuditLog
            from django.utils import timezone as tz
            AuditLog.objects.using("audit").create(
                event_timestamp=tz.now(),
                user_id=request.user.pk,
                user_display=getattr(request.user, "display_name", str(request.user)),
                action="update",
                resource_type="messaging_settings",
                resource_id=0,
                metadata={"changed_fields": list(form.changed_data)},
            )

            messages.success(request, _("Messaging settings updated."))
            return redirect("admin_settings:messaging_settings")
    else:
        form = MessagingSettingsForm(current_settings=current_settings)

    # Channel status for display
    email_configured = current_flags.get("messaging_email", False)
    sms_configured = current_flags.get("messaging_sms", False)

    # Health status
    health_checks = {h.channel: h for h in SystemHealthCheck.objects.all()}

    current_profile = current_settings.get("messaging_profile", "record_keeping")
    safety_first = current_settings.get("safety_first_mode", "false") == "true"

    return render(request, "admin_settings/messaging_settings.html", {
        "form": form,
        "email_configured": email_configured,
        "sms_configured": sms_configured,
        "health_checks": health_checks,
        "current_profile": current_profile,
        "safety_first": safety_first,
    })


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
        client_file__is_demo=True, status="active"
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


# --- Demo Data Management ---

@login_required
@admin_required
def demo_data_management(request):
    """Manage configuration-aware demo data generation."""
    from django.conf import settings as django_settings

    from apps.auth_app.models import User
    from apps.clients.models import ClientFile
    from apps.notes.models import ProgressNote
    from apps.programs.models import Program

    demo_mode = django_settings.DEMO_MODE
    demo_client_count = ClientFile.objects.filter(is_demo=True).count()
    demo_user_count = User.objects.filter(is_demo=True).count()
    demo_note_count = ProgressNote.objects.filter(
        client_file__is_demo=True
    ).count()
    active_program_count = Program.objects.filter(status="active").count()

    # Check when demo data was last generated
    last_generated = InstanceSetting.objects.filter(
        setting_key="demo_data_generated_at"
    ).values_list("setting_value", flat=True).first()

    if request.method == "POST":
        if not demo_mode:
            messages.error(request, _("Demo mode is not enabled."))
            return redirect("admin_settings:demo_data_management")

        action = request.POST.get("action")

        if action == "generate":
            from apps.admin_settings.demo_engine import DemoDataEngine
            from io import StringIO

            demo_form = DemoDataForm(request.POST)
            if not demo_form.is_valid():
                messages.error(request, _("Invalid parameters for demo data generation."))
                return redirect("admin_settings:demo_data_management")

            clients_per_program = demo_form.cleaned_data["clients_per_program"]
            days_span = demo_form.cleaned_data["days_span"]

            output = StringIO()
            engine = DemoDataEngine(stdout=output, stderr=output)

            try:
                success = engine.run(
                    clients_per_program=clients_per_program,
                    days_span=days_span,
                    force=True,
                )
                if success:
                    # Store generation timestamp
                    from django.utils import timezone as tz
                    InstanceSetting.objects.update_or_create(
                        setting_key="demo_data_generated_at",
                        defaults={"setting_value": tz.now().isoformat()},
                    )
                    messages.success(request, _("Demo data generated successfully."))
                else:
                    messages.warning(request, _("Demo data generation did not complete. Check that programs are configured."))
            except Exception as e:
                messages.error(request, _("Error generating demo data: %(error)s") % {"error": str(e)})

            return redirect("admin_settings:demo_data_management")

        elif action == "clear":
            from apps.admin_settings.demo_engine import DemoDataEngine
            from io import StringIO

            output = StringIO()
            engine = DemoDataEngine(stdout=output, stderr=output)
            engine.cleanup_demo_data()

            InstanceSetting.objects.filter(
                setting_key="demo_data_generated_at"
            ).delete()

            messages.success(request, _("Demo data cleared successfully."))
            return redirect("admin_settings:demo_data_management")

    return render(request, "admin_settings/demo_data.html", {
        "demo_mode": demo_mode,
        "demo_client_count": demo_client_count,
        "demo_user_count": demo_user_count,
        "demo_note_count": demo_note_count,
        "active_program_count": active_program_count,
        "last_generated": last_generated,
    })


# --- Organisation Profile (CIDS) ---

@login_required
@admin_required
def organization_profile(request):
    """Edit the singleton organisation profile for CIDS exports."""
    profile = OrganizationProfile.get_solo()

    if request.method == "POST":
        form = OrganizationProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Organisation profile updated."))
            return redirect("admin_settings:organization_profile")
    else:
        form = OrganizationProfileForm(instance=profile)

    return render(request, "admin_settings/organization_profile.html", {
        "form": form,
        "profile": profile,
    })


# --- Backup & Export Settings ---

@login_required
@admin_required
def backup_settings(request):
    """Configure backup reminder settings on OrganizationProfile."""
    from .forms import BackupReminderForm

    profile = OrganizationProfile.get_solo()

    if request.method == "POST":
        form = BackupReminderForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Backup reminder settings updated."))
            return redirect("admin_settings:backup_settings")
    else:
        form = BackupReminderForm(instance=profile)

    return render(request, "admin_settings/backup_settings.html", {
        "form": form,
        "profile": profile,
    })
