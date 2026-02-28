"""Survey views — management (staff/admin) and participant-level."""
import csv
import io
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import inlineformset_factory
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.auth_app.decorators import admin_required, requires_permission
from apps.programs.access import get_client_or_403

from .engine import is_surveys_enabled
from .forms import (
    CSVImportForm,
    ManualAssignmentForm,
    SurveyForm,
    SurveyQuestionForm,
    SurveySectionForm,
    TriggerRuleForm,
)
from .models import (
    Survey,
    SurveyAnswer,
    SurveyAssignment,
    SurveyLink,
    SurveyQuestion,
    SurveyResponse,
    SurveySection,
    SurveyTriggerRule,
)

logger = logging.getLogger(__name__)

SectionFormSet = inlineformset_factory(
    Survey,
    SurveySection,
    form=SurveySectionForm,
    extra=1,
    can_delete=True,
)


def _surveys_or_404():
    """Raise 404 if surveys feature is disabled."""
    if not is_surveys_enabled():
        raise Http404


# ---------------------------------------------------------------------------
# Management views — /manage/surveys/ (Admin + PM)
# ---------------------------------------------------------------------------


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def survey_list(request):
    """List all surveys."""
    _surveys_or_404()
    surveys = Survey.objects.all()
    return render(request, "surveys/admin/survey_list.html", {
        "surveys": surveys,
    })


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def survey_create(request):
    """Create a new survey with sections."""
    _surveys_or_404()
    if request.method == "POST":
        form = SurveyForm(request.POST)
        formset = SectionFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            survey = form.save(commit=False)
            survey.created_by = request.user
            survey.save()
            formset.instance = survey
            formset.save()
            messages.success(request, _("Survey created."))
            return redirect("survey_manage:survey_questions", survey_id=survey.pk)
    else:
        form = SurveyForm()
        formset = SectionFormSet()
    for section_form in formset:
        section_form.fields["condition_question"].queryset = (
            SurveyQuestion.objects.none()
        )
    return render(request, "surveys/admin/survey_form.html", {
        "form": form,
        "formset": formset,
        "editing": False,
    })


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def survey_edit(request, survey_id):
    """Edit an existing survey."""
    _surveys_or_404()
    survey = get_object_or_404(Survey, pk=survey_id)
    if request.method == "POST":
        form = SurveyForm(request.POST, instance=survey)
        formset = SectionFormSet(request.POST, instance=survey)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, _("Survey updated."))
            return redirect("survey_manage:survey_detail", survey_id=survey.pk)
    else:
        form = SurveyForm(instance=survey)
        formset = SectionFormSet(instance=survey)
    all_questions = SurveyQuestion.objects.filter(
        section__survey=survey, section__is_active=True,
    ).select_related("section").order_by("section__sort_order", "sort_order")
    for section_form in formset:
        section_form.fields["condition_question"].queryset = all_questions
        section_form.fields["condition_question"].label_from_instance = (
            lambda q: f"{q.section.title} \u2192 {q.question_text[:60]}"
        )
    return render(request, "surveys/admin/survey_form.html", {
        "form": form,
        "formset": formset,
        "editing": True,
        "survey": survey,
    })


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def survey_detail(request, survey_id):
    """View survey details — questions, responses, rules."""
    _surveys_or_404()
    survey = get_object_or_404(Survey, pk=survey_id)
    sections = survey.sections.filter(is_active=True).prefetch_related("questions").select_related("condition_question")
    responses = survey.responses.order_by("-submitted_at")[:20]
    rules = survey.trigger_rules.all()
    response_count = survey.responses.count()
    return render(request, "surveys/admin/survey_detail.html", {
        "survey": survey,
        "sections": sections,
        "responses": responses,
        "rules": rules,
        "response_count": response_count,
    })


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def survey_questions(request, survey_id):
    """Add or edit questions for a survey."""
    _surveys_or_404()
    survey = get_object_or_404(Survey, pk=survey_id)
    sections = survey.sections.filter(is_active=True).order_by("sort_order").select_related("condition_question")

    if request.method == "POST":
        # Process question additions/edits from form
        action = request.POST.get("action", "")

        if action == "add_question":
            section_id = request.POST.get("section_id")
            section = get_object_or_404(SurveySection, pk=section_id, survey=survey)
            q_form = SurveyQuestionForm(request.POST)
            if q_form.is_valid():
                question = q_form.save(commit=False)
                question.section = section
                # Handle options for choice-type questions
                options_text = request.POST.get("options_text", "")
                if options_text and question.question_type in (
                    "single_choice", "multiple_choice",
                ):
                    options = []
                    for i, line in enumerate(options_text.strip().split("\n")):
                        line = line.strip()
                        if line:
                            options.append({
                                "value": str(i + 1),
                                "label": line,
                                "label_fr": "",
                                "score": i,
                            })
                    question.options_json = options
                question.save()
                messages.success(request, _("Question added."))
            else:
                messages.error(request, _("Please fix the errors below."))
                return render(request, "surveys/admin/survey_questions.html", {
                    "survey": survey,
                    "sections": sections,
                    "q_form": q_form,
                    "add_to_section": section,
                })
            return redirect(
                "survey_manage:survey_questions", survey_id=survey.pk,
            )

        elif action == "delete_question":
            question_id = request.POST.get("question_id")
            question = get_object_or_404(
                SurveyQuestion, pk=question_id, section__survey=survey,
            )
            question.delete()
            messages.success(request, _("Question removed."))
            return redirect(
                "survey_manage:survey_questions", survey_id=survey.pk,
            )

        elif action == "activate":
            survey.status = "active"
            survey.save(update_fields=["status"])
            messages.success(request, _("Survey is now active."))
            return redirect("survey_manage:survey_detail", survey_id=survey.pk)

    q_form = SurveyQuestionForm()
    return render(request, "surveys/admin/survey_questions.html", {
        "survey": survey,
        "sections": sections,
        "q_form": q_form,
    })


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def survey_status(request, survey_id):
    """Change survey status (activate, close, archive)."""
    _surveys_or_404()
    survey = get_object_or_404(Survey, pk=survey_id)
    if request.method == "POST":
        new_status = request.POST.get("status", "")
        if new_status in dict(Survey.STATUS_CHOICES):
            old_status = survey.status
            survey.status = new_status
            survey.save(update_fields=["status"])
            # Auto-deactivate trigger rules when closing/archiving
            if new_status in ("closed", "archived"):
                survey.trigger_rules.filter(is_active=True).update(is_active=False)
            messages.success(
                request,
                _("Survey status changed from %(old)s to %(new)s.")
                % {"old": old_status, "new": new_status},
            )
    return redirect("survey_manage:survey_detail", survey_id=survey.pk)


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def condition_values(request, survey_id, question_id):
    """Return HTML options for the condition_value dropdown (HTMX)."""
    _surveys_or_404()
    survey = get_object_or_404(Survey, pk=survey_id)
    question = get_object_or_404(
        SurveyQuestion, pk=question_id, section__survey=survey,
    )

    if question.question_type == "yes_no":
        options = [("1", _("Yes")), ("0", _("No"))]
    elif question.question_type in ("single_choice", "multiple_choice", "rating_scale"):
        options = [
            (opt["value"], opt.get("label", opt["value"]))
            for opt in (question.options_json or [])
        ]
    else:
        # short_text / long_text — return a text input instead of a select
        html = (
            '<input type="text" name="condition_value" '
            f'placeholder="{_("Type the exact answer value")}">'
        )
        return HttpResponse(html)

    html_parts = [f'<option value="">— {_("Select a value")} —</option>']
    for value, label in options:
        html_parts.append(f'<option value="{escape(value)}">{escape(label)}</option>')
    return HttpResponse("\n".join(html_parts))


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def survey_response_detail(request, survey_id, response_id):
    """View a single survey response."""
    _surveys_or_404()
    survey = get_object_or_404(Survey, pk=survey_id)
    response = get_object_or_404(
        SurveyResponse, pk=response_id, survey=survey,
    )
    answers = response.answers.select_related("question__section").order_by(
        "question__section__sort_order", "question__sort_order",
    )
    return render(request, "surveys/admin/response_detail.html", {
        "survey": survey,
        "response": response,
        "answers": answers,
    })


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def csv_import(request):
    """Import a survey from CSV."""
    _surveys_or_404()
    if request.method == "POST":
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                csv_file = request.FILES["csv_file"]
                content = csv_file.read().decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(content))

                with transaction.atomic():
                    survey = Survey.objects.create(
                        name=form.cleaned_data["survey_name"],
                        name_fr=form.cleaned_data.get("survey_name_fr", ""),
                        status="draft",
                        created_by=request.user,
                    )

                    sections = {}  # title → SurveySection
                    q_order = 0

                    for row_num, row in enumerate(reader, start=2):
                        section_title = row.get("section", "").strip()
                        if not section_title:
                            messages.error(
                                request,
                                _("Row %(num)d: missing section title.")
                                % {"num": row_num},
                            )
                            raise ValueError("Missing section title")

                        if section_title not in sections:
                            section = SurveySection.objects.create(
                                survey=survey,
                                title=section_title,
                                title_fr=row.get("section_fr", "").strip(),
                                sort_order=len(sections),
                                instructions=row.get("instructions", "").strip(),
                                page_break=row.get(
                                    "page_break", "",
                                ).strip().lower() == "yes",
                            )
                            sections[section_title] = section

                        section = sections[section_title]

                        question_text = row.get("question", "").strip()
                        if not question_text:
                            continue

                        q_type = row.get("type", "short_text").strip()
                        required = row.get(
                            "required", "no",
                        ).strip().lower() == "yes"

                        # Parse options
                        options_json = []
                        options_str = row.get("options", "").strip()
                        score_str = row.get("score_values", "").strip()
                        options_fr_str = row.get("options_fr", "").strip()

                        if options_str:
                            labels = options_str.split(";")
                            scores = (
                                score_str.split(";") if score_str else []
                            )
                            fr_labels = (
                                options_fr_str.split(";")
                                if options_fr_str else []
                            )
                            for i, lbl in enumerate(labels):
                                opt = {
                                    "value": str(i),
                                    "label": lbl.strip(),
                                    "label_fr": (
                                        fr_labels[i].strip()
                                        if i < len(fr_labels) else ""
                                    ),
                                    "score": (
                                        int(scores[i].strip())
                                        if i < len(scores) else i
                                    ),
                                }
                                options_json.append(opt)

                        # Rating scale min/max
                        min_val = None
                        max_val = None
                        if q_type == "rating_scale" and options_json:
                            min_val = 0
                            max_val = len(options_json) - 1

                        SurveyQuestion.objects.create(
                            section=section,
                            question_text=question_text,
                            question_text_fr=row.get(
                                "question_fr", "",
                            ).strip(),
                            question_type=q_type,
                            sort_order=q_order,
                            required=required,
                            options_json=options_json,
                            min_value=min_val,
                            max_value=max_val,
                        )
                        q_order += 1

                messages.success(
                    request,
                    _("Survey '%(name)s' imported with %(count)d questions.")
                    % {"name": survey.name, "count": q_order},
                )
                return redirect(
                    "survey_manage:survey_questions", survey_id=survey.pk,
                )
            except (ValueError, KeyError, csv.Error) as exc:
                messages.error(
                    request,
                    _("CSV import failed: %(error)s") % {"error": str(exc)},
                )
    else:
        form = CSVImportForm()
    return render(request, "surveys/admin/csv_import.html", {"form": form})


# ---------------------------------------------------------------------------
# Participant-level views — staff viewing/managing surveys on a client file
# ---------------------------------------------------------------------------


@login_required
def client_surveys(request, client_id):
    """Show surveys assigned to a specific participant — staff view."""
    _surveys_or_404()
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden(
            _("You do not have access to this participant."),
        )

    # Evaluate trigger rules on page load
    from .engine import evaluate_survey_rules

    participant_user = getattr(client, "portal_account", None)
    if participant_user:
        evaluate_survey_rules(client, participant_user)

    assignments = SurveyAssignment.objects.filter(
        client_file=client,
    ).select_related("survey", "triggered_by_rule").order_by("-created_at")

    responses = SurveyResponse.objects.filter(
        client_file=client,
    ).select_related("survey").order_by("-submitted_at")

    active_surveys = Survey.objects.filter(status="active")

    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {
            "url": reverse(
                "clients:client_detail", kwargs={"client_id": client.pk},
            ),
            "label": f"{client.display_name} {client.last_name}",
        },
        {"url": "", "label": _("Surveys")},
    ]

    return render(request, "surveys/client_surveys.html", {
        "client": client,
        "assignments": assignments,
        "responses": responses,
        "active_surveys": active_surveys,
        "breadcrumbs": breadcrumbs,
    })


@login_required
def assign_survey(request, client_id):
    """Manually assign a survey to a participant."""
    _surveys_or_404()
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden(
            _("You do not have access to this participant."),
        )

    participant_user = getattr(client, "portal_account", None)
    if not participant_user:
        messages.error(
            request,
            _("This participant does not have a portal account. "
              "You can still enter survey responses on their behalf."),
        )
        return redirect("surveys:client_surveys", client_id=client_id)

    if request.method == "POST":
        form = ManualAssignmentForm(request.POST)
        if form.is_valid():
            SurveyAssignment.objects.create(
                survey=form.cleaned_data["survey"],
                participant_user=participant_user,
                client_file=client,
                status="pending",
                assigned_by=request.user,
                due_date=form.cleaned_data.get("due_date"),
                trigger_reason=_("Manually assigned by staff"),
            )
            messages.success(request, _("Survey assigned."))
            return redirect("surveys:client_surveys", client_id=client_id)
    else:
        form = ManualAssignmentForm()

    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {
            "url": reverse(
                "clients:client_detail", kwargs={"client_id": client.pk},
            ),
            "label": f"{client.display_name} {client.last_name}",
        },
        {
            "url": reverse(
                "surveys:client_surveys", kwargs={"client_id": client.pk},
            ),
            "label": _("Surveys"),
        },
        {"url": "", "label": _("Assign Survey")},
    ]

    return render(request, "surveys/assign_survey.html", {
        "client": client,
        "form": form,
        "breadcrumbs": breadcrumbs,
    })


@login_required
def staff_data_entry(request, client_id, survey_id):
    """Staff fills in a survey on behalf of a participant."""
    _surveys_or_404()
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden(
            _("You do not have access to this participant."),
        )

    survey = get_object_or_404(Survey, pk=survey_id, status="active")
    sections = survey.sections.filter(
        is_active=True,
    ).prefetch_related("questions").select_related("condition_question").order_by("sort_order")

    if request.method == "POST":
        from apps.portal.survey_helpers import filter_visible_sections

        # Materialise queryset once to avoid duplicate DB hits
        sections_list = list(sections)

        # 1. Collect all submitted answers
        all_answers = {}
        for section in sections_list:
            for question in section.questions.all().order_by("sort_order"):
                field_name = f"q_{question.pk}"
                if question.question_type == "multiple_choice":
                    raw_values = request.POST.getlist(field_name)
                    raw_value = ";".join(raw_values) if raw_values else ""
                else:
                    raw_value = request.POST.get(field_name, "").strip()
                if raw_value:
                    all_answers[question.pk] = raw_value

        # 2. Determine which sections are visible based on answers
        visible_sections = filter_visible_sections(sections_list, all_answers)
        visible_section_pks = {s.pk for s in visible_sections}

        # 3. Validate required fields only in visible sections
        errors = []
        answers_data = []
        for section in sections_list:
            for question in section.questions.all().order_by("sort_order"):
                raw_value = all_answers.get(question.pk, "")
                if (question.required
                        and not raw_value
                        and section.pk in visible_section_pks):
                    errors.append(question.question_text)
                if raw_value:
                    answers_data.append((question, raw_value))

        if errors:
            messages.error(
                request,
                _("Please answer all required questions."),
            )
            return render(request, "surveys/staff_data_entry.html", {
                "client": client,
                "survey": survey,
                "sections": sections,
                "posted": request.POST,
                "breadcrumbs": _staff_entry_breadcrumbs(request, client, survey),
            })

        # 4. Save all submitted answers (even from hidden sections)
        with transaction.atomic():
            response = SurveyResponse.objects.create(
                survey=survey,
                client_file=client,
                channel="staff_entered",
            )
            for question, raw_value in answers_data:
                answer = SurveyAnswer(
                    response=response,
                    question=question,
                )
                answer.value = raw_value
                if question.question_type in ("rating_scale", "yes_no"):
                    try:
                        answer.numeric_value = int(raw_value)
                    except (ValueError, TypeError):
                        pass
                elif question.question_type == "single_choice":
                    for opt in (question.options_json or []):
                        if opt.get("value") == raw_value:
                            answer.numeric_value = opt.get("score")
                            break
                answer.save()

        messages.success(request, _("Survey response saved."))
        return redirect("surveys:client_surveys", client_id=client_id)

    return render(request, "surveys/staff_data_entry.html", {
        "client": client,
        "survey": survey,
        "sections": sections,
        "posted": {},
        "breadcrumbs": _staff_entry_breadcrumbs(request, client, survey),
    })


def _staff_entry_breadcrumbs(request, client, survey):
    return [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {
            "url": reverse(
                "clients:client_detail", kwargs={"client_id": client.pk},
            ),
            "label": f"{client.display_name} {client.last_name}",
        },
        {
            "url": reverse(
                "surveys:client_surveys", kwargs={"client_id": client.pk},
            ),
            "label": _("Surveys"),
        },
        {"url": "", "label": survey.name},
    ]


@login_required
@require_POST
def approve_assignment(request, assignment_id):
    """Approve an awaiting-approval survey assignment."""
    _surveys_or_404()
    assignment = get_object_or_404(SurveyAssignment, pk=assignment_id)
    assignment.status = "pending"
    assignment.save(update_fields=["status"])
    messages.success(request, _("Survey assignment approved."))
    return redirect(
        "surveys:client_surveys", client_id=assignment.client_file_id,
    )


@login_required
@require_POST
def dismiss_assignment(request, assignment_id):
    """Dismiss a survey assignment."""
    _surveys_or_404()
    assignment = get_object_or_404(SurveyAssignment, pk=assignment_id)
    assignment.status = "dismissed"
    assignment.save(update_fields=["status"])
    messages.success(request, _("Survey assignment dismissed."))
    return redirect(
        "surveys:client_surveys", client_id=assignment.client_file_id,
    )


@login_required
def client_response_detail(request, client_id, response_id):
    """View a single response on a participant's file."""
    _surveys_or_404()
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden(
            _("You do not have access to this participant."),
        )

    response = get_object_or_404(
        SurveyResponse, pk=response_id, client_file=client,
    )
    answers = response.answers.select_related(
        "question__section",
    ).order_by("question__section__sort_order", "question__sort_order")

    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {
            "url": reverse(
                "clients:client_detail", kwargs={"client_id": client.pk},
            ),
            "label": f"{client.display_name} {client.last_name}",
        },
        {
            "url": reverse(
                "surveys:client_surveys", kwargs={"client_id": client.pk},
            ),
            "label": _("Surveys"),
        },
        {"url": "", "label": response.survey.name},
    ]

    return render(request, "surveys/response_detail.html", {
        "client": client,
        "survey": response.survey,
        "response": response,
        "answers": answers,
        "breadcrumbs": breadcrumbs,
    })


# ---------------------------------------------------------------------------
# Shareable link management — /manage/surveys/<id>/links/
# ---------------------------------------------------------------------------


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def survey_links(request, survey_id):
    """Manage shareable links for a survey."""
    _surveys_or_404()
    survey = get_object_or_404(Survey, pk=survey_id)

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "create":
            expires_days = request.POST.get("expires_days", "")
            expires_at = None
            if expires_days:
                try:
                    expires_at = timezone.now() + timezone.timedelta(
                        days=int(expires_days),
                    )
                except (ValueError, TypeError):
                    pass
            SurveyLink.objects.create(
                survey=survey,
                created_by=request.user,
                collect_name=request.POST.get("collect_name") == "on",
                expires_at=expires_at,
            )
            messages.success(request, _("Shareable link created."))
        elif action == "deactivate":
            link_id = request.POST.get("link_id")
            link = get_object_or_404(SurveyLink, pk=link_id, survey=survey)
            link.is_active = False
            link.save(update_fields=["is_active"])
            messages.success(request, _("Link deactivated."))
        return redirect("survey_manage:survey_links", survey_id=survey.pk)

    links = SurveyLink.objects.filter(survey=survey).order_by("-created_at")
    return render(request, "surveys/admin/survey_links.html", {
        "survey": survey,
        "links": links,
    })


# ---------------------------------------------------------------------------
# Trigger rule management — /manage/surveys/<id>/rules/
# ---------------------------------------------------------------------------


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def survey_rules_list(request, survey_id):
    """List trigger rules for a survey."""
    _surveys_or_404()
    survey = get_object_or_404(Survey, pk=survey_id)
    rules = survey.trigger_rules.select_related(
        "program", "event_type",
    ).order_by("-created_at")
    return render(request, "surveys/admin/rule_list.html", {
        "survey": survey,
        "rules": rules,
    })


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def survey_rule_create(request, survey_id):
    """Create a new trigger rule for a survey."""
    _surveys_or_404()
    survey = get_object_or_404(Survey, pk=survey_id)

    if request.method == "POST":
        form = TriggerRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.survey = survey
            rule.created_by = request.user
            rule.save()
            messages.success(request, _("Trigger rule created."))
            return redirect("survey_manage:survey_rules", survey_id=survey.pk)
    else:
        form = TriggerRuleForm()

    return render(request, "surveys/admin/rule_form.html", {
        "survey": survey,
        "form": form,
    })


@login_required
@requires_permission("template.note.manage", allow_admin=True)
@require_POST
def survey_rule_deactivate(request, survey_id, rule_id):
    """Deactivate a trigger rule."""
    _surveys_or_404()
    survey = get_object_or_404(Survey, pk=survey_id)
    rule = get_object_or_404(SurveyTriggerRule, pk=rule_id, survey=survey)
    rule.is_active = False
    rule.save(update_fields=["is_active"])
    messages.success(request, _("Trigger rule deactivated."))
    return redirect("survey_manage:survey_rules", survey_id=survey.pk)
