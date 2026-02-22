"""Public survey views — no login required.

These views handle the shareable link channel. Anyone with a valid
link token can view and submit a survey response.
"""
import logging

from django.db import transaction
from django.http import HttpResponseGone, HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.utils.translation import gettext as _

from .models import (
    SurveyAnswer,
    SurveyLink,
    SurveyResponse,
)

logger = logging.getLogger(__name__)


def public_survey_form(request, token):
    """Display and process a public survey form via shareable link."""
    try:
        link = get_object_or_404(SurveyLink, token=token)
    except Exception:
        # Database table may not exist yet, or other unexpected error.
        # Show the expired/unavailable page rather than a raw 500.
        logger.exception("Error loading survey link: %s", token)
        return render(request, "surveys/public_expired.html", {
            "survey": None,
        })

    # Check if link is usable
    if not link.is_active or link.is_expired or link.survey.status != "active":
        return HttpResponseGone(
            render(request, "surveys/public_expired.html", {
                "survey": link.survey,
            }).content,
            content_type="text/html",
        )

    survey = link.survey
    sections = survey.sections.filter(
        is_active=True,
    ).prefetch_related("questions").order_by("sort_order")

    if request.method == "POST":
        # Honeypot anti-spam check
        if request.POST.get("website"):
            # Bots fill in hidden fields; real users won't see it
            return redirect("public_survey_thank_you", token=link.token)

        errors = []
        answers_data = []

        for section in sections:
            for question in section.questions.all().order_by("sort_order"):
                field_name = f"q_{question.pk}"
                if question.question_type == "multiple_choice":
                    raw_values = request.POST.getlist(field_name)
                    raw_value = ";".join(raw_values) if raw_values else ""
                else:
                    raw_value = request.POST.get(field_name, "").strip()

                if question.required and not raw_value:
                    errors.append(question.question_text)
                if raw_value:
                    answers_data.append((question, raw_value))

        if errors:
            # Build repopulation dict keyed by question PK
            repopulate = {}
            for section in sections:
                for q in section.questions.all():
                    field_name = f"q_{q.pk}"
                    if q.question_type == "multiple_choice":
                        repopulate[q.pk] = ";".join(request.POST.getlist(field_name))
                    else:
                        repopulate[q.pk] = request.POST.get(field_name, "")
            return render(request, "surveys/public_form.html", {
                "survey": survey,
                "sections": sections,
                "link": link,
                "posted": request.POST,
                "repopulate": repopulate,
                "errors": errors,
            })

        respondent_name = ""
        if link.collect_name:
            respondent_name = request.POST.get("respondent_name", "").strip()

        with transaction.atomic():
            response = SurveyResponse.objects.create(
                survey=survey,
                channel="link",
                client_file=None,
                respondent_name_display=respondent_name,
                token=link.token,
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

        return redirect("public_survey_thank_you", token=link.token)

    return render(request, "surveys/public_form.html", {
        "survey": survey,
        "sections": sections,
        "link": link,
        "posted": {},
        "repopulate": {},
        "errors": [],
    })


def public_survey_thank_you(request, token):
    """Thank-you page after public survey submission."""
    try:
        link = get_object_or_404(SurveyLink, token=token)
    except Exception:
        logger.exception("Error loading survey link for thank-you: %s", token)
        return render(request, "surveys/public_expired.html", {
            "survey": None,
        })
    return render(request, "surveys/public_thank_you.html", {
        "survey": link.survey,
    })
