# Surveys Future Work Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the four remaining survey features: shareable public links, trigger rule management UI, portal auto-save with partial answers, and French translations.

**Architecture:** Each feature is independent — they can be built in any order. The recommended build order is: (1) auto-save first (enhances existing portal flow), (2) shareable links (new public channel), (3) trigger rule management UI (staff admin), (4) translations last (captures all new strings). All features follow existing Django MVT patterns with Pico CSS, HTMX where appropriate, and TDD.

**Tech Stack:** Django 5.1, PostgreSQL, HTMX 2.0.4, Pico CSS, Fernet encryption, `polib` for translations

---

## Feature A: Portal Auto-Save / Partial Answers (SURVEY-AUTOSAVE1)

**What it does:** When a participant fills in a survey through the portal, answers are auto-saved on field blur via HTMX. If the participant closes the browser and returns later, their in-progress answers are restored. On final submit, partial answers are moved to `SurveyAnswer` rows and cleaned up.

**Key context:**
- `PartialAnswer` model already exists (`apps/surveys/models.py:358-381`) with unique constraint on `(assignment, question)`
- `portal_survey_fill` view exists (`apps/portal/views.py:1319-1423`) but does NOT load or save partial answers
- HTMX 2.0.4 is loaded in `base_portal.html` but zero HTMX patterns exist yet in the portal
- CSRF token is already in a `<meta>` tag for HTMX use
- Encryption: `konote.encryption.encrypt_field` / `decrypt_field` used for answer values

---

### Task A1: Write failing test for auto-save endpoint

**Files:**
- Modify: `tests/test_surveys.py`

**Step 1: Write the failing test**

Add a new test class at the end of `tests/test_surveys.py`:

```python
@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-autosave",
)
class PortalAutoSaveTests(TestCase):
    """Test auto-save of partial answers in the portal."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        from django.core.cache import cache
        cache.delete("feature_toggles")
        FeatureToggle.objects.update_or_create(
            feature_key="surveys",
            defaults={"is_enabled": True},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )
        self.staff = User.objects.create_user(
            username="autosave_staff", password="testpass123",
            display_name="Autosave Staff",
        )
        self.survey = Survey.objects.create(
            name="Autosave Survey", status="active", created_by=self.staff,
        )
        self.section = SurveySection.objects.create(
            survey=self.survey, title="Section 1", sort_order=1,
        )
        self.q1 = SurveyQuestion.objects.create(
            section=self.section, question_text="Your name?",
            question_type="short_text", sort_order=1,
        )
        self.q2 = SurveyQuestion.objects.create(
            section=self.section, question_text="Rate us",
            question_type="rating_scale", sort_order=2,
            min_value=1, max_value=5,
        )
        self.client_file = ClientFile.objects.create(
            record_id="AUTO-001", status="active",
        )
        self.client_file.first_name = "Auto"
        self.client_file.last_name = "Save"
        self.client_file.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="autosave@example.com",
            client_file=self.client_file,
            display_name="Auto S",
            password="testpass123",
        )
        self.assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="in_progress",
        )

    def _portal_session(self):
        """Set up a portal session for the participant."""
        session = self.client.session
        session["_portal_participant_id"] = str(self.participant.pk)
        session.save()

    def test_autosave_creates_partial_answer(self):
        self._portal_session()
        resp = self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Alice"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PartialAnswer.objects.count(), 1)
        pa = PartialAnswer.objects.first()
        self.assertEqual(pa.question, self.q1)

    def test_autosave_updates_existing_partial(self):
        self._portal_session()
        self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Alice"},
            HTTP_HX_REQUEST="true",
        )
        self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Bob"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(PartialAnswer.objects.count(), 1)

    def test_autosave_requires_htmx(self):
        self._portal_session()
        resp = self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Alice"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_form_loads_partial_answers(self):
        """When opening a form with partial answers, values are pre-filled."""
        from konote.encryption import encrypt_field
        PartialAnswer.objects.create(
            assignment=self.assignment,
            question=self.q1,
            value_encrypted=encrypt_field("Alice"),
        )
        self._portal_session()
        resp = self.client.get(
            f"/my/surveys/{self.assignment.pk}/fill/",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Alice", resp.content.decode())

    def test_submit_cleans_up_partial_answers(self):
        """After submit, partial answers are deleted."""
        PartialAnswer.objects.create(
            assignment=self.assignment,
            question=self.q1,
            value_encrypted=b"dummy",
        )
        self._portal_session()
        self.client.post(
            f"/my/surveys/{self.assignment.pk}/fill/",
            {f"q_{self.q1.pk}": "Final Answer", f"q_{self.q2.pk}": "3"},
        )
        self.assertEqual(PartialAnswer.objects.count(), 0)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py::PortalAutoSaveTests -v`
Expected: FAIL — URL `/my/surveys/<id>/save/` not found (404 or NoReverseMatch)

**Step 3: Commit**

```bash
git add tests/test_surveys.py
git commit -m "test: add failing tests for portal survey auto-save (SURVEY-AUTOSAVE1)"
```

---

### Task A2: Add auto-save URL and view

**Files:**
- Modify: `apps/portal/urls.py:30` (add new path)
- Modify: `apps/portal/views.py` (add `portal_survey_autosave` view)

**Step 1: Add the URL**

In `apps/portal/urls.py`, after the existing survey URLs (line 30-32), add:

```python
    path("surveys/<int:assignment_id>/save/", views.portal_survey_autosave, name="survey_autosave"),
```

**Step 2: Add the view**

In `apps/portal/views.py`, after the `portal_survey_fill` function, add:

```python
@portal_login_required
@require_POST
def portal_survey_autosave(request, assignment_id):
    """Auto-save a single answer via HTMX on field blur."""
    from apps.surveys.engine import is_surveys_enabled
    from apps.surveys.models import PartialAnswer, SurveyAssignment, SurveyQuestion
    from konote.encryption import encrypt_field

    if not is_surveys_enabled():
        raise Http404

    # Only accept HTMX requests
    if not request.headers.get("HX-Request"):
        return HttpResponse(status=400)

    participant = request.participant_user
    assignment = get_object_or_404(
        SurveyAssignment,
        pk=assignment_id,
        participant_user=participant,
        status__in=("pending", "in_progress"),
    )

    question_id = request.POST.get("question_id")
    value = request.POST.get("value", "")

    question = get_object_or_404(
        SurveyQuestion,
        pk=question_id,
        section__survey=assignment.survey,
    )

    if value:
        PartialAnswer.objects.update_or_create(
            assignment=assignment,
            question=question,
            defaults={"value_encrypted": encrypt_field(value)},
        )
    else:
        # Clear partial if value is empty
        PartialAnswer.objects.filter(
            assignment=assignment, question=question,
        ).delete()

    # Mark as in_progress if still pending
    if assignment.status == "pending":
        assignment.status = "in_progress"
        assignment.started_at = timezone.now()
        assignment.save(update_fields=["status", "started_at"])

    return HttpResponse(status=200)
```

**Step 3: Run tests**

Run: `pytest tests/test_surveys.py::PortalAutoSaveTests::test_autosave_creates_partial_answer tests/test_surveys.py::PortalAutoSaveTests::test_autosave_updates_existing_partial tests/test_surveys.py::PortalAutoSaveTests::test_autosave_requires_htmx -v`
Expected: PASS for all three auto-save tests

**Step 4: Commit**

```bash
git add apps/portal/urls.py apps/portal/views.py
git commit -m "feat: add portal survey auto-save endpoint (SURVEY-AUTOSAVE1)"
```

---

### Task A3: Load partial answers into form and clean up on submit

**Files:**
- Modify: `apps/portal/views.py` — update `portal_survey_fill` view

**Step 1: Update `portal_survey_fill` to load partial answers**

In `apps/portal/views.py`, modify the `portal_survey_fill` function. The changes are:

1. After loading sections (line ~1343), load existing partial answers and build a dict:
```python
    from apps.surveys.models import PartialAnswer
    from konote.encryption import decrypt_field

    # Load existing partial answers for pre-fill
    partials = {}
    for pa in PartialAnswer.objects.filter(assignment=assignment):
        partials[pa.question_id] = decrypt_field(pa.value_encrypted)
```

2. In the POST handler, after creating `SurveyAnswer` rows and updating assignment status (around line 1402), add cleanup:
```python
            # Clean up partial answers after successful submit
            PartialAnswer.objects.filter(assignment=assignment).delete()
```

3. In the template context for both GET and error-POST renders, add `partials`:
```python
    return render(request, "portal/survey_fill.html", {
        ...
        "partials": partials,
    })
```

**Step 2: Run tests**

Run: `pytest tests/test_surveys.py::PortalAutoSaveTests::test_form_loads_partial_answers tests/test_surveys.py::PortalAutoSaveTests::test_submit_cleans_up_partial_answers -v`
Expected: PASS

**Step 3: Commit**

```bash
git add apps/portal/views.py
git commit -m "feat: load partial answers into form and clean up on submit (SURVEY-AUTOSAVE1)"
```

---

### Task A4: Update survey_fill template with HTMX auto-save and pre-fill

**Files:**
- Modify: `apps/portal/templates/portal/survey_fill.html`

**Step 1: Update template**

Replace the content of `survey_fill.html` with HTMX auto-save on blur. Key changes:

1. Add HTMX `hx-post` on every input field, triggered on `blur` (or `change` for radios/checkboxes):
   - Each input gets: `hx-post="{% url 'portal:survey_autosave' assignment_id=assignment.pk %}"` `hx-trigger="blur"` `hx-vals='{"question_id": "{{ question.pk }}"}'` `hx-swap="none"`
   - For radios/checkboxes: `hx-trigger="change"` instead of blur

2. Pre-fill values from `partials` dict:
   - Text inputs: `value="{{ partials|default_if_none:'' }}"`  — use a template lookup
   - Radios/checkboxes: add `checked` when partial value matches
   - Use a custom template tag or inline lookup

3. Add a visual save indicator:
   - `hx-indicator` pointing to a small "Saving..." text near each field

The detailed template will be provided. Pre-fill logic will use Django's template system — since `partials` is a dict keyed by question PK, we can look up values with a simple template filter.

**Step 2: Create a template filter for dict lookup**

Create `apps/portal/templatetags/portal_tags.py` (if it doesn't already exist, add to it):

```python
@register.filter
def dict_get(d, key):
    """Look up a key in a dict. Usage: {{ mydict|dict_get:item.pk }}"""
    if d is None:
        return ""
    return d.get(key, "")
```

**Step 3: Run full test suite**

Run: `pytest tests/test_surveys.py::PortalAutoSaveTests -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add apps/portal/templates/portal/survey_fill.html apps/portal/templatetags/
git commit -m "feat: add HTMX auto-save and partial answer pre-fill to survey form (SURVEY-AUTOSAVE1)"
```

---

## Feature B: Shareable Link Channel (SURVEY-LINK1)

**What it does:** Staff can generate a shareable URL for any active survey. Anyone with the link can fill it in — no login required. Responses are saved with `channel="link"` and a token. Optionally anonymous.

**Key context:**
- `SurveyResponse.token` field exists (`models.py:315`) — CharField(max_length=64)
- `SurveyResponse.channel` has `"link"` option
- `SurveyResponse.respondent_name_display` exists for optional name
- `Survey.expires_at` exists for link expiry
- `Survey.is_anonymous` controls whether responses link to a client file
- No model for the "link" itself — we'll add a `SurveyLink` model to track generated links with tokens

---

### Task B1: Write failing tests for shareable link model

**Files:**
- Modify: `tests/test_surveys.py`

**Step 1: Write the failing test**

```python
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SurveyLinkModelTests(TestCase):
    """Test SurveyLink model for shareable URLs."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="link_staff", password="testpass123",
            display_name="Link Staff",
        )
        self.survey = Survey.objects.create(
            name="Link Survey", status="active", created_by=self.staff,
        )
        SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )

    def test_create_link(self):
        from apps.surveys.models import SurveyLink
        link = SurveyLink.objects.create(
            survey=self.survey,
            created_by=self.staff,
        )
        self.assertTrue(len(link.token) >= 32)
        self.assertTrue(link.is_active)

    def test_link_token_unique(self):
        from apps.surveys.models import SurveyLink
        link1 = SurveyLink.objects.create(
            survey=self.survey, created_by=self.staff,
        )
        link2 = SurveyLink.objects.create(
            survey=self.survey, created_by=self.staff,
        )
        self.assertNotEqual(link1.token, link2.token)

    def test_link_with_expiry(self):
        from apps.surveys.models import SurveyLink
        link = SurveyLink.objects.create(
            survey=self.survey,
            created_by=self.staff,
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.assertFalse(link.is_expired)

    def test_expired_link(self):
        from apps.surveys.models import SurveyLink
        link = SurveyLink.objects.create(
            survey=self.survey,
            created_by=self.staff,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertTrue(link.is_expired)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py::SurveyLinkModelTests -v`
Expected: FAIL — `SurveyLink` model does not exist

**Step 3: Commit**

```bash
git add tests/test_surveys.py
git commit -m "test: add failing tests for SurveyLink model (SURVEY-LINK1)"
```

---

### Task B2: Create SurveyLink model and migration

**Files:**
- Modify: `apps/surveys/models.py` (add SurveyLink class)
- Create: `apps/surveys/migrations/0004_surveylink.py` (auto-generated)

**Step 1: Add the model**

In `apps/surveys/models.py`, before the `PartialAnswer` class, add:

```python
import secrets

class SurveyLink(models.Model):
    """A shareable link token for a survey. No login required to respond."""

    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="links",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    collect_name = models.BooleanField(
        default=False,
        help_text=_("If true, ask respondent for their name (optional, not encrypted)."),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="survey_links_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "surveys"
        db_table = "survey_links"

    def __str__(self):
        return f"Link for {self.survey.name} ({self.token[:8]}...)"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False
```

**Step 2: Generate migration**

Run: `python manage.py makemigrations surveys -n surveylink`

**Step 3: Run migration**

Run: `python manage.py migrate`

**Step 4: Run tests**

Run: `pytest tests/test_surveys.py::SurveyLinkModelTests -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add apps/surveys/models.py apps/surveys/migrations/
git commit -m "feat: add SurveyLink model for shareable survey URLs (SURVEY-LINK1)"
```

---

### Task B3: Write failing tests for public survey form view

**Files:**
- Modify: `tests/test_surveys.py`

**Step 1: Write the failing tests**

```python
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PublicSurveyViewTests(TestCase):
    """Test public survey form accessible via shareable link."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="pub_staff", password="testpass123",
            display_name="Public Staff",
        )
        self.survey = Survey.objects.create(
            name="Public Survey", status="active", created_by=self.staff,
        )
        self.section = SurveySection.objects.create(
            survey=self.survey, title="Feedback", sort_order=1,
        )
        self.q1 = SurveyQuestion.objects.create(
            section=self.section, question_text="How was your experience?",
            question_type="short_text", sort_order=1, required=True,
        )
        from apps.surveys.models import SurveyLink
        self.link = SurveyLink.objects.create(
            survey=self.survey, created_by=self.staff,
        )

    def test_public_form_renders(self):
        resp = self.client.get(f"/s/{self.link.token}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Public Survey")

    def test_public_form_submit_creates_response(self):
        resp = self.client.post(
            f"/s/{self.link.token}/",
            {f"q_{self.q1.pk}": "Great!"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(SurveyResponse.objects.filter(channel="link").count(), 1)

    def test_expired_link_returns_gone(self):
        from apps.surveys.models import SurveyLink
        expired = SurveyLink.objects.create(
            survey=self.survey, created_by=self.staff,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        resp = self.client.get(f"/s/{expired.token}/")
        self.assertEqual(resp.status_code, 410)

    def test_inactive_link_returns_gone(self):
        self.link.is_active = False
        self.link.save()
        resp = self.client.get(f"/s/{self.link.token}/")
        self.assertEqual(resp.status_code, 410)

    def test_invalid_token_returns_404(self):
        resp = self.client.get("/s/nonexistent-token/")
        self.assertEqual(resp.status_code, 404)

    def test_closed_survey_returns_gone(self):
        self.survey.status = "closed"
        self.survey.save()
        resp = self.client.get(f"/s/{self.link.token}/")
        self.assertEqual(resp.status_code, 410)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py::PublicSurveyViewTests -v`
Expected: FAIL — URL `/s/<token>/` not found

**Step 3: Commit**

```bash
git add tests/test_surveys.py
git commit -m "test: add failing tests for public survey link view (SURVEY-LINK1)"
```

---

### Task B4: Add public survey views and URLs

**Files:**
- Create: `apps/surveys/public_views.py` (new file — keeps public views separate from staff views)
- Modify: root URL config to add `/s/<token>/` route
- Create: `templates/surveys/public_form.html`
- Create: `templates/surveys/public_thank_you.html`
- Create: `templates/surveys/public_expired.html`

**Step 1: Find the root URL config**

The root urlconf should be in `konote/urls.py`. The `/s/` prefix keeps URLs short for sharing.

**Step 2: Create public views**

In `apps/surveys/public_views.py`:

```python
"""Public survey views — no login required.

These views handle the shareable link channel. Anyone with a valid
link token can view and submit a survey response.
"""
from django.db import transaction
from django.http import HttpResponseGone
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import (
    SurveyAnswer,
    SurveyLink,
    SurveyResponse,
)


def public_survey_form(request, token):
    """Display and process a public survey form via shareable link."""
    link = get_object_or_404(SurveyLink, token=token)

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
            return render(request, "surveys/public_form.html", {
                "survey": survey,
                "sections": sections,
                "link": link,
                "posted": request.POST,
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

        return redirect("surveys:public_thank_you", token=link.token)

    return render(request, "surveys/public_form.html", {
        "survey": survey,
        "sections": sections,
        "link": link,
        "posted": {},
        "errors": [],
    })


def public_survey_thank_you(request, token):
    """Thank-you page after public survey submission."""
    link = get_object_or_404(SurveyLink, token=token)
    return render(request, "surveys/public_thank_you.html", {
        "survey": link.survey,
    })
```

**Step 3: Add URL routes**

In the root `konote/urls.py`, add:

```python
from apps.surveys.public_views import public_survey_form, public_survey_thank_you

urlpatterns = [
    ...
    path("s/<str:token>/", public_survey_form, name="public_survey_form"),
    path("s/<str:token>/thanks/", public_survey_thank_you, name="public_survey_thank_you"),
    ...
]
```

Also update the survey `urls.py` or use the root urlconf directly — the exact placement depends on the root URL structure. The name `surveys:public_thank_you` may need to be in the surveys namespace or at root level.

**Step 4: Create templates**

Create `templates/surveys/public_form.html` — similar to `portal/survey_fill.html` but:
- Extends a minimal base template (not `base_portal.html`)
- No login required
- Optional name field when `link.collect_name` is True
- Same question type rendering as staff_data_entry.html

Create `templates/surveys/public_thank_you.html` — simple thank you page.

Create `templates/surveys/public_expired.html` — message that the survey link is no longer available.

**Step 5: Run tests**

Run: `pytest tests/test_surveys.py::PublicSurveyViewTests -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add apps/surveys/public_views.py konote/urls.py templates/surveys/public_form.html templates/surveys/public_thank_you.html templates/surveys/public_expired.html
git commit -m "feat: add public survey form views and templates (SURVEY-LINK1)"
```

---

### Task B5: Write failing tests for staff link generation UI

**Files:**
- Modify: `tests/test_surveys.py`

**Step 1: Write the failing tests**

```python
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class StaffLinkGenerationTests(TestCase):
    """Test staff UI for generating shareable survey links."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="linkgen_staff", password="testpass123",
            display_name="LinkGen Staff", role="admin",
        )
        self.client.login(username="linkgen_staff", password="testpass123")
        from django.core.cache import cache
        cache.delete("feature_toggles")
        FeatureToggle.objects.update_or_create(
            feature_key="surveys",
            defaults={"is_enabled": True},
        )
        self.survey = Survey.objects.create(
            name="LinkGen Survey", status="active", created_by=self.staff,
        )
        SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )

    def test_generate_link_page_renders(self):
        resp = self.client.get(
            f"/manage/surveys/{self.survey.pk}/links/",
        )
        self.assertEqual(resp.status_code, 200)

    def test_create_link(self):
        from apps.surveys.models import SurveyLink
        resp = self.client.post(
            f"/manage/surveys/{self.survey.pk}/links/",
            {"action": "create"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(SurveyLink.objects.filter(survey=self.survey).count(), 1)

    def test_deactivate_link(self):
        from apps.surveys.models import SurveyLink
        link = SurveyLink.objects.create(
            survey=self.survey, created_by=self.staff,
        )
        resp = self.client.post(
            f"/manage/surveys/{self.survey.pk}/links/",
            {"action": "deactivate", "link_id": link.pk},
        )
        link.refresh_from_db()
        self.assertFalse(link.is_active)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py::StaffLinkGenerationTests -v`
Expected: FAIL — URL not found

**Step 3: Commit**

```bash
git add tests/test_surveys.py
git commit -m "test: add failing tests for staff link generation (SURVEY-LINK1)"
```

---

### Task B6: Add staff link management view and template

**Files:**
- Modify: `apps/surveys/views.py` (add `survey_links` view)
- Modify: `apps/surveys/manage_urls.py` (add URL)
- Create: `templates/surveys/admin/survey_links.html`
- Modify: `templates/surveys/admin/survey_detail.html` (add "Shareable Links" section)

**Step 1: Add the view**

In `apps/surveys/views.py`, add:

```python
@login_required
@requires_permission("template.note.manage", allow_admin=True)
def survey_links(request, survey_id):
    """Manage shareable links for a survey."""
    _surveys_or_404()
    survey = get_object_or_404(Survey, pk=survey_id)

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "create":
            from .models import SurveyLink
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
            from .models import SurveyLink
            link = get_object_or_404(SurveyLink, pk=link_id, survey=survey)
            link.is_active = False
            link.save(update_fields=["is_active"])
            messages.success(request, _("Link deactivated."))
        return redirect("survey_manage:survey_links", survey_id=survey.pk)

    from .models import SurveyLink
    links = SurveyLink.objects.filter(survey=survey).order_by("-created_at")
    return render(request, "surveys/admin/survey_links.html", {
        "survey": survey,
        "links": links,
    })
```

**Step 2: Add URL**

In `apps/surveys/manage_urls.py`, add:

```python
    path("<int:survey_id>/links/", views.survey_links, name="survey_links"),
```

**Step 3: Create template**

Create `templates/surveys/admin/survey_links.html` showing:
- Table of existing links with token (truncated), status, expiry, response count
- Full shareable URL (using `request.get_host()` + `/s/<token>/`)
- Copy-to-clipboard button (vanilla JS)
- "Create New Link" form with optional expiry and collect_name checkbox
- "Deactivate" button for each active link

**Step 4: Update survey detail page**

In `templates/surveys/admin/survey_detail.html`, add a link to the links management page.

**Step 5: Run tests**

Run: `pytest tests/test_surveys.py::StaffLinkGenerationTests -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add apps/surveys/views.py apps/surveys/manage_urls.py templates/surveys/admin/survey_links.html templates/surveys/admin/survey_detail.html
git commit -m "feat: add staff UI for managing shareable survey links (SURVEY-LINK1)"
```

---

### Task B7: Register SurveyLink in Django admin

**Files:**
- Modify: `apps/surveys/admin.py`

**Step 1: Add admin registration**

In `apps/surveys/admin.py`, add import and registration:

```python
from .models import SurveyLink

@admin.register(SurveyLink)
class SurveyLinkAdmin(admin.ModelAdmin):
    list_display = ("survey", "token", "is_active", "expires_at", "created_at")
    list_filter = ("is_active",)
    readonly_fields = ("token",)
```

**Step 2: Run tests**

Run: `pytest tests/test_surveys.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add apps/surveys/admin.py
git commit -m "feat: register SurveyLink in Django admin (SURVEY-LINK1)"
```

---

## Feature C: Trigger Rule Management UI (SURVEY-RULES1)

**What it does:** Staff and PMs can create, view, edit, and deactivate trigger rules from the survey management interface instead of needing Django admin access.

**Key context:**
- `SurveyTriggerRule` model is fully built (`models.py:146-226`)
- Currently only manageable via Django admin (`admin.py:48-51`)
- Rules are displayed (read-only) on the survey detail page (`views.py:130`)
- Need: a form to create/edit rules, a view to list/manage them, template

---

### Task C1: Write failing tests for trigger rule management views

**Files:**
- Modify: `tests/test_surveys.py`

**Step 1: Write the failing tests**

```python
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class TriggerRuleManagementTests(TestCase):
    """Test staff UI for managing trigger rules."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="ruleui_staff", password="testpass123",
            display_name="RuleUI Staff", role="admin",
        )
        self.client.login(username="ruleui_staff", password="testpass123")
        from django.core.cache import cache
        cache.delete("feature_toggles")
        FeatureToggle.objects.update_or_create(
            feature_key="surveys",
            defaults={"is_enabled": True},
        )
        self.program = Program.objects.create(name="RuleUI Program")
        self.event_type = EventType.objects.create(name="RuleUI Event")
        self.survey = Survey.objects.create(
            name="RuleUI Survey", status="active", created_by=self.staff,
        )
        SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )

    def test_rule_list_page_renders(self):
        resp = self.client.get(
            f"/manage/surveys/{self.survey.pk}/rules/",
        )
        self.assertEqual(resp.status_code, 200)

    def test_create_characteristic_rule(self):
        resp = self.client.post(
            f"/manage/surveys/{self.survey.pk}/rules/new/",
            {
                "trigger_type": "characteristic",
                "program": self.program.pk,
                "repeat_policy": "once_per_participant",
                "auto_assign": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            SurveyTriggerRule.objects.filter(survey=self.survey).count(), 1,
        )

    def test_create_event_rule(self):
        resp = self.client.post(
            f"/manage/surveys/{self.survey.pk}/rules/new/",
            {
                "trigger_type": "event",
                "event_type": self.event_type.pk,
                "repeat_policy": "once_per_participant",
                "auto_assign": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        rule = SurveyTriggerRule.objects.get(survey=self.survey)
        self.assertEqual(rule.event_type, self.event_type)

    def test_create_time_rule(self):
        resp = self.client.post(
            f"/manage/surveys/{self.survey.pk}/rules/new/",
            {
                "trigger_type": "time",
                "program": self.program.pk,
                "recurrence_days": 30,
                "anchor": "enrolment_date",
                "repeat_policy": "recurring",
                "auto_assign": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        rule = SurveyTriggerRule.objects.get(survey=self.survey)
        self.assertEqual(rule.recurrence_days, 30)

    def test_deactivate_rule(self):
        rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        resp = self.client.post(
            f"/manage/surveys/{self.survey.pk}/rules/{rule.pk}/deactivate/",
        )
        rule.refresh_from_db()
        self.assertFalse(rule.is_active)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py::TriggerRuleManagementTests -v`
Expected: FAIL — URLs not found

**Step 3: Commit**

```bash
git add tests/test_surveys.py
git commit -m "test: add failing tests for trigger rule management UI (SURVEY-RULES1)"
```

---

### Task C2: Create TriggerRuleForm

**Files:**
- Modify: `apps/surveys/forms.py`

**Step 1: Add the form**

In `apps/surveys/forms.py`, add:

```python
from .models import SurveyTriggerRule

class TriggerRuleForm(forms.ModelForm):
    """Form for creating/editing a survey trigger rule."""

    class Meta:
        model = SurveyTriggerRule
        fields = [
            "trigger_type", "event_type", "program",
            "recurrence_days", "anchor", "repeat_policy",
            "auto_assign", "include_existing", "due_days",
        ]
        labels = {
            "trigger_type": _("When should this survey be assigned?"),
            "event_type": _("Event type"),
            "program": _("Program"),
            "recurrence_days": _("Repeat every N days"),
            "anchor": _("Count days from"),
            "repeat_policy": _("How often per participant?"),
            "auto_assign": _("Assign automatically"),
            "include_existing": _("Also assign to existing participants"),
            "due_days": _("Due date (days after assignment)"),
        }
        help_texts = {
            "auto_assign": _(
                "If unchecked, staff must approve each assignment before "
                "the participant sees it."
            ),
            "include_existing": _(
                "When first activated, also assign to participants who "
                "already match the criteria."
            ),
            "due_days": _("Leave blank for no due date."),
        }
        widgets = {
            "recurrence_days": forms.NumberInput(attrs={"min": 1}),
            "due_days": forms.NumberInput(attrs={"min": 1}),
        }
```

**Step 2: Commit**

```bash
git add apps/surveys/forms.py
git commit -m "feat: add TriggerRuleForm for staff UI (SURVEY-RULES1)"
```

---

### Task C3: Add trigger rule management views and URLs

**Files:**
- Modify: `apps/surveys/views.py` (add `survey_rules_list`, `survey_rule_create`, `survey_rule_deactivate`)
- Modify: `apps/surveys/manage_urls.py` (add URLs)
- Create: `templates/surveys/admin/rule_list.html`
- Create: `templates/surveys/admin/rule_form.html`

**Step 1: Add views**

In `apps/surveys/views.py`, add:

```python
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
        from .forms import TriggerRuleForm
        form = TriggerRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.survey = survey
            rule.created_by = request.user
            rule.save()
            messages.success(request, _("Trigger rule created."))
            return redirect("survey_manage:survey_rules", survey_id=survey.pk)
    else:
        from .forms import TriggerRuleForm
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
    from .models import SurveyTriggerRule
    rule = get_object_or_404(SurveyTriggerRule, pk=rule_id, survey=survey)
    rule.is_active = False
    rule.save(update_fields=["is_active"])
    messages.success(request, _("Trigger rule deactivated."))
    return redirect("survey_manage:survey_rules", survey_id=survey.pk)
```

**Step 2: Add URLs**

In `apps/surveys/manage_urls.py`, add:

```python
    path("<int:survey_id>/rules/", views.survey_rules_list, name="survey_rules"),
    path("<int:survey_id>/rules/new/", views.survey_rule_create, name="survey_rule_create"),
    path("<int:survey_id>/rules/<int:rule_id>/deactivate/", views.survey_rule_deactivate, name="survey_rule_deactivate"),
```

**Step 3: Create templates**

`templates/surveys/admin/rule_list.html`:
- Table showing each rule: trigger type (human-readable), program/event type, repeat policy, auto-assign, active status, created date
- "New Rule" button linking to create form
- "Deactivate" button for each active rule
- Breadcrumbs: Surveys > Survey Name > Trigger Rules

`templates/surveys/admin/rule_form.html`:
- The TriggerRuleForm rendered as a standard Django form
- Help text explaining each trigger type
- Conditional field visibility via vanilla JS (show event_type only for event triggers, show program for enrolment/time/characteristic, show recurrence_days and anchor for time triggers)
- Breadcrumbs: Surveys > Survey Name > Trigger Rules > New Rule

**Step 4: Run tests**

Run: `pytest tests/test_surveys.py::TriggerRuleManagementTests -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add apps/surveys/views.py apps/surveys/manage_urls.py templates/surveys/admin/rule_list.html templates/surveys/admin/rule_form.html
git commit -m "feat: add trigger rule management views and templates (SURVEY-RULES1)"
```

---

### Task C4: Link trigger rules from survey detail page

**Files:**
- Modify: `templates/surveys/admin/survey_detail.html`

**Step 1: Add link**

In the survey detail template, update the trigger rules section to:
- Show a "Manage Rules" button linking to `survey_manage:survey_rules`
- Keep the existing read-only rule list but add action links

**Step 2: Run full test suite**

Run: `pytest tests/test_surveys.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add templates/surveys/admin/survey_detail.html
git commit -m "feat: link trigger rule management from survey detail page (SURVEY-RULES1)"
```

---

## Feature D: French Translations (SURVEY-I18N1)

**What it does:** Extract all translatable strings from survey templates and Python code, then add French translations to the `.po` file and compile.

**Key context:**
- Management command: `python manage.py translate_strings` (custom, uses `polib`)
- Locale file: `locale/fr/LC_MESSAGES/django.po`
- All survey templates already use `{% trans %}` and `{% blocktrans %}`
- Python views/forms use `gettext` and `gettext_lazy` via `_()` and `_()`
- New templates from Features A, B, C will introduce new strings

**Important:** This task should be done LAST, after A, B, and C are complete, so all new strings are captured.

---

### Task D1: Extract new translatable strings

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po`
- Modify: `locale/fr/LC_MESSAGES/django.mo`

**Step 1: Run the extraction command**

Run: `python manage.py translate_strings --dry-run`

Review the output to see which new strings were found. These will include strings from:
- `apps/surveys/public_views.py`
- `apps/surveys/forms.py` (TriggerRuleForm labels and help texts)
- `apps/surveys/views.py` (new success messages)
- `templates/surveys/public_form.html`
- `templates/surveys/public_thank_you.html`
- `templates/surveys/public_expired.html`
- `templates/surveys/admin/survey_links.html`
- `templates/surveys/admin/rule_list.html`
- `templates/surveys/admin/rule_form.html`
- Updated `templates/portal/survey_fill.html`

**Step 2: Run extraction for real**

Run: `python manage.py translate_strings`

**Step 3: Commit extraction**

```bash
git add locale/
git commit -m "chore: extract new survey translatable strings (SURVEY-I18N1)"
```

---

### Task D2: Add French translations for all new survey strings

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po`

**Step 1: Identify untranslated survey strings**

Search the `.po` file for empty `msgstr ""` entries near survey-related `msgid` values. Focus on strings added by features A, B, and C.

**Step 2: Add French translations**

Fill in each `msgstr` with the correct French translation. Key translations:

| English | French |
|---------|--------|
| Shareable link | Lien partageable |
| Generate Link | Générer un lien |
| Copy Link | Copier le lien |
| Link copied! | Lien copié! |
| This survey is no longer available. | Ce sondage n'est plus disponible. |
| Deactivate | Désactiver |
| Trigger Rules | Règles de déclenchement |
| When should this survey be assigned? | Quand ce sondage doit-il être attribué? |
| Event type | Type d'événement |
| Repeat every N days | Répéter tous les N jours |
| Count days from | Compter les jours depuis |
| How often per participant? | À quelle fréquence par participant? |
| Assign automatically | Attribuer automatiquement |
| Also assign to existing participants | Attribuer également aux participants existants |
| Due date (days after assignment) | Date d'échéance (jours après l'attribution) |
| Trigger rule created. | Règle de déclenchement créée. |
| Trigger rule deactivated. | Règle de déclenchement désactivée. |
| Saving... | Enregistrement... |
| Saved | Enregistré |
| Your answers are being saved automatically. | Vos réponses sont enregistrées automatiquement. |

**Step 3: Commit translations**

```bash
git add locale/fr/LC_MESSAGES/django.po
git commit -m "feat: add French translations for survey strings (SURVEY-I18N1)"
```

---

### Task D3: Compile translations and verify

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.mo`

**Step 1: Compile**

Run: `python manage.py translate_strings`

This both re-extracts (idempotent) and compiles the `.mo` file.

**Step 2: Verify no untranslated survey strings remain**

Run: `python scripts/validate_translations.py`

Check output for any untranslated survey-related strings.

**Step 3: Commit compiled translations**

```bash
git add locale/
git commit -m "chore: compile French translations (SURVEY-I18N1)"
```

---

## Dependency Graph

```
Feature A (Auto-Save)     Feature B (Links)     Feature C (Rules UI)
         \                     |                     /
          \                    |                    /
           \                   |                   /
            --------  Feature D (Translations)  --------
```

Features A, B, and C are independent — can be built in parallel or any order.
Feature D must come last (captures all new strings from A, B, C).

## Summary

| Feature | Tasks | New Files | Modified Files |
|---------|-------|-----------|----------------|
| A: Auto-Save | A1-A4 | 0 | 4 (views, urls, template, templatetags) |
| B: Shareable Links | B1-B7 | 5 (model, views, 3 templates) | 5 (models, urls, views, admin, detail template) |
| C: Rules UI | C1-C4 | 2 (templates) | 4 (forms, views, urls, detail template) |
| D: Translations | D1-D3 | 0 | 2 (django.po, django.mo) |
| **Total** | **14 tasks** | **7 new files** | **~10 modified files** |
