"""AI-powered HTMX endpoints — all POST, all rate-limited, no PII."""
import json
import logging
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Q as models_Q
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.admin_settings.models import FeatureToggle
from konote import ai
from konote.forms import (
    GenerateNarrativeForm,
    GoalBuilderChatForm,
    GoalBuilderSaveForm,
    ImproveOutcomeForm,
    SuggestMetricsForm,
    SuggestNoteStructureForm,
    TargetSuggestForm,
)

logger = logging.getLogger(__name__)


def _ai_enabled():
    """Check both the feature toggle and the API key."""
    if not ai.is_ai_available():
        return False
    return FeatureToggle.get_all_flags().get("ai_assist", False)


@login_required
@require_POST
@ratelimit(key="user", rate="20/h", method="POST", block=True)
def suggest_metrics_view(request):
    """Suggest metrics for a plan target description."""
    if not _ai_enabled():
        return HttpResponseForbidden("AI features are not enabled.")

    form = SuggestMetricsForm(request.POST)
    if not form.is_valid():
        return render(request, "ai/_error.html", {"message": "Please enter a target description first."})
    target_description = form.cleaned_data["target_description"]

    # Build catalogue from non-PII metric data
    from apps.plans.models import MetricDefinition

    metrics = list(
        MetricDefinition.objects.filter(is_enabled=True, status="active").values(
            "id", "name", "definition", "category"
        )
    )

    suggestions = ai.suggest_metrics(target_description, metrics)
    if suggestions is None:
        return render(request, "ai/_error.html", {"message": "AI suggestion unavailable. Please try again later."})

    return render(request, "ai/_metric_suggestions.html", {"suggestions": suggestions})


@login_required
@require_POST
@ratelimit(key="user", rate="20/h", method="POST", block=True)
def improve_outcome_view(request):
    """Improve a draft outcome statement."""
    if not _ai_enabled():
        return HttpResponseForbidden("AI features are not enabled.")

    form = ImproveOutcomeForm(request.POST)
    if not form.is_valid():
        return render(request, "ai/_error.html", {"message": "Please enter a draft outcome first."})
    draft_text = form.cleaned_data["draft_text"]

    improved = ai.improve_outcome(draft_text)
    if improved is None:
        return render(request, "ai/_error.html", {"message": "AI suggestion unavailable. Please try again later."})

    return render(request, "ai/_improved_outcome.html", {"improved_text": improved, "original_text": draft_text})


@login_required
@require_POST
@ratelimit(key="user", rate="20/h", method="POST", block=True)
def generate_narrative_view(request):
    """Generate an outcome narrative from aggregate metrics."""
    if not _ai_enabled():
        return HttpResponseForbidden("AI features are not enabled.")

    from apps.notes.models import MetricValue
    from apps.programs.models import Program, UserProgramRole

    form = GenerateNarrativeForm(request.POST)
    if not form.is_valid():
        return render(request, "ai/_error.html", {"message": "Please select a program and date range."})

    program_id = form.cleaned_data["program_id"]
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]

    try:
        program = Program.objects.get(pk=program_id)
    except Program.DoesNotExist:
        return HttpResponseBadRequest("Program not found.")

    # Verify user has access to this program (admin sees all)
    if not request.user.is_admin:
        has_role = UserProgramRole.objects.filter(
            user=request.user, program=program, status="active",
        ).exists()
        if not has_role:
            return HttpResponseForbidden("You do not have access to this program.")

    # Build aggregate stats from metric values — no PII, just numbers
    values = (
        MetricValue.objects.filter(
            progress_note_target__progress_note__client_file__enrolments__program=program,
            progress_note_target__progress_note__client_file__enrolments__status="enrolled",
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        )
        .select_related("metric_def")
    )

    # Aggregate by metric
    from collections import defaultdict

    aggregates = defaultdict(lambda: {"total": 0.0, "count": 0})
    for mv in values:
        try:
            num = float(mv.value)
        except (ValueError, TypeError):
            continue
        key = mv.metric_def.name
        aggregates[key]["total"] += num
        aggregates[key]["count"] += 1
        aggregates[key]["unit"] = mv.metric_def.unit

    aggregate_stats = [
        {
            "metric_name": name,
            "average": round(data["total"] / data["count"], 1) if data["count"] else 0,
            "count": data["count"],
            "unit": data.get("unit", ""),
        }
        for name, data in aggregates.items()
    ]

    if not aggregate_stats:
        return render(request, "ai/_error.html", {"message": "No metric data found for this period."})

    date_range = f"{date_from} to {date_to}"
    narrative = ai.generate_narrative(program.name, date_range, aggregate_stats)
    if narrative is None:
        return render(request, "ai/_error.html", {"message": "AI narrative unavailable. Please try again later."})

    return render(request, "ai/_narrative.html", {"narrative": narrative, "program_name": program.name})


@login_required
@require_POST
@ratelimit(key="user", rate="20/h", method="POST", block=True)
def suggest_note_structure_view(request):
    """Suggest a progress note structure for a plan target."""
    if not _ai_enabled():
        return HttpResponseForbidden("AI features are not enabled.")

    from apps.plans.models import PlanTarget
    from apps.programs.models import UserProgramRole

    form = SuggestNoteStructureForm(request.POST)
    if not form.is_valid():
        return render(request, "ai/_error.html", {"message": "No target selected."})

    try:
        target = PlanTarget.objects.select_related("plan_section__program").get(
            pk=form.cleaned_data["target_id"]
        )
    except PlanTarget.DoesNotExist:
        return HttpResponseBadRequest("Target not found.")

    # Verify user has access to the program that owns this target
    program = target.plan_section.program if target.plan_section else None
    if program and not request.user.is_admin:
        has_role = UserProgramRole.objects.filter(
            user=request.user, program=program, status="active",
        ).exists()
        if not has_role:
            return HttpResponseForbidden("You do not have access to this program.")

    metric_names = list(target.metrics.filter(status="active").values_list("name", flat=True))

    sections = ai.suggest_note_structure(target.name, target.description, metric_names)
    if sections is None:
        return render(request, "ai/_error.html", {"message": "AI suggestion unavailable. Please try again later."})

    return render(request, "ai/_note_structure.html", {"sections": sections, "target_name": target.name})


@login_required
@require_POST
@ratelimit(key="user", rate="20/h", method="POST", block=True)
def suggest_target_view(request):
    """Suggest a structured target from participant words. HTMX POST.

    Takes the participant's own words and returns an AI-generated suggestion
    card with target name, SMART description, section, and recommended metrics.
    """
    if not _ai_enabled():
        return HttpResponseForbidden("AI features are not enabled.")

    form = TargetSuggestForm(request.POST)
    if not form.is_valid():
        return render(request, "ai/_error.html", {
            "message": _("Please describe what the participant wants to work on."),
        })

    participant_words = form.cleaned_data["participant_words"]
    client_id = form.cleaned_data["client_id"]

    from apps.clients.models import ClientFile
    from apps.plans.models import PlanSection
    from apps.plans.views import _can_edit_plan
    from apps.programs.access import get_client_or_403
    from apps.reports.pii_scrub import scrub_pii

    client_file = get_client_or_403(request, client_id)
    if client_file is None:
        return HttpResponseForbidden("You do not have access to this client.")
    if not _can_edit_plan(request.user, client_file):
        return HttpResponseForbidden("You don't have permission to edit this plan.")

    # PII-scrub before sending to AI
    known_names = _get_known_names_for_client(client_file)
    scrubbed_words = scrub_pii(participant_words, known_names)

    # Build AI context
    program, metric_catalogue, existing_sections = _get_goal_builder_context(client_file)
    program_name = program.name if program else "General"

    # Call AI
    result = ai.suggest_target(scrubbed_words, program_name, metric_catalogue, existing_sections)

    if result is None:
        return render(request, "plans/_ai_suggest_error.html", {
            "client": client_file,
            "participant_words": participant_words,
        })

    # Resolve suggested section name to a PK if it matches an existing section
    section_choices = list(
        PlanSection.objects.filter(client_file=client_file, status="default")
        .values("pk", "name")
    )
    matched_section_pk = None
    for sc in section_choices:
        if sc["name"].lower().strip() == result.get("suggested_section", "").lower().strip():
            matched_section_pk = sc["pk"]
            break

    # Serialise suggestion for embedding as data attribute
    suggestion_json = json.dumps(result)

    return render(request, "plans/_ai_suggestion.html", {
        "suggestion": result,
        "suggestion_json": suggestion_json,
        "client": client_file,
        "participant_words": participant_words,
        "sections": section_choices,
        "matched_section_pk": matched_section_pk,
    })


@login_required
@require_POST
@ratelimit(key="user", rate="10/h", method="POST", block=True)
def outcome_insights_view(request):
    """Generate AI narrative draft from qualitative outcome data. HTMX POST.

    Access control: user must have an active role (staff+) in the requested
    program. Without this check, any authenticated user could POST with an
    arbitrary program_id and receive AI-processed quotes from that program.
    """
    if not _ai_enabled():
        return HttpResponseForbidden("AI features are not enabled.")

    from apps.programs.models import Program, UserProgramRole
    from apps.reports.insights import get_structured_insights, collect_quotes
    from apps.reports.pii_scrub import scrub_pii
    from apps.reports.models import InsightSummary

    program_id = request.POST.get("program_id")
    date_from_str = request.POST.get("date_from")
    date_to_str = request.POST.get("date_to")
    regenerate = request.POST.get("regenerate")

    if not program_id or not date_from_str or not date_to_str:
        return render(request, "reports/_insights_ai.html", {
            "error": "Please select a program and date range first.",
        })

    try:
        program = Program.objects.get(pk=program_id)
    except Program.DoesNotExist:
        return HttpResponseBadRequest("Program not found.")

    # Verify user has access to this program (admin sees all)
    if not request.user.is_admin:
        has_role = UserProgramRole.objects.filter(
            user=request.user, program=program, status="active",
        ).exists()
        if not has_role:
            return HttpResponseForbidden("You do not have access to this program.")

    try:
        dt_from = date.fromisoformat(date_from_str)
        dt_to = date.fromisoformat(date_to_str)
    except ValueError:
        return HttpResponseBadRequest("Invalid date format.")

    # Check cache first (unless regenerating)
    cache_key = f"insights:{program_id}:{dt_from}:{dt_to}"
    if not regenerate:
        try:
            cached = InsightSummary.objects.get(cache_key=cache_key)
            return render(request, "reports/_insights_ai.html", {
                "summary": cached.summary_json,
                "program_id": program_id,
                "date_from": date_from_str,
                "date_to": date_to_str,
                "generated_at": cached.generated_at,
            })
        except InsightSummary.DoesNotExist:
            pass

    # Collect data
    structured = get_structured_insights(program=program, date_from=dt_from, date_to=dt_to)
    quotes = collect_quotes(
        program=program, date_from=dt_from, date_to=dt_to,
        max_quotes=30, include_dates=False,
    )

    if not quotes and structured["note_count"] < 20:
        return render(request, "reports/_insights_ai.html", {
            "error": "Not enough data to generate a meaningful summary.",
        })

    # PII-scrub quotes before sending to AI
    # Collect known names from clients in this program
    from apps.clients.models import ClientFile, ClientProgramEnrolment
    client_ids = (
        ClientProgramEnrolment.objects.filter(program=program, status="enrolled")
        .values_list("client_file_id", flat=True)
    )
    known_names = set()
    for client in ClientFile.objects.filter(pk__in=client_ids):
        for name in [client.first_name, client.last_name, client.preferred_name]:
            if name and len(name) >= 2:
                known_names.add(name)

    # Also scrub staff names
    from apps.auth_app.models import User
    for user in User.objects.filter(is_active=True):
        display = getattr(user, "display_name", "")
        if display and len(display) >= 2:
            known_names.add(display)

    scrubbed_quotes = []
    # Build ephemeral quote_source_map: scrubbed_text → note_id.
    # This map is NEVER persisted and NEVER sent to the AI.
    # It exists only to reconnect AI-identified themes back to source notes.
    quote_source_map = {}
    for q in quotes:
        # Data minimization: only send scrubbed text and target name to AI.
        # note_id is deliberately excluded — internal IDs should not reach
        # external services (prevents correlation if AI provider is breached).
        scrubbed_text = scrub_pii(q["text"], known_names)
        scrubbed_quotes.append({
            "text": scrubbed_text,
            "target_name": q.get("target_name", ""),
        })
        if q.get("note_id"):
            quote_source_map[scrubbed_text] = q["note_id"]

    # Pass existing active theme names so the AI reuses them.
    from apps.notes.models import SuggestionTheme
    existing_theme_names = list(
        SuggestionTheme.objects.active()
        .filter(program=program)
        .values_list("name", flat=True)
    )

    date_range = f"{dt_from} to {dt_to}"
    result = ai.generate_outcome_insights(
        program.name, date_range, structured, scrubbed_quotes,
        existing_theme_names=existing_theme_names,
    )

    if result is None:
        return render(request, "reports/_insights_ai.html", {
            "error": "AI summary could not be verified. Showing data analysis only.",
        })

    # Cache the validated result
    InsightSummary.objects.update_or_create(
        cache_key=cache_key,
        defaults={
            "summary_json": result,
            "generated_by": request.user,
        },
    )

    # Persist AI-identified suggestion themes as database records.
    if result.get("suggestion_themes"):
        try:
            from apps.notes.theme_engine import process_ai_themes
            process_ai_themes(result["suggestion_themes"], quote_source_map, program)
        except Exception:
            logger.exception("Failed to process AI suggestion themes")

    return render(request, "reports/_insights_ai.html", {
        "summary": result,
        "program_id": program_id,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "generated_at": timezone.now(),
    })


# ── Goal Builder ───────────────────────────────────────────────────


def _get_known_names_for_client(client_file):
    """Collect known names for PII scrubbing: client + enrolled peers + staff."""
    from apps.auth_app.models import User
    from apps.clients.models import ClientFile, ClientProgramEnrolment

    known_names = set()
    # This client's names
    for name in [client_file.first_name, client_file.last_name, client_file.preferred_name]:
        if name and len(name) >= 2:
            known_names.add(name)

    # Active staff names
    for user in User.objects.filter(is_active=True):
        display = getattr(user, "display_name", "")
        if display and len(display) >= 2:
            known_names.add(display)

    return known_names


def _get_goal_builder_context(client_file):
    """Build context for the goal builder AI: metrics catalogue, existing sections, program."""
    from apps.plans.models import MetricDefinition, PlanSection
    from apps.clients.models import ClientProgramEnrolment

    # Get program from client's active enrolment
    enrolment = (
        ClientProgramEnrolment.objects.filter(client_file=client_file, status="enrolled")
        .select_related("program")
        .first()
    )
    program = enrolment.program if enrolment else None

    # Metric catalogue (active metrics visible to this program)
    metrics_qs = MetricDefinition.objects.filter(is_enabled=True, status="active")
    if program:
        metrics_qs = metrics_qs.filter(
            models_Q(owning_program__isnull=True) | models_Q(owning_program=program)
        )
    metric_catalogue = list(metrics_qs.values("id", "name", "definition", "category"))

    # Existing plan sections for this client
    existing_sections = list(
        PlanSection.objects.filter(client_file=client_file, status="default")
        .values_list("name", flat=True)
    )

    return program, metric_catalogue, existing_sections


def _session_key(client_id):
    """Session key for storing goal builder conversation."""
    return f"goal_builder_{client_id}"


@login_required
def goal_builder_start(request, client_id):
    """Open the Goal Builder panel — GET returns the chat panel."""
    if not _ai_enabled():
        return HttpResponseForbidden("AI features are not enabled.")

    from apps.clients.models import ClientFile
    from apps.plans.views import _can_edit_plan

    client_file = get_object_or_404(ClientFile, pk=client_id)
    if not _can_edit_plan(request.user, client_file):
        return HttpResponseForbidden("You don't have permission to edit this plan.")

    # Clear any previous conversation
    request.session.pop(_session_key(client_id), None)

    return render(request, "plans/_goal_builder.html", {
        "client": client_file,
        "messages": [],
        "draft": None,
        "sections": list(
            client_file.plan_sections.filter(status="default").values("pk", "name")
        ),
    })


@login_required
@require_POST
@ratelimit(key="user", rate="20/h", method="POST", block=True)
def goal_builder_chat(request, client_id):
    """Process a chat message in the Goal Builder — POST returns updated panel."""
    if not _ai_enabled():
        return HttpResponseForbidden("AI features are not enabled.")

    from apps.clients.models import ClientFile
    from apps.plans.views import _can_edit_plan
    from apps.reports.pii_scrub import scrub_pii

    client_file = get_object_or_404(ClientFile, pk=client_id)
    if not _can_edit_plan(request.user, client_file):
        return HttpResponseForbidden("You don't have permission to edit this plan.")

    form = GoalBuilderChatForm(request.POST)
    if not form.is_valid():
        return render(request, "plans/_goal_builder.html", {
            "client": client_file,
            "messages": _get_session_messages(request, client_id),
            "draft": None,
            "error": "Please enter a message.",
            "sections": list(
                client_file.plan_sections.filter(status="default").values("pk", "name")
            ),
        })

    user_message = form.cleaned_data["message"]

    # PII-scrub before adding to conversation history
    known_names = _get_known_names_for_client(client_file)
    scrubbed_message = scrub_pii(user_message, known_names)

    # Retrieve conversation history from session
    session_data = request.session.get(_session_key(client_id), {"messages": []})
    conversation = session_data.get("messages", [])

    # Append user message (scrubbed) to conversation
    conversation.append({"role": "user", "content": scrubbed_message})

    # Build AI context
    program, metric_catalogue, existing_sections = _get_goal_builder_context(client_file)
    program_name = program.name if program else "General"

    # Call AI
    result = ai.build_goal_chat(conversation, program_name, metric_catalogue, existing_sections)

    if result is None:
        return render(request, "plans/_goal_builder.html", {
            "client": client_file,
            "messages": _build_display_messages(conversation),
            "draft": None,
            "error": "AI is unavailable right now. Please try again later, or add the goal manually.",
            "sections": list(
                client_file.plan_sections.filter(status="default").values("pk", "name")
            ),
        })

    # Append AI response to conversation (store the raw JSON as the content)
    conversation.append({"role": "assistant", "content": json.dumps(result)})

    # Save to session
    session_data["messages"] = conversation
    # Store the latest unscrubbed user words for client_goal if AI captured them
    if result.get("draft") and result["draft"].get("client_goal"):
        session_data["last_user_words"] = user_message
    request.session[_session_key(client_id)] = session_data
    request.session.modified = True

    return render(request, "plans/_goal_builder.html", {
        "client": client_file,
        "messages": _build_display_messages(conversation),
        "draft": result.get("draft"),
        "draft_json": json.dumps(result.get("draft")) if result.get("draft") else "",
        "sections": list(
            client_file.plan_sections.filter(status="default").values("pk", "name")
        ),
    })


@login_required
@require_POST
def goal_builder_save(request, client_id):
    """Save a goal from the Goal Builder — POST creates target + metric + section.

    Uses the shared _create_goal() helper for atomic section + target + revision
    + metric creation. Custom metric creation (from AI) is handled here before
    calling the helper.
    """

    from apps.clients.models import ClientFile
    from apps.plans.models import MetricDefinition, PlanSection
    from apps.plans.views import _can_edit_plan, _create_goal
    from apps.clients.models import ClientProgramEnrolment

    client_file = get_object_or_404(ClientFile, pk=client_id)
    if not _can_edit_plan(request.user, client_file):
        return HttpResponseForbidden("You don't have permission to edit this plan.")

    form = GoalBuilderSaveForm(request.POST)
    if not form.is_valid():
        return render(request, "plans/_goal_builder.html", {
            "client": client_file,
            "messages": _get_session_messages(request, client_id),
            "draft": None,
            "error": "Please check the form — some required fields are missing.",
            "sections": list(
                client_file.plan_sections.filter(status="default").values("pk", "name")
            ),
        })

    cleaned = form.cleaned_data

    # Get program from enrolment
    enrolment = (
        ClientProgramEnrolment.objects.filter(client_file=client_file, status="enrolled")
        .select_related("program")
        .first()
    )
    program = enrolment.program if enrolment else None

    # Resolve section
    section = None
    if cleaned.get("section_id"):
        section = PlanSection.objects.filter(
            pk=cleaned["section_id"], client_file=client_file,
        ).first()

    # Resolve metric — existing or create custom (AI-specific)
    metric_ids = []
    if cleaned.get("existing_metric_id"):
        metric = MetricDefinition.objects.filter(
            pk=cleaned["existing_metric_id"], is_enabled=True, status="active",
        ).first()
        if metric:
            metric_ids.append(metric.pk)

    if not metric_ids and cleaned.get("metric_name"):
        metric = MetricDefinition.objects.create(
            name=cleaned["metric_name"],
            definition=cleaned.get("metric_definition", ""),
            min_value=cleaned.get("metric_min", 1),
            max_value=cleaned.get("metric_max", 5),
            unit=cleaned.get("metric_unit", "score"),
            is_library=False,
            owning_program=program,
            category="custom",
        )
        metric_ids.append(metric.pk)

    try:
        _create_goal(
            client_file=client_file,
            user=request.user,
            name=cleaned["name"],
            description=cleaned.get("description", ""),
            client_goal=cleaned.get("client_goal", ""),
            section=section,
            new_section_name=cleaned.get("new_section_name", ""),
            program=program,
            metric_ids=metric_ids,
        )
    except ValueError:
        return render(request, "plans/_goal_builder.html", {
            "client": client_file,
            "messages": _get_session_messages(request, client_id),
            "draft": None,
            "error": "Could not determine which section to place the goal in.",
            "sections": list(
                client_file.plan_sections.filter(status="default").values("pk", "name")
            ),
        })

    # Clear session conversation
    request.session.pop(_session_key(client_id), None)

    return redirect("plans:plan_view", client_id=client_id)


def _get_session_messages(request, client_id):
    """Retrieve and format conversation messages from session."""
    session_data = request.session.get(_session_key(client_id), {"messages": []})
    return _build_display_messages(session_data.get("messages", []))


def _build_display_messages(conversation):
    """Convert raw conversation to display-friendly format.

    User messages are shown as-is. Assistant messages are parsed from JSON
    to extract the display message text.
    """
    display = []
    for msg in conversation:
        if msg["role"] == "user":
            display.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            try:
                parsed = json.loads(msg["content"])
                display.append({
                    "role": "assistant",
                    "content": parsed.get("message", ""),
                    "questions": parsed.get("questions", []),
                })
            except (json.JSONDecodeError, TypeError):
                display.append({"role": "assistant", "content": msg["content"]})
    return display
