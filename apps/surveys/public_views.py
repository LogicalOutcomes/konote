"""Public survey views — no login required.

These views handle the shareable link channel. Anyone with a valid
link token can view and submit a survey response.
"""
import logging

from django.db import transaction
from django_ratelimit.decorators import ratelimit
from django.http import Http404, HttpResponseGone, HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.utils import timezone
from django.utils.translation import get_language, gettext as _

from apps.audit.models import AuditLog
from apps.portal.survey_helpers import (
    calculate_section_scores,
    filter_visible_sections,
)

from .models import (
    SurveyAnswer,
    SurveyLink,
    SurveyResponse,
)

logger = logging.getLogger(__name__)


def _get_consent_text(survey):
    """Return the appropriate consent text based on current language.

    Uses French text when the language is French and French text is
    available; otherwise falls back to the English consent text.
    """
    lang = get_language() or "en"
    if lang.startswith("fr") and survey.consent_text_fr:
        return survey.consent_text_fr
    return survey.consent_text


def _consent_session_key(link_pk):
    """Return the session key used to track consent for a survey link."""
    return f"consent_given_{link_pk}"


@ratelimit(key="ip", rate="30/h", method="POST", block=True)
def public_survey_form(request, token):
    """Display and process a public survey form via shareable link."""
    try:
        link = get_object_or_404(SurveyLink, token=token)
    except Http404:
        raise  # propagate — token not found is a genuine 404
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

    # Single-response check: show friendly message if cookie exists
    cookie_key = f"survey_done_{link.token[:8]}"
    if link.single_response:
        try:
            request.get_signed_cookie(cookie_key)
            already_responded = True
        except Exception:  # BadSignature, KeyError, etc. — any failure means "not yet responded"
            already_responded = False
    else:
        already_responded = False
    if already_responded:
        return render(request, "surveys/public_already_responded.html", {
            "survey": survey,
        })

    # ----- Consent gate -----
    consent_key = _consent_session_key(link.pk)
    if survey.consent_text:
        if request.method == "POST" and "consent_agree" in request.POST:
            # Respondent is agreeing to consent — store in session and redirect
            request.session[consent_key] = timezone.now().isoformat()
            return redirect("public_survey_form", token=token)

        if not request.session.get(consent_key):
            # Consent not yet given — show consent page
            consent_text = _get_consent_text(survey)
            lang = get_language() or "en"
            consent_lang = "fr" if lang.startswith("fr") and survey.consent_text_fr else "en"
            return render(request, "surveys/public_consent.html", {
                "survey": survey,
                "consent_text": consent_text,
                "consent_lang": consent_lang,
                "link": link,
            })

    sections = survey.sections.filter(
        is_active=True,
    ).prefetch_related("questions").select_related(
        "condition_question",
    ).order_by("sort_order")

    # Materialise queryset once to support conditional filtering
    sections_list = list(sections)

    if request.method == "POST":
        # Honeypot anti-spam check
        if request.POST.get("website"):
            # Bots fill in hidden fields; real users won't see it
            return redirect("public_survey_thank_you", token=link.token)

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
            # Build repopulation dict keyed by question PK
            repopulate = {}
            for section in sections_list:
                for q in section.questions.all():
                    field_name = f"q_{q.pk}"
                    if q.question_type == "multiple_choice":
                        repopulate[q.pk] = ";".join(request.POST.getlist(field_name))
                    else:
                        repopulate[q.pk] = request.POST.get(field_name, "")
            return render(request, "surveys/public_form.html", {
                "survey": survey,
                "sections": sections_list,
                "link": link,
                "posted": request.POST,
                "repopulate": repopulate,
                "errors": errors,
            })

        respondent_name = ""
        if link.collect_name:
            respondent_name = request.POST.get("respondent_name", "").strip()

        # Determine consent timestamp if consent was required
        consent_given_at_val = None
        if survey.consent_text:
            consent_iso = request.session.get(_consent_session_key(link.pk))
            if consent_iso:
                try:
                    from django.utils.dateparse import parse_datetime
                    consent_given_at_val = parse_datetime(consent_iso)
                except (ValueError, TypeError):
                    consent_given_at_val = timezone.now()

        with transaction.atomic():
            response = SurveyResponse.objects.create(
                survey=survey,
                channel="link",
                client_file=None,
                respondent_name_display=respondent_name,
                token=link.token,
                consent_given_at=consent_given_at_val,
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

        # Audit trail — do NOT log respondent_name or IP (PIPEDA 4.4)
        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            action="post",
            resource_type="survey",
            resource_id=response.pk,
            metadata={
                "channel": "public_link",
                "survey_id": survey.pk,
                "survey_name": survey.name,
                "link_token_prefix": link.token[:8],
                "is_anonymous": survey.is_anonymous,
            },
        )

        # Store scores in session if survey allows score display
        if survey.show_scores_to_participant:
            scores = calculate_section_scores(visible_sections, all_answers)
            if scores:
                request.session[f"survey_scores_{link.token}"] = scores

        resp = redirect("public_survey_thank_you", token=link.token)

        # Set signed cookie to discourage repeat submissions
        if link.single_response:
            resp.set_signed_cookie(
                cookie_key, "1",
                max_age=365 * 24 * 60 * 60,  # 1 year
                httponly=True,
                samesite="Lax",
            )

        return resp

    return render(request, "surveys/public_form.html", {
        "survey": survey,
        "sections": sections_list,
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

    # Retrieve scores from session (one-time read, then clean up)
    session_key = f"survey_scores_{link.token}"
    scores = request.session.pop(session_key, None)

    return render(request, "surveys/public_thank_you.html", {
        "survey": link.survey,
        "scores": scores,
    })
