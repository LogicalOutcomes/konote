# Surveys Integration — Quick Notes + Participant Portal

> Implementation instructions for connecting the `apps/surveys/` system to (A) quick notes / staff-side views and (B) the participant portal.

**Current state:** Models, trigger engine, and signals are built. Views, templates, and URLs are empty stubs. No survey-related UI exists yet.

**Prerequisites:**
- `apps.surveys` is in `INSTALLED_APPS` ✓
- Feature toggle `surveys` exists in admin settings (seeded as `False`) ✓
- All models have migrations ✓
- Trigger engine (`engine.py`) and signals (`signals.py`) are functional ✓

---

## Part A: Add Surveys to Quick Notes & Staff-Side Views

The goal is to let staff **assign, view, and enter survey responses** from the same participant page where they create quick notes.

### A1. Add survey management URLs

**File:** `apps/surveys/manage_urls.py`

Add URL routes under `/manage/surveys/` for admin/PM-level survey management:

```python
from django.urls import path
from . import views

app_name = "surveys"

urlpatterns = [
    # Survey list and CRUD
    path("", views.survey_list, name="survey_list"),
    path("new/", views.survey_create, name="survey_create"),
    path("<int:survey_id>/", views.survey_detail, name="survey_detail"),
    path("<int:survey_id>/edit/", views.survey_edit, name="survey_edit"),
    path("<int:survey_id>/questions/", views.survey_questions, name="survey_questions"),

    # Trigger rules
    path("<int:survey_id>/rules/", views.survey_rules, name="survey_rules"),
    path("<int:survey_id>/rules/new/", views.rule_create, name="rule_create"),

    # CSV import
    path("import/", views.csv_import, name="csv_import"),

    # Bulk approval of pending assignments
    path("pending/", views.pending_assignments, name="pending_assignments"),
]
```

**File:** `konote/urls.py`

Register the manage URLs. Add this line after the existing `/manage/` routes (around line 56):

```python
path("manage/surveys/", include("apps.surveys.manage_urls")),
```

### A2. Add participant-level survey URLs

**File:** `apps/surveys/urls.py`

These routes appear under a participant's record — for staff to view/manage surveys on a specific client file:

```python
from django.urls import path
from . import views

app_name = "surveys"

urlpatterns = [
    # Staff views: surveys on a specific participant
    path("participant/<int:client_id>/", views.client_surveys, name="client_surveys"),
    path("participant/<int:client_id>/assign/", views.assign_survey, name="assign_survey"),
    path("participant/<int:client_id>/enter/<int:survey_id>/", views.staff_data_entry, name="staff_data_entry"),
    path("assignment/<int:assignment_id>/approve/", views.approve_assignment, name="approve_assignment"),
    path("assignment/<int:assignment_id>/dismiss/", views.dismiss_assignment, name="dismiss_assignment"),
    path("response/<int:response_id>/", views.response_detail, name="response_detail"),
]
```

**File:** `konote/urls.py`

Register participant-level survey URLs. Add after the manage route:

```python
path("surveys/", include("apps.surveys.urls")),
```

### A3. Create survey forms

**File:** `apps/surveys/forms.py`

Build Django forms for survey operations:

```python
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Survey, SurveySection, SurveyQuestion, SurveyAnswer


class SurveyForm(forms.ModelForm):
    """Form for creating/editing a survey."""
    class Meta:
        model = Survey
        fields = ["name", "name_fr", "description", "description_fr",
                  "is_anonymous", "show_scores_to_participant", "portal_visible"]


class SurveySectionForm(forms.ModelForm):
    """Form for a survey section."""
    class Meta:
        model = SurveySection
        fields = ["title", "title_fr", "instructions", "instructions_fr",
                  "sort_order", "page_break", "scoring_method", "max_score"]


class SurveyQuestionForm(forms.ModelForm):
    """Form for a survey question."""
    class Meta:
        model = SurveyQuestion
        fields = ["question_text", "question_text_fr", "question_type",
                  "sort_order", "required", "options_json", "min_value", "max_value"]


class ManualAssignmentForm(forms.Form):
    """Form for staff to manually assign a survey to a participant."""
    survey = forms.ModelChoiceField(
        queryset=Survey.objects.filter(status="active"),
        label=_("Survey"),
        empty_label=_("— Select a survey —"),
    )
    due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("Due date (optional)"),
    )


class StaffDataEntryForm(forms.Form):
    """Dynamic form for staff filling in a survey on behalf of a participant.

    Built dynamically in the view based on the survey's questions.
    Each question becomes a form field named 'q_{question_id}'.
    """
    pass  # Fields are added dynamically in the view


class CSVImportForm(forms.Form):
    """Form for uploading a survey CSV."""
    csv_file = forms.FileField(label=_("CSV file"))
    survey_name = forms.CharField(max_length=255, label=_("Survey name"))
    survey_name_fr = forms.CharField(max_length=255, required=False, label=_("Survey name (French)"))
```

### A4. Build staff-side views

**File:** `apps/surveys/views.py`

The key views to implement:

#### `client_surveys` — Show surveys on a participant's file

This is the primary integration point with the staff-side participant view. Shows:
- Surveys awaiting approval (with Approve/Dismiss buttons)
- Pending and in-progress surveys
- Completed survey responses

```python
@login_required
@requires_permission("note.view", _get_program_from_client)
def client_surveys(request, client_id):
    """Show surveys for a specific participant — staff view."""
    from apps.surveys.engine import evaluate_survey_rules, is_surveys_enabled

    if not is_surveys_enabled():
        raise Http404

    client = get_client_or_403(request, client_id)

    # Evaluate trigger rules on page load (time + characteristic rules)
    participant_user = getattr(client, "portal_account", None)
    if participant_user:
        evaluate_survey_rules(client, participant_user)

    # Get all assignments for this participant
    assignments = SurveyAssignment.objects.filter(
        client_file=client,
    ).select_related("survey", "triggered_by_rule").order_by("-created_at")

    # Get responses (for direct staff-entered responses without assignments)
    responses = SurveyResponse.objects.filter(
        client_file=client,
    ).select_related("survey").order_by("-submitted_at")

    return render(request, "surveys/client_surveys.html", {
        "client": client,
        "assignments": assignments,
        "responses": responses,
    })
```

#### `assign_survey` — Staff manually assigns a survey

```python
@login_required
@requires_permission("note.create", _get_program_from_client)
def assign_survey(request, client_id):
    """Manually assign a survey to a participant."""
    client = get_client_or_403(request, client_id)
    participant_user = getattr(client, "portal_account", None)

    if not participant_user:
        messages.error(request, _("This participant does not have a portal account."))
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
            )
            messages.success(request, _("Survey assigned."))
            return redirect("surveys:client_surveys", client_id=client_id)
    else:
        form = ManualAssignmentForm()

    return render(request, "surveys/assign_survey.html", {
        "client": client,
        "form": form,
    })
```

#### `staff_data_entry` — Staff fills in a survey on behalf of a participant

This is the "quick note" equivalent for surveys — staff can fill in a survey during a session or phone call:

```python
@login_required
@requires_permission("note.create", _get_program_from_client)
def staff_data_entry(request, client_id, survey_id):
    """Staff fills in a survey on behalf of a participant."""
    client = get_client_or_403(request, client_id)
    survey = get_object_or_404(Survey, pk=survey_id, status="active")

    # Build dynamic form from survey questions
    sections = survey.sections.filter(is_active=True).prefetch_related("questions")

    if request.method == "POST":
        # Validate and save all answers
        with transaction.atomic():
            response = SurveyResponse.objects.create(
                survey=survey,
                client_file=client,
                channel="staff_entered",
            )
            for section in sections:
                for question in section.questions.all():
                    field_name = f"q_{question.pk}"
                    raw_value = request.POST.get(field_name, "").strip()
                    if question.required and not raw_value:
                        # Re-render form with errors
                        messages.error(request, _(
                            "Please answer all required questions."
                        ))
                        response.delete()
                        return render(request, "surveys/staff_data_entry.html", {
                            "client": client,
                            "survey": survey,
                            "sections": sections,
                            "posted": request.POST,
                        })

                    if raw_value:
                        answer = SurveyAnswer(
                            response=response,
                            question=question,
                        )
                        answer.value = raw_value
                        # Set numeric_value for scored questions
                        if question.question_type in ("rating_scale", "yes_no"):
                            try:
                                answer.numeric_value = int(raw_value)
                            except (ValueError, TypeError):
                                pass
                        elif question.question_type == "single_choice":
                            # Look up score from options_json
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
    })
```

#### `approve_assignment` / `dismiss_assignment`

```python
@login_required
@require_POST
def approve_assignment(request, assignment_id):
    assignment = get_object_or_404(SurveyAssignment, pk=assignment_id)
    assignment.status = "pending"
    assignment.save(update_fields=["status"])
    messages.success(request, _("Survey assignment approved."))
    return redirect("surveys:client_surveys", client_id=assignment.client_file_id)


@login_required
@require_POST
def dismiss_assignment(request, assignment_id):
    assignment = get_object_or_404(SurveyAssignment, pk=assignment_id)
    assignment.status = "dismissed"
    assignment.save(update_fields=["status"])
    messages.success(request, _("Survey assignment dismissed."))
    return redirect("surveys:client_surveys", client_id=assignment.client_file_id)
```

### A5. Create staff-side templates

#### `templates/surveys/client_surveys.html`

Main section shown on the participant's file. Include this as a tab or a section on the client detail page:

```django-html
{% extends "base.html" %}
{% load i18n %}

{% block content %}
<h2>{% trans "Surveys" %}</h2>

{# Awaiting Approval #}
{% for a in assignments %}
{% if a.status == "awaiting_approval" %}
<article class="survey-pending-approval">
    <p><strong>{{ a.survey.name }}</strong> — {{ a.trigger_reason }}</p>
    <form method="post" action="{% url 'surveys:approve_assignment' a.pk %}" style="display:inline">
        {% csrf_token %}
        <button type="submit" class="small">{% trans "Approve" %}</button>
    </form>
    <form method="post" action="{% url 'surveys:dismiss_assignment' a.pk %}" style="display:inline">
        {% csrf_token %}
        <button type="submit" class="small outline secondary">{% trans "Dismiss" %}</button>
    </form>
</article>
{% endif %}
{% endfor %}

{# Pending / In Progress #}
<h3>{% trans "Pending" %}</h3>
{% for a in assignments %}
{% if a.status == "pending" or a.status == "in_progress" %}
<article>
    <p>{{ a.survey.name }} — {{ a.get_status_display }}
       {% if a.due_date %} · {% trans "Due:" %} {{ a.due_date }}{% endif %}
    </p>
</article>
{% endif %}
{% endfor %}

{# Completed #}
<h3>{% trans "Completed" %}</h3>
{% for a in assignments %}
{% if a.status == "completed" %}
<article>
    <p>{{ a.survey.name }} — {{ a.completed_at|date:"N j, Y" }}</p>
</article>
{% endif %}
{% endfor %}

{# Actions #}
<div class="button-group">
    <a href="{% url 'surveys:assign_survey' client.pk %}" role="button" class="outline">
        {% trans "Assign Survey" %}
    </a>
</div>

{# Staff data entry — show active surveys #}
<h3>{% trans "Enter Responses" %}</h3>
<p>{% trans "Fill in a survey on behalf of this participant:" %}</p>
<ul>
{% for survey in active_surveys %}
    <li><a href="{% url 'surveys:staff_data_entry' client.pk survey.pk %}">{{ survey.name }}</a></li>
{% endfor %}
</ul>

{% endblock %}
```

#### `templates/surveys/staff_data_entry.html`

Dynamic form that renders all survey questions for staff to fill in:

```django-html
{% extends "base.html" %}
{% load i18n %}

{% block content %}
<h1>{{ survey.name }}</h1>
<p>{% blocktrans with name=client.display_name %}Entering responses for {{ name }}{% endblocktrans %}</p>

<form method="post">
    {% csrf_token %}
    {% for section in sections %}
    <fieldset>
        <legend>{{ section.title }}</legend>
        {% if section.instructions %}
        <p><small>{{ section.instructions }}</small></p>
        {% endif %}

        {% for question in section.questions.all %}
        <div class="form-group">
            <label for="q_{{ question.pk }}">
                {{ question.question_text }}
                {% if question.required %}<abbr title="required">*</abbr>{% endif %}
            </label>

            {% if question.question_type == "short_text" %}
            <input type="text" id="q_{{ question.pk }}" name="q_{{ question.pk }}"
                   {% if question.required %}required{% endif %}>

            {% elif question.question_type == "long_text" %}
            <textarea id="q_{{ question.pk }}" name="q_{{ question.pk }}" rows="3"
                      {% if question.required %}required{% endif %}></textarea>

            {% elif question.question_type == "rating_scale" %}
            <input type="number" id="q_{{ question.pk }}" name="q_{{ question.pk }}"
                   min="{{ question.min_value }}" max="{{ question.max_value }}"
                   {% if question.required %}required{% endif %}>

            {% elif question.question_type == "yes_no" %}
            <label><input type="radio" name="q_{{ question.pk }}" value="1"> {% trans "Yes" %}</label>
            <label><input type="radio" name="q_{{ question.pk }}" value="0"> {% trans "No" %}</label>

            {% elif question.question_type == "single_choice" %}
            {% for opt in question.options_json %}
            <label>
                <input type="radio" name="q_{{ question.pk }}" value="{{ opt.value }}">
                {{ opt.label }}
            </label>
            {% endfor %}

            {% elif question.question_type == "multiple_choice" %}
            {% for opt in question.options_json %}
            <label>
                <input type="checkbox" name="q_{{ question.pk }}" value="{{ opt.value }}">
                {{ opt.label }}
            </label>
            {% endfor %}
            {% endif %}
        </div>
        {% endfor %}
    </fieldset>
    {% endfor %}

    <button type="submit">{% trans "Save Response" %}</button>
</form>
{% endblock %}
```

### A6. Link surveys into the quick note flow

There are two integration points with quick notes:

#### Option 1: "Assign a survey" button on the quick note confirmation

After saving a quick note, if the participant has a portal account and the surveys feature is enabled, show a prompt:

**File:** `apps/notes/views.py` — in `quick_note_create`, after saving the note:

```python
# After note.save() and messages.success():
from apps.surveys.engine import is_surveys_enabled
if is_surveys_enabled():
    participant_user = getattr(client, "portal_account", None)
    if participant_user:
        # Redirect to note list with a survey prompt
        messages.info(
            request,
            mark_safe(
                _('Want to send a survey? <a href="%(url)s">Assign one now</a>.')
                % {"url": reverse("surveys:assign_survey", kwargs={"client_id": client.pk})}
            ),
        )
```

#### Option 2: "Fill in a survey" link alongside quick note (recommended)

Add a "Fill in a survey" link to the quick note form page and to the participant timeline, so staff can easily switch between logging a contact and entering survey data.

**File:** `templates/notes/quick_note_form.html` — add above or below the form:

```django-html
{% if features.surveys %}
<aside class="survey-cta">
    <p>{% trans "Need to record survey responses from this interaction?" %}</p>
    <a href="{% url 'surveys:client_surveys' client.pk %}" role="button" class="outline small">
        {% trans "Go to Surveys" %}
    </a>
</aside>
{% endif %}
```

#### Option 3: Inline survey widget on quick note form (advanced)

Add a dropdown to the quick note form that optionally attaches a short survey inline. This is the most seamless but most complex option — only recommended for agencies that use surveys heavily.

**Implementation:** Add a `survey` field to `QuickNoteForm`:

```python
# In apps/notes/forms.py
class QuickNoteForm(forms.Form):
    # ... existing fields ...

    quick_survey = forms.ModelChoiceField(
        queryset=Survey.objects.none(),  # Set in view
        required=False,
        label=_("Attach a quick survey"),
        empty_label=_("— No survey —"),
    )
```

Then in the view, populate the queryset with active surveys and, on POST, create both the note and a `SurveyResponse` with `channel="staff_entered"`.

**Recommendation:** Start with Option 2 (link alongside quick note). It's the simplest and keeps surveys and notes as separate workflows that are easy to navigate between.

### A7. Add surveys to the participant timeline/detail page

Add a "Surveys" tab or section to the client detail page.

**File:** Update the client detail template to include a surveys section when the feature is enabled:

```django-html
{% if features.surveys %}
<section id="surveys">
    <h2>{% trans "Surveys" %}</h2>
    <div hx-get="{% url 'surveys:client_surveys' client.pk %}"
         hx-trigger="revealed"
         hx-target="this">
        <p>{% trans "Loading surveys..." %}</p>
    </div>
</section>
{% endif %}
```

This lazy-loads the surveys section via HTMX so it doesn't slow down the main page.

### A8. Wire up the feature toggle check

**File:** `konote/context_processors.py`

Ensure `features.surveys` is available in templates. If the context processor already reads all feature toggles, no change needed. If it uses a whitelist, add `"surveys"` to it.

### A9. Add survey evaluation to staff client views

**File:** `apps/clients/views.py` (or wherever `client_detail` lives)

Call the trigger engine when staff view a participant's file, so time-based and characteristic rules are evaluated:

```python
# At the top of client_detail view:
from apps.surveys.engine import evaluate_survey_rules, is_surveys_enabled

# Inside the view, after loading client:
if is_surveys_enabled():
    participant_user = getattr(client, "portal_account", None)
    if participant_user:
        evaluate_survey_rules(client, participant_user)
```

---

## Part B: Add Surveys to the Participant Portal

The portal-side experience is called **"Questions for You"** — see [tasks/portal-questions-design.md](../../tasks/portal-questions-design.md) for the full UX design.

### B1. Add portal survey URLs

**File:** `apps/portal/urls.py`

Add these routes to the existing portal URL configuration:

```python
# Questions for You (surveys in portal)
path("questions/", views.questions_list, name="questions"),
path("questions/<int:assignment_id>/", views.question_form, name="question_form"),
path("questions/<int:assignment_id>/page/<int:page>/", views.question_form_page, name="question_form_page"),
path("questions/<int:assignment_id>/save/", views.question_autosave, name="question_autosave"),
path("questions/<int:assignment_id>/save-page/", views.question_save_page, name="question_save_page"),
path("questions/<int:assignment_id>/submit/", views.question_submit, name="question_submit"),
path("questions/<int:assignment_id>/review/", views.question_review, name="question_review"),
```

### B2. Build portal survey views

**File:** `apps/portal/views.py`

Add these views (all decorated with `@portal_login_required`):

#### `questions_list` — List pending and completed surveys

```python
@portal_login_required
def questions_list(request):
    """List the participant's survey assignments."""
    from apps.surveys.engine import evaluate_survey_rules, is_surveys_enabled
    from apps.surveys.models import SurveyAssignment

    if not is_surveys_enabled():
        raise Http404

    participant = request.participant_user
    client_file = _get_client_file(request)

    # Evaluate trigger rules on access
    evaluate_survey_rules(client_file, participant)

    assignments = SurveyAssignment.objects.filter(
        participant_user=participant,
    ).select_related("survey").order_by("-created_at")

    pending = [a for a in assignments if a.status in ("pending", "in_progress")]
    completed = [a for a in assignments if a.status == "completed"]

    return render(request, "portal/questions_list.html", {
        "pending": pending,
        "completed": completed,
    })
```

#### `question_form` — Display the survey form

```python
@portal_login_required
def question_form(request, assignment_id):
    """Show the survey form for a specific assignment."""
    from apps.surveys.models import SurveyAssignment, PartialAnswer

    participant = request.participant_user
    assignment = get_object_or_404(
        SurveyAssignment,
        pk=assignment_id,
        participant_user=participant,
        status__in=["pending", "in_progress"],
    )

    # Mark as in_progress on first open
    if assignment.status == "pending":
        assignment.status = "in_progress"
        assignment.started_at = timezone.now()
        assignment.save(update_fields=["status", "started_at"])

    survey = assignment.survey
    sections = survey.sections.filter(is_active=True).prefetch_related("questions")

    # Load any saved partial answers
    partial_answers = {
        pa.question_id: pa
        for pa in PartialAnswer.objects.filter(assignment=assignment)
    }

    # Determine if this is multi-page
    pages = [s for s in sections if s.page_break]
    is_multipage = len(pages) > 0

    if is_multipage:
        # Show first page
        return redirect("portal:question_form_page", assignment_id=assignment_id, page=1)

    return render(request, "portal/question_form.html", {
        "assignment": assignment,
        "survey": survey,
        "sections": sections,
        "partial_answers": partial_answers,
    })
```

#### `question_autosave` — HTMX auto-save on blur

```python
@portal_login_required
@require_POST
@csrf_exempt  # HTMX sends CSRF via header
def question_autosave(request, assignment_id):
    """Auto-save a single answer via HTMX."""
    from apps.surveys.models import SurveyAssignment, SurveyQuestion, PartialAnswer
    from konote.encryption import encrypt_field

    participant = request.participant_user
    assignment = get_object_or_404(
        SurveyAssignment,
        pk=assignment_id,
        participant_user=participant,
        status="in_progress",
    )

    question_id = request.POST.get("question_id")
    value = request.POST.get("value", "")

    question = get_object_or_404(SurveyQuestion, pk=question_id)

    PartialAnswer.objects.update_or_create(
        assignment=assignment,
        question=question,
        defaults={"value_encrypted": encrypt_field(value)},
    )

    return HttpResponse(status=204)  # No content — autosave confirmed
```

#### `question_submit` — Final submission

```python
@portal_login_required
@require_POST
def question_submit(request, assignment_id):
    """Submit all answers for a survey assignment."""
    from apps.surveys.models import (
        SurveyAssignment, SurveyResponse, SurveyAnswer, PartialAnswer,
    )
    from konote.encryption import decrypt_field

    participant = request.participant_user
    assignment = get_object_or_404(
        SurveyAssignment,
        pk=assignment_id,
        participant_user=participant,
        status="in_progress",
    )

    survey = assignment.survey
    partial_answers = PartialAnswer.objects.filter(
        assignment=assignment,
    ).select_related("question")

    # Validate required questions
    required_questions = SurveyQuestion.objects.filter(
        section__survey=survey,
        section__is_active=True,
        required=True,
    )
    answered_ids = {pa.question_id for pa in partial_answers}
    missing = [q for q in required_questions if q.pk not in answered_ids]

    if missing:
        messages.error(request, _("Please answer all required questions."))
        return redirect("portal:question_form", assignment_id=assignment_id)

    # Create response and move partial answers to final answers
    with transaction.atomic():
        response = SurveyResponse.objects.create(
            survey=survey,
            assignment=assignment,
            client_file=assignment.client_file,
            channel="portal",
        )

        for pa in partial_answers:
            decrypted_value = decrypt_field(pa.value_encrypted)
            answer = SurveyAnswer(
                response=response,
                question=pa.question,
            )
            answer.value = decrypted_value

            # Set numeric_value for scored question types
            q = pa.question
            if q.question_type in ("rating_scale", "yes_no"):
                try:
                    answer.numeric_value = int(decrypted_value)
                except (ValueError, TypeError):
                    pass
            elif q.question_type == "single_choice":
                for opt in (q.options_json or []):
                    if opt.get("value") == decrypted_value:
                        answer.numeric_value = opt.get("score")
                        break

            answer.save()

        # Mark assignment completed
        assignment.status = "completed"
        assignment.completed_at = timezone.now()
        assignment.save(update_fields=["status", "completed_at"])

        # Clean up partial answers
        partial_answers.delete()

    _audit_portal_event(request, "portal_survey_submitted", metadata={
        "survey_id": survey.pk,
        "assignment_id": assignment.pk,
    })

    return render(request, "portal/question_confirm.html", {
        "assignment": assignment,
        "survey": survey,
        "show_scores": survey.show_scores_to_participant,
    })
```

#### `question_review` — View past responses

```python
@portal_login_required
def question_review(request, assignment_id):
    """Read-only view of a completed survey response."""
    from apps.surveys.models import SurveyAssignment, SurveyResponse

    participant = request.participant_user
    assignment = get_object_or_404(
        SurveyAssignment,
        pk=assignment_id,
        participant_user=participant,
        status="completed",
    )

    response = SurveyResponse.objects.filter(
        assignment=assignment,
    ).prefetch_related("answers__question__section").first()

    return render(request, "portal/question_review.html", {
        "assignment": assignment,
        "survey": assignment.survey,
        "response": response,
    })
```

### B3. Create portal templates

#### `apps/portal/templates/portal/questions_list.html`

```django-html
{% extends "portal/base_portal.html" %}
{% load i18n portal_tags %}

{% block title %}{% trans "Questions for You" %}{% endblock %}

{% block content %}
<h1>{% trans "Questions for You" %}</h1>

{% if not pending and not completed %}
<p>{% trans "No questions right now — check back later." %}</p>
{% endif %}

{% if pending %}
<h2>{% trans "New" %}</h2>
{% for a in pending %}
<a href="{% url 'portal:question_form' a.pk %}" class="portal-card">
    <article>
        <h3>{{ a.survey.name }}</h3>
        {% if a.status == "in_progress" %}
        <p>{% trans "Pick up where you left off" %}</p>
        {% endif %}
        {% if a.due_date %}
        <p><small>{% trans "Due:" %} {{ a.due_date|portal_date }}</small></p>
        {% endif %}
    </article>
</a>
{% endfor %}
{% endif %}

{% if completed %}
<h2>{% trans "Completed" %}</h2>
{% for a in completed %}
<a href="{% url 'portal:question_review' a.pk %}" class="portal-card">
    <article>
        <h3>{{ a.survey.name }}</h3>
        <p><small>{% trans "Completed" %} {{ a.completed_at|portal_date }}</small></p>
    </article>
</a>
{% endfor %}
{% endif %}

{% endblock %}
```

#### `apps/portal/templates/portal/question_form.html`

```django-html
{% extends "portal/base_portal.html" %}
{% load i18n %}

{% block title %}{{ survey.name }}{% endblock %}

{% block content %}
<h1>{{ survey.name }}</h1>
{% if survey.description %}
<p>{{ survey.description }}</p>
{% endif %}

<form method="post" action="{% url 'portal:question_submit' assignment.pk %}">
    {% csrf_token %}

    {% for section in sections %}
    <fieldset>
        <legend>{{ section.title }}</legend>
        {% if section.instructions %}
        <p><small>{{ section.instructions }}</small></p>
        {% endif %}

        {% for question in section.questions.all %}
        <div class="form-group"
             hx-post="{% url 'portal:question_autosave' assignment.pk %}"
             hx-trigger="blur from:find input, blur from:find textarea, change from:find select"
             hx-vals='{"question_id": "{{ question.pk }}"}'
             hx-swap="none">

            <label for="q_{{ question.pk }}">
                {{ question.question_text }}
                {% if question.required %}<abbr title="{% trans 'required' %}">*</abbr>{% endif %}
            </label>

            {% if question.question_type == "short_text" %}
            <input type="text" id="q_{{ question.pk }}" name="value"
                   value="{{ partial_answers|get_value:question.pk }}"
                   {% if question.required %}required{% endif %}>

            {% elif question.question_type == "long_text" %}
            <textarea id="q_{{ question.pk }}" name="value" rows="3"
                      {% if question.required %}required{% endif %}>{{ partial_answers|get_value:question.pk }}</textarea>

            {% elif question.question_type == "rating_scale" %}
            <input type="number" id="q_{{ question.pk }}" name="value"
                   min="{{ question.min_value }}" max="{{ question.max_value }}"
                   value="{{ partial_answers|get_value:question.pk }}"
                   {% if question.required %}required{% endif %}>

            {% elif question.question_type == "yes_no" %}
            <label><input type="radio" name="value" value="1"> {% trans "Yes" %}</label>
            <label><input type="radio" name="value" value="0"> {% trans "No" %}</label>

            {% elif question.question_type == "single_choice" %}
            {% for opt in question.options_json %}
            <label><input type="radio" name="value" value="{{ opt.value }}"> {{ opt.label }}</label>
            {% endfor %}

            {% elif question.question_type == "multiple_choice" %}
            {% for opt in question.options_json %}
            <label><input type="checkbox" name="value" value="{{ opt.value }}"> {{ opt.label }}</label>
            {% endfor %}
            {% endif %}
        </div>
        {% endfor %}
    </fieldset>
    {% endfor %}

    <button type="submit">{% trans "Submit" %}</button>
</form>
{% endblock %}
```

#### `apps/portal/templates/portal/question_confirm.html`

```django-html
{% extends "portal/base_portal.html" %}
{% load i18n %}

{% block title %}{% trans "Thanks!" %}{% endblock %}

{% block content %}
<h1>{% trans "Thanks! Your answers have been saved." %}</h1>

{% if show_scores %}
{# Section scores would be calculated and passed from the view #}
{% endif %}

<a href="{% url 'portal:dashboard' %}" role="button">{% trans "Back to dashboard" %}</a>
{% endblock %}
```

#### `apps/portal/templates/portal/question_review.html`

```django-html
{% extends "portal/base_portal.html" %}
{% load i18n portal_tags %}

{% block title %}{{ survey.name }}{% endblock %}

{% block content %}
<h1>{{ survey.name }}</h1>
<p><small>{% trans "Submitted on" %} {{ assignment.completed_at|portal_date }}</small></p>

{% for answer in response.answers.all %}
<div class="review-answer">
    <p><strong>{{ answer.question.question_text }}</strong></p>
    <p>→ {{ answer.value }}</p>
</div>
{% endfor %}

<a href="{% url 'portal:questions' %}" role="button" class="outline">{% trans "Back to questions" %}</a>
{% endblock %}
```

### B4. Add the dashboard card

**File:** `apps/portal/templates/portal/dashboard.html`

Add a "Questions for You" nav card alongside the existing cards. Place it inside the `.portal-nav-cards` div, guarded by `features.surveys`:

```django-html
{% if features.surveys %}
<a href="{% url 'portal:questions' %}" class="portal-card">
    <article>
        <svg aria-hidden="true" width="28" height="28" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 11l3 3L22 4"/>
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
        </svg>
        <h2>{% trans "Questions for You" %}</h2>
        <p>{% blocktrans with worker_term=term.worker %}Forms and check-ins from your {{ worker_term }}.{% endblocktrans %}</p>
        {% if pending_survey_count %}
        <span class="badge" aria-label="{% blocktrans count count=pending_survey_count %}{{ count }} new{% plural %}{{ count }} new{% endblocktrans %}">{{ pending_survey_count }}</span>
        {% endif %}
    </article>
</a>
{% endif %}
```

### B5. Update the dashboard view to include survey count

**File:** `apps/portal/views.py` — in the `dashboard` view

Add pending survey count to the template context:

```python
# Inside dashboard(), before the render() call:
pending_survey_count = 0
if is_surveys_enabled():
    from apps.surveys.models import SurveyAssignment
    # Evaluate trigger rules on dashboard load
    evaluate_survey_rules(client_file, participant)
    pending_survey_count = SurveyAssignment.objects.filter(
        participant_user=participant,
        status__in=["pending", "in_progress"],
    ).count()
```

Add `"pending_survey_count": pending_survey_count` to the context dict passed to `render()`.

### B6. Handle the "single pending form" shortcut

As described in the design doc: if there's only one pending survey, the dashboard card should link directly to the form instead of the list.

**In the dashboard view**, if `pending_survey_count == 1`, also pass the assignment ID:

```python
if pending_survey_count == 1:
    single_assignment = SurveyAssignment.objects.filter(
        participant_user=participant,
        status__in=["pending", "in_progress"],
    ).first()
    context["single_survey_assignment_id"] = single_assignment.pk if single_assignment else None
```

**In the dashboard template**, adjust the card link:

```django-html
{% if single_survey_assignment_id %}
<a href="{% url 'portal:question_form' single_survey_assignment_id %}" class="portal-card">
{% else %}
<a href="{% url 'portal:questions' %}" class="portal-card">
{% endif %}
```

---

## Implementation Checklist

### Part A (Staff / Quick Notes)

| # | Task | Files to change |
|---|---|---|
| A1 | Add survey manage URLs | `apps/surveys/manage_urls.py`, `konote/urls.py` |
| A2 | Add participant-level survey URLs | `apps/surveys/urls.py`, `konote/urls.py` |
| A3 | Create survey forms | `apps/surveys/forms.py` |
| A4 | Build staff-side views | `apps/surveys/views.py` |
| A5 | Create staff-side templates | `templates/surveys/client_surveys.html`, `templates/surveys/staff_data_entry.html`, `templates/surveys/assign_survey.html` |
| A6 | Link surveys into quick note flow | `apps/notes/views.py`, `templates/notes/quick_note_form.html` |
| A7 | Add surveys section to client detail | Client detail template |
| A8 | Wire up feature toggle in templates | `konote/context_processors.py` (if needed) |
| A9 | Add trigger evaluation to staff views | `apps/clients/views.py` |
| A10 | Write tests | `tests/test_surveys.py` |

### Part B (Participant Portal)

| # | Task | Files to change |
|---|---|---|
| B1 | Add portal survey URLs | `apps/portal/urls.py` |
| B2 | Build portal survey views | `apps/portal/views.py` |
| B3 | Create portal templates | `apps/portal/templates/portal/questions_list.html`, `question_form.html`, `question_confirm.html`, `question_review.html` |
| B4 | Add dashboard card | `apps/portal/templates/portal/dashboard.html` |
| B5 | Update dashboard view for survey count + trigger evaluation | `apps/portal/views.py` |
| B6 | Single-form shortcut on dashboard | `apps/portal/views.py`, dashboard template |
| B7 | Auto-save with HTMX | Portal form template + `question_autosave` view |
| B8 | Multi-page form support (if page breaks) | `question_form_page` view + partial template |
| B9 | Conditional section evaluation | JavaScript + view logic |
| B10 | Write tests | `tests/test_portal_surveys.py` |

---

## Build Order

1. **A1–A3** — URLs and forms (no UI yet, but wires up routing)
2. **A4–A5** — Staff views and templates (staff can see/manage surveys)
3. **A6** — Quick note integration (link from notes to surveys)
4. **A7–A9** — Client detail integration + trigger evaluation on page load
5. **B1–B3** — Portal URLs, views, and templates
6. **B4–B6** — Dashboard card and smart linking
7. **B7–B9** — Auto-save, multi-page, conditionals (progressive enhancement)
8. **A10, B10** — Tests

---

## Key Design Decisions

1. **Surveys and notes stay separate.** A survey response is not a progress note. They appear in different sections of the participant file. Staff can navigate between them easily.

2. **Staff data entry uses the same survey form.** When staff fill in a survey on behalf of a participant, they see the same questions. The response is marked `channel="staff_entered"`.

3. **Portal auto-save uses `PartialAnswer`.** Answers are encrypted and stored per-question as the participant fills in the form. On submit, they move to `SurveyAnswer`. If the participant closes the browser, they resume where they left off.

4. **Trigger evaluation happens on page load.** Both the portal dashboard and the staff client detail page call `evaluate_survey_rules()`. This catches time-based and characteristic-based rules without needing a cron job.

5. **Feature toggle controls everything.** All survey UI is wrapped in `{% if features.surveys %}` or guarded by `is_surveys_enabled()` in views.
