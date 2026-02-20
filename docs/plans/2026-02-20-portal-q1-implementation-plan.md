# PORTAL-Q1 "Questions for You" Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the "Questions for You" portal feature with HTMX auto-save, multi-page navigation, conditional sections, review page, and dashboard badge.

**Architecture:** Enhance existing portal survey views at `/my/surveys/`. Auto-save uses HTMX POST on blur/change with Fernet-encrypted PartialAnswer storage. Page navigation uses standard form POST + redirect for reliability. Conditional sections evaluated server-side on page load/navigation only.

**Tech Stack:** Django 5, HTMX 2.0.4, Pico CSS, Fernet encryption

**Worktree:** `.worktrees/feat-portal-q1-impl` on branch `feat/portal-q1-implementation`

---

## Task 1: Add `.value` Property to PartialAnswer

The PartialAnswer model has `value_encrypted` BinaryField but no property getter/setter for transparent encryption, unlike SurveyAnswer which has `.value`. Add it.

**Files:**
- Modify: `apps/surveys/models.py` (PartialAnswer class, ~line 358)
- Test: `tests/test_surveys.py` (AssignmentResponseModelTests class)

**Step 1: Write the failing test**

Add to `tests/test_surveys.py` inside `AssignmentResponseModelTests`:

```python
def test_partial_answer_value_property(self):
    """PartialAnswer.value encrypts on set, decrypts on get."""
    assignment = SurveyAssignment.objects.create(
        survey=self.survey,
        participant_user=self.participant,
        client_file=self.client_file,
        status="in_progress",
    )
    pa = PartialAnswer(assignment=assignment, question=self.question)
    pa.value = "test answer"
    pa.save()
    pa.refresh_from_db()
    self.assertEqual(pa.value, "test answer")
    # Encrypted field should not be plain text
    self.assertNotEqual(pa.value_encrypted, b"test answer")

def test_partial_answer_value_empty(self):
    """PartialAnswer.value handles empty string."""
    assignment = SurveyAssignment.objects.create(
        survey=self.survey,
        participant_user=self.participant,
        client_file=self.client_file,
        status="in_progress",
    )
    pa = PartialAnswer(assignment=assignment, question=self.question)
    pa.value = ""
    pa.save()
    pa.refresh_from_db()
    self.assertEqual(pa.value, "")
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_surveys.py::AssignmentResponseModelTests::test_partial_answer_value_property tests/test_surveys.py::AssignmentResponseModelTests::test_partial_answer_value_empty -v`
Expected: FAIL with `AttributeError: 'PartialAnswer' object has no attribute 'value'` (or similar)

**Step 3: Add .value property to PartialAnswer**

In `apps/surveys/models.py`, add to the PartialAnswer class (after `updated_at`, before `class Meta`):

```python
@property
def value(self):
    return decrypt_field(self.value_encrypted)

@value.setter
def value(self, val):
    self.value_encrypted = encrypt_field(val)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_surveys.py::AssignmentResponseModelTests -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add apps/surveys/models.py tests/test_surveys.py
git commit -m "feat: add .value property to PartialAnswer for Fernet encryption"
```

---

## Task 2: Page Grouping Utility

Create a helper function that groups survey sections into pages based on `page_break` flags, evaluates conditional section visibility, and handles page numbering.

**Files:**
- Create: `apps/portal/survey_helpers.py`
- Test: `tests/test_portal_surveys.py` (new file)

**Step 1: Write the failing tests**

Create `tests/test_portal_surveys.py`:

```python
"""Tests for portal survey helpers and views.

Run with:
    pytest tests/test_portal_surveys.py -v
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.auth_app.models import User
from apps.clients.models import ClientFile
from apps.portal.models import ParticipantUser
from apps.surveys.models import (
    Survey, SurveySection, SurveyQuestion,
    SurveyAssignment, PartialAnswer,
)
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PageGroupingTests(TestCase):
    """Test grouping sections into pages."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="pg_staff", password="testpass123",
            display_name="PG Staff",
        )

    def test_single_page_no_breaks(self):
        """Survey with no page_break sections = 1 page."""
        from apps.portal.survey_helpers import group_sections_into_pages

        survey = Survey.objects.create(name="No Breaks", created_by=self.staff)
        s1 = SurveySection.objects.create(
            survey=survey, title="S1", sort_order=1, page_break=False,
        )
        s2 = SurveySection.objects.create(
            survey=survey, title="S2", sort_order=2, page_break=False,
        )
        sections = list(survey.sections.filter(is_active=True).order_by("sort_order"))
        pages = group_sections_into_pages(sections)
        self.assertEqual(len(pages), 1)
        self.assertEqual(len(pages[0]), 2)

    def test_multi_page_with_breaks(self):
        """page_break=True starts a new page."""
        from apps.portal.survey_helpers import group_sections_into_pages

        survey = Survey.objects.create(name="Paged", created_by=self.staff)
        SurveySection.objects.create(
            survey=survey, title="Page 1A", sort_order=1, page_break=False,
        )
        SurveySection.objects.create(
            survey=survey, title="Page 1B", sort_order=2, page_break=False,
        )
        SurveySection.objects.create(
            survey=survey, title="Page 2", sort_order=3, page_break=True,
        )
        SurveySection.objects.create(
            survey=survey, title="Page 3", sort_order=4, page_break=True,
        )
        sections = list(survey.sections.filter(is_active=True).order_by("sort_order"))
        pages = group_sections_into_pages(sections)
        self.assertEqual(len(pages), 3)
        self.assertEqual(len(pages[0]), 2)  # Page 1A + 1B
        self.assertEqual(len(pages[1]), 1)  # Page 2
        self.assertEqual(len(pages[2]), 1)  # Page 3

    def test_conditional_section_hidden(self):
        """Conditional section hidden when condition not met."""
        from apps.portal.survey_helpers import filter_visible_sections

        survey = Survey.objects.create(
            name="Conditional", created_by=self.staff, status="active",
        )
        s1 = SurveySection.objects.create(
            survey=survey, title="Main", sort_order=1,
        )
        trigger_q = SurveyQuestion.objects.create(
            section=s1, question_text="Has children?",
            question_type="yes_no", sort_order=1, required=True,
        )
        SurveySection.objects.create(
            survey=survey, title="Childcare", sort_order=2,
            condition_question=trigger_q, condition_value="1",
        )
        sections = list(survey.sections.filter(is_active=True).order_by("sort_order"))
        # No partial answers — condition not met
        visible = filter_visible_sections(sections, partial_answers={})
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0].title, "Main")

    def test_conditional_section_visible(self):
        """Conditional section visible when condition is met."""
        from apps.portal.survey_helpers import filter_visible_sections

        survey = Survey.objects.create(
            name="Conditional2", created_by=self.staff, status="active",
        )
        s1 = SurveySection.objects.create(
            survey=survey, title="Main", sort_order=1,
        )
        trigger_q = SurveyQuestion.objects.create(
            section=s1, question_text="Has children?",
            question_type="yes_no", sort_order=1, required=True,
        )
        SurveySection.objects.create(
            survey=survey, title="Childcare", sort_order=2,
            condition_question=trigger_q, condition_value="1",
        )
        sections = list(survey.sections.filter(is_active=True).order_by("sort_order"))
        # Partial answer matches condition
        visible = filter_visible_sections(
            sections, partial_answers={trigger_q.pk: "1"},
        )
        self.assertEqual(len(visible), 2)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_portal_surveys.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'apps.portal.survey_helpers'`

**Step 3: Implement the helpers**

Create `apps/portal/survey_helpers.py`:

```python
"""Helpers for portal survey rendering: page grouping, conditional sections."""


def group_sections_into_pages(sections):
    """Group a list of SurveySection objects into pages.

    Sections are grouped sequentially. A section with page_break=True
    starts a new page. Returns a list of lists.
    """
    if not sections:
        return []
    pages = [[]]
    for section in sections:
        if section.page_break and pages[-1]:
            pages.append([])
        pages[-1].append(section)
    return pages


def filter_visible_sections(sections, partial_answers):
    """Filter sections based on conditional visibility.

    Args:
        sections: list of SurveySection objects (ordered by sort_order)
        partial_answers: dict of {question_pk: value_string} from PartialAnswer

    Returns:
        list of visible SurveySection objects
    """
    visible = []
    for section in sections:
        if section.condition_question_id is None:
            visible.append(section)
        else:
            answer = partial_answers.get(section.condition_question_id, "")
            if answer == section.condition_value:
                visible.append(section)
    return visible


def get_partial_answers_dict(assignment):
    """Load all PartialAnswer values for an assignment as {question_pk: value}."""
    from apps.surveys.models import PartialAnswer
    partials = PartialAnswer.objects.filter(assignment=assignment)
    return {pa.question_id: pa.value for pa in partials}


def calculate_section_scores(sections, answers_dict):
    """Calculate scores for scored sections.

    Args:
        sections: list of SurveySection objects
        answers_dict: dict of {question_pk: value_string}

    Returns:
        list of dicts: [{"title": str, "score": int, "max_score": int}, ...]
        Only includes sections with scoring_method != "none".
    """
    scores = []
    for section in sections:
        if section.scoring_method == "none" or not section.max_score:
            continue
        total = 0
        for question in section.questions.all().order_by("sort_order"):
            answer_val = answers_dict.get(question.pk, "")
            if not answer_val:
                continue
            if question.question_type in ("rating_scale", "yes_no"):
                try:
                    total += int(answer_val)
                except (ValueError, TypeError):
                    pass
            elif question.question_type == "single_choice":
                for opt in (question.options_json or []):
                    if opt.get("value") == answer_val and opt.get("score") is not None:
                        total += opt["score"]
                        break
        scores.append({
            "title": section.title,
            "score": total,
            "max_score": section.max_score,
        })
    return scores
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_portal_surveys.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add apps/portal/survey_helpers.py tests/test_portal_surveys.py
git commit -m "feat: add page grouping and conditional section helpers"
```

---

## Task 3: Auto-Save View

Add the HTMX endpoint that saves a single answer to PartialAnswer on blur/change.

**Files:**
- Modify: `apps/portal/views.py` (add `portal_survey_autosave`)
- Modify: `apps/portal/urls.py` (add save URL)
- Test: `tests/test_portal_surveys.py` (add view tests)

**Step 1: Write the failing tests**

Add to `tests/test_portal_surveys.py`:

```python
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-portal",
)
class AutoSaveViewTests(TestCase):
    """Test the HTMX auto-save endpoint."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="auto_staff", password="testpass123",
            display_name="Auto Staff",
        )
        self.survey = Survey.objects.create(
            name="Auto Survey", status="active", created_by=self.staff,
        )
        self.section = SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )
        self.q1 = SurveyQuestion.objects.create(
            section=self.section, question_text="Name?",
            question_type="short_text", sort_order=1,
        )
        self.q2 = SurveyQuestion.objects.create(
            section=self.section, question_text="How?",
            question_type="rating_scale", sort_order=2,
            options_json=[
                {"value": "1", "label": "Bad", "score": 1},
                {"value": "2", "label": "OK", "score": 2},
                {"value": "3", "label": "Good", "score": 3},
            ],
        )
        self.client_file = ClientFile.objects.create(
            record_id="AUTO-001", status="active",
        )
        self.client_file.first_name = "Auto"
        self.client_file.last_name = "Test"
        self.client_file.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="auto@example.com",
            client_file=self.client_file,
            display_name="Auto P",
            password="testpass123",
        )
        from apps.admin_settings.models import FeatureToggle
        FeatureToggle.objects.update_or_create(
            feature_name="surveys",
            defaults={"is_enabled": True},
        )
        self.assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="in_progress",
        )

    def _portal_login(self):
        """Set up portal session for the test client."""
        session = self.client.session
        session["portal_participant_id"] = self.participant.pk
        session.save()

    def test_autosave_creates_partial_answer(self):
        self._portal_login()
        response = self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Jane Doe"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        pa = PartialAnswer.objects.get(
            assignment=self.assignment, question=self.q1,
        )
        self.assertEqual(pa.value, "Jane Doe")

    def test_autosave_updates_existing(self):
        self._portal_login()
        # First save
        self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Jane"},
            HTTP_HX_REQUEST="true",
        )
        # Update
        self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Jane Doe"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(PartialAnswer.objects.filter(
            assignment=self.assignment, question=self.q1,
        ).count(), 1)
        pa = PartialAnswer.objects.get(
            assignment=self.assignment, question=self.q1,
        )
        self.assertEqual(pa.value, "Jane Doe")

    def test_autosave_rejects_non_htmx(self):
        self._portal_login()
        response = self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Jane"},
        )
        self.assertEqual(response.status_code, 400)

    def test_autosave_wrong_assignment(self):
        """Cannot save to someone else's assignment."""
        other_cf = ClientFile.objects.create(
            record_id="OTHER-001", status="active",
        )
        other_cf.first_name = "Other"
        other_cf.last_name = "Person"
        other_cf.save()
        other_p = ParticipantUser.objects.create_participant(
            email="other@example.com",
            client_file=other_cf,
            display_name="Other P",
            password="testpass123",
        )
        other_assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=other_p,
            client_file=other_cf,
            status="in_progress",
        )
        self._portal_login()
        response = self.client.post(
            f"/my/surveys/{other_assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "hacked"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 404)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_portal_surveys.py::AutoSaveViewTests -v`
Expected: FAIL (404 because URL doesn't exist yet)

**Step 3: Implement the auto-save view**

Add to `apps/portal/views.py` (after the existing `portal_survey_fill` function):

```python
@portal_login_required
def portal_survey_autosave(request, assignment_id):
    """HTMX auto-save: save a single answer to PartialAnswer."""
    from apps.surveys.engine import is_surveys_enabled
    from apps.surveys.models import PartialAnswer, SurveyAssignment, SurveyQuestion

    if not is_surveys_enabled():
        raise Http404

    # Only accept HTMX requests
    if not request.headers.get("HX-Request"):
        return HttpResponseBadRequest("HTMX request required")

    participant = request.participant_user
    assignment = get_object_or_404(
        SurveyAssignment,
        pk=assignment_id,
        participant_user=participant,
        status="in_progress",
    )

    question_id = request.POST.get("question_id")
    value = request.POST.get("value", "")

    # Verify question belongs to this survey
    question = get_object_or_404(
        SurveyQuestion,
        pk=question_id,
        section__survey=assignment.survey,
    )

    if value:
        pa, _ = PartialAnswer.objects.update_or_create(
            assignment=assignment,
            question=question,
            defaults={},
        )
        pa.value = value
        pa.save()
    else:
        # Empty value — delete partial answer if it exists
        PartialAnswer.objects.filter(
            assignment=assignment, question=question,
        ).delete()

    return HttpResponse(
        '<span role="status" class="save-indicator">Saved</span>',
        content_type="text/html",
    )
```

Add URL in `apps/portal/urls.py`:

```python
path("surveys/<int:assignment_id>/save/", views.portal_survey_autosave, name="survey_autosave"),
```

Also add `HttpResponseBadRequest` to the imports at the top of views.py if not already there:

```python
from django.http import HttpResponseBadRequest
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_portal_surveys.py::AutoSaveViewTests -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add apps/portal/views.py apps/portal/urls.py tests/test_portal_surveys.py
git commit -m "feat: add HTMX auto-save endpoint for portal surveys"
```

---

## Task 4: Refactor survey_fill View (GET) — Multi-Page + Pre-populate

Refactor the existing `portal_survey_fill` GET handler to support multi-page rendering and pre-populate from PartialAnswer.

**Files:**
- Modify: `apps/portal/views.py` (refactor `portal_survey_fill`)
- Test: `tests/test_portal_surveys.py` (add GET tests)

**Step 1: Write the failing tests**

Add to `tests/test_portal_surveys.py`:

```python
@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-fill",
)
class SurveyFillViewTests(TestCase):
    """Test the survey fill view GET handling."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="fill_staff", password="testpass123",
            display_name="Fill Staff",
        )
        self.survey = Survey.objects.create(
            name="Fill Survey", status="active", created_by=self.staff,
        )
        self.s1 = SurveySection.objects.create(
            survey=self.survey, title="Page One", sort_order=1,
        )
        self.q1 = SurveyQuestion.objects.create(
            section=self.s1, question_text="Name?",
            question_type="short_text", sort_order=1, required=True,
        )
        self.s2 = SurveySection.objects.create(
            survey=self.survey, title="Page Two", sort_order=2, page_break=True,
        )
        self.q2 = SurveyQuestion.objects.create(
            section=self.s2, question_text="How?",
            question_type="rating_scale", sort_order=1,
            options_json=[
                {"value": "1", "label": "Bad", "score": 1},
                {"value": "3", "label": "Good", "score": 3},
            ],
        )
        self.client_file = ClientFile.objects.create(
            record_id="FILL-001", status="active",
        )
        self.client_file.first_name = "Fill"
        self.client_file.last_name = "Test"
        self.client_file.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="fill@example.com",
            client_file=self.client_file,
            display_name="Fill P",
            password="testpass123",
        )
        from apps.admin_settings.models import FeatureToggle
        FeatureToggle.objects.update_or_create(
            feature_name="surveys", defaults={"is_enabled": True},
        )
        self.assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="pending",
        )

    def _portal_login(self):
        session = self.client.session
        session["portal_participant_id"] = self.participant.pk
        session.save()

    def test_get_renders_page_1(self):
        self._portal_login()
        response = self.client.get(
            f"/my/surveys/{self.assignment.pk}/fill/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page One")
        self.assertNotContains(response, "Page Two")  # page_break = different page
        self.assertContains(response, "Page 1 of 2")

    def test_get_page_2(self):
        self._portal_login()
        # Must be in_progress to access page 2
        self.assignment.status = "in_progress"
        self.assignment.save()
        response = self.client.get(
            f"/my/surveys/{self.assignment.pk}/fill/?page=2",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page Two")
        self.assertNotContains(response, "Page One")

    def test_get_pre_populates_from_partial(self):
        self._portal_login()
        self.assignment.status = "in_progress"
        self.assignment.save()
        pa = PartialAnswer(
            assignment=self.assignment, question=self.q1,
        )
        pa.value = "Pre-filled Name"
        pa.save()
        response = self.client.get(
            f"/my/surveys/{self.assignment.pk}/fill/",
        )
        self.assertContains(response, "Pre-filled Name")

    def test_marks_pending_as_in_progress(self):
        self._portal_login()
        self.assertEqual(self.assignment.status, "pending")
        self.client.get(f"/my/surveys/{self.assignment.pk}/fill/")
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, "in_progress")

    def test_scrolling_form_no_page_breaks(self):
        """Survey with no page breaks renders all sections on one page."""
        survey2 = Survey.objects.create(
            name="Scroll Survey", status="active", created_by=self.staff,
        )
        SurveySection.objects.create(
            survey=survey2, title="A", sort_order=1, page_break=False,
        )
        SurveySection.objects.create(
            survey=survey2, title="B", sort_order=2, page_break=False,
        )
        assignment2 = SurveyAssignment.objects.create(
            survey=survey2,
            participant_user=self.participant,
            client_file=self.client_file,
            status="pending",
        )
        self._portal_login()
        response = self.client.get(f"/my/surveys/{assignment2.pk}/fill/")
        self.assertContains(response, "A")
        self.assertContains(response, "B")
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_portal_surveys.py::SurveyFillViewTests -v`
Expected: Failures (current view doesn't support multi-page or pre-populate)

**Step 3: Refactor portal_survey_fill**

Replace the entire `portal_survey_fill` function in `apps/portal/views.py` with:

```python
@portal_login_required
def portal_survey_fill(request, assignment_id):
    """Fill in a survey — supports multi-page and auto-save."""
    from apps.surveys.engine import is_surveys_enabled
    from apps.surveys.models import (
        SurveyAnswer, SurveyAssignment, SurveyResponse, PartialAnswer,
    )
    from apps.portal.survey_helpers import (
        group_sections_into_pages, filter_visible_sections,
        get_partial_answers_dict, calculate_section_scores,
    )

    if not is_surveys_enabled():
        raise Http404

    participant = request.participant_user
    client_file = _get_client_file(request)

    assignment = get_object_or_404(
        SurveyAssignment,
        pk=assignment_id,
        participant_user=participant,
        status__in=("pending", "in_progress"),
    )
    survey = assignment.survey

    # Mark as in_progress on first visit
    if assignment.status == "pending":
        assignment.status = "in_progress"
        assignment.started_at = timezone.now()
        assignment.save(update_fields=["status", "started_at"])

    # Load all sections and partial answers
    all_sections = list(
        survey.sections.filter(is_active=True)
        .prefetch_related("questions")
        .order_by("sort_order")
    )
    partial_answers = get_partial_answers_dict(assignment)
    visible_sections = filter_visible_sections(all_sections, partial_answers)
    pages = group_sections_into_pages(visible_sections)
    is_multi_page = len(pages) > 1

    # Determine current page
    page_num = 1
    if is_multi_page:
        try:
            page_num = int(request.GET.get("page", 1))
        except (ValueError, TypeError):
            page_num = 1
        page_num = max(1, min(page_num, len(pages)))

    if request.method == "POST":
        action = request.POST.get("action", "submit")

        if is_multi_page and action == "next":
            # Save current page answers and go to next page
            current_sections = pages[page_num - 1]
            errors = _save_page_answers(
                request, assignment, current_sections, partial_answers,
            )
            if errors:
                return render(request, "portal/survey_fill.html", {
                    "participant": participant,
                    "assignment": assignment,
                    "survey": survey,
                    "sections": current_sections,
                    "page_num": page_num,
                    "total_pages": len(pages),
                    "is_multi_page": is_multi_page,
                    "is_last_page": page_num == len(pages),
                    "partial_answers": partial_answers,
                    "errors": errors,
                })
            # Refresh partial answers and page structure after save
            partial_answers = get_partial_answers_dict(assignment)
            visible_sections = filter_visible_sections(all_sections, partial_answers)
            pages = group_sections_into_pages(visible_sections)
            next_page = min(page_num + 1, len(pages))
            return redirect(f"{request.path}?page={next_page}")

        # Final submit
        # Re-read all partial answers to build final response
        partial_answers = get_partial_answers_dict(assignment)

        # For scrolling form or last page, also save current page
        if is_multi_page:
            current_sections = pages[page_num - 1]
        else:
            current_sections = visible_sections
        page_errors = _save_page_answers(
            request, assignment, current_sections, partial_answers,
        )
        if page_errors:
            return render(request, "portal/survey_fill.html", {
                "participant": participant,
                "assignment": assignment,
                "survey": survey,
                "sections": current_sections,
                "page_num": page_num,
                "total_pages": len(pages),
                "is_multi_page": is_multi_page,
                "is_last_page": True,
                "partial_answers": partial_answers,
                "errors": page_errors,
            })

        # Refresh and validate ALL required questions across all pages
        partial_answers = get_partial_answers_dict(assignment)
        visible_sections = filter_visible_sections(all_sections, partial_answers)
        all_errors = []
        for section in visible_sections:
            for question in section.questions.all().order_by("sort_order"):
                if question.required and not partial_answers.get(question.pk):
                    all_errors.append(question.question_text)

        if all_errors:
            # Find which page has the first error and redirect there
            pages = group_sections_into_pages(visible_sections)
            if is_multi_page:
                current_sections = pages[page_num - 1]
            return render(request, "portal/survey_fill.html", {
                "participant": participant,
                "assignment": assignment,
                "survey": survey,
                "sections": current_sections,
                "page_num": page_num,
                "total_pages": len(pages),
                "is_multi_page": is_multi_page,
                "is_last_page": True,
                "partial_answers": partial_answers,
                "errors": all_errors,
            })

        # Create final response from PartialAnswer data
        from django.db import transaction

        with transaction.atomic():
            response_obj = SurveyResponse.objects.create(
                survey=survey,
                assignment=assignment,
                client_file=client_file,
                channel="portal",
            )
            for question_pk, answer_value in partial_answers.items():
                from apps.surveys.models import SurveyQuestion
                try:
                    question = SurveyQuestion.objects.get(pk=question_pk)
                except SurveyQuestion.DoesNotExist:
                    continue

                answer = SurveyAnswer(
                    response=response_obj,
                    question=question,
                )
                answer.value = answer_value

                if question.question_type in ("rating_scale", "yes_no"):
                    try:
                        answer.numeric_value = int(answer_value)
                    except (ValueError, TypeError):
                        pass
                elif question.question_type == "single_choice":
                    for opt in (question.options_json or []):
                        if opt.get("value") == answer_value:
                            answer.numeric_value = opt.get("score")
                            break
                answer.save()

            assignment.status = "completed"
            assignment.completed_at = timezone.now()
            assignment.save(update_fields=["status", "completed_at"])

            # Clean up partial answers
            PartialAnswer.objects.filter(assignment=assignment).delete()

        _audit_portal_event(request, "portal_survey_submitted", metadata={
            "survey_id": str(survey.pk),
            "assignment_id": str(assignment.pk),
        })
        return redirect("portal:survey_thank_you", assignment_id=assignment.pk)

    # GET — render form
    if is_multi_page:
        current_sections = pages[page_num - 1]
    else:
        current_sections = visible_sections

    return render(request, "portal/survey_fill.html", {
        "participant": participant,
        "assignment": assignment,
        "survey": survey,
        "sections": current_sections,
        "page_num": page_num,
        "total_pages": len(pages),
        "is_multi_page": is_multi_page,
        "is_last_page": page_num == len(pages),
        "partial_answers": partial_answers,
        "errors": [],
    })


def _save_page_answers(request, assignment, sections, partial_answers):
    """Save answers from POST data for sections on the current page.

    Returns list of error messages for missing required fields.
    Updates partial_answers dict in place.
    """
    from apps.surveys.models import PartialAnswer, SurveyQuestion

    errors = []
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
                pa, _ = PartialAnswer.objects.update_or_create(
                    assignment=assignment,
                    question=question,
                    defaults={},
                )
                pa.value = raw_value
                pa.save()
                partial_answers[question.pk] = raw_value
            else:
                PartialAnswer.objects.filter(
                    assignment=assignment, question=question,
                ).delete()
                partial_answers.pop(question.pk, None)

    return errors
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_portal_surveys.py -v`
Expected: ALL PASS (some tests may need the template update from Task 6 — if so, note that the template renders but content assertions work)

**Step 5: Commit**

```bash
git add apps/portal/views.py tests/test_portal_surveys.py
git commit -m "feat: refactor survey fill view with multi-page and PartialAnswer integration"
```

---

## Task 5: Survey Fill Template — Full Rewrite

Rewrite `survey_fill.html` with HTMX auto-save, multi-page navigation, proper fieldset/legend semantics, and accessibility.

**Files:**
- Modify: `apps/portal/templates/portal/survey_fill.html`

**Step 1: Write the new template**

Replace `apps/portal/templates/portal/survey_fill.html` entirely:

```html
{% extends "portal/base_portal.html" %}
{% load i18n %}

{% block title %}{{ survey.name }}{% endblock %}

{% block content %}
<h1>{{ survey.name }}</h1>

{% if survey.description %}
<p>{{ survey.description }}</p>
{% endif %}

{% if is_multi_page %}
<div class="survey-progress" role="status" aria-live="polite">
    <small>{% blocktrans with current=page_num total=total_pages %}Page {{ current }} of {{ total }}{% endblocktrans %}</small>
    <progress value="{{ page_num }}" max="{{ total_pages }}" aria-label="{% trans 'Survey progress' %}"></progress>
</div>
{% endif %}

<div id="save-status" aria-live="polite"></div>

{% if errors %}
<article class="portal-message portal-message-error" role="alert">
    <p><strong>{% trans "Please answer all required questions:" %}</strong></p>
    <ul>
    {% for err in errors %}
        <li>{{ err }}</li>
    {% endfor %}
    </ul>
</article>
{% endif %}

<form method="post" id="survey-form">
    {% csrf_token %}

    {% for section in sections %}
    <fieldset class="survey-section">
        <legend><strong>{{ section.title }}</strong></legend>
        {% if section.instructions %}<p>{{ section.instructions }}</p>{% endif %}

        {% for question in section.questions.all %}
        <div class="survey-question" style="margin-bottom:1.5rem">

            {% if question.question_type == "short_text" %}
            <label for="q_{{ question.pk }}">
                {{ question.question_text }}{% if question.required %} <abbr title="{% trans 'required' %}" aria-hidden="true">*</abbr>{% endif %}
            </label>
            <input type="text" id="q_{{ question.pk }}" name="q_{{ question.pk }}"
                   value="{{ question.pk|partial_value:partial_answers }}"
                   {% if question.required %}required aria-required="true"{% endif %}
                   hx-post="{% url 'portal:survey_autosave' assignment_id=assignment.pk %}"
                   hx-trigger="blur"
                   hx-vals='{"question_id": "{{ question.pk }}"}'
                   hx-include="[name=csrfmiddlewaretoken]"
                   hx-target="#save-status"
                   hx-swap="innerHTML">

            {% elif question.question_type == "long_text" %}
            <label for="q_{{ question.pk }}">
                {{ question.question_text }}{% if question.required %} <abbr title="{% trans 'required' %}" aria-hidden="true">*</abbr>{% endif %}
            </label>
            <textarea id="q_{{ question.pk }}" name="q_{{ question.pk }}" rows="4"
                      {% if question.required %}required aria-required="true"{% endif %}
                      hx-post="{% url 'portal:survey_autosave' assignment_id=assignment.pk %}"
                      hx-trigger="blur"
                      hx-vals='{"question_id": "{{ question.pk }}"}'
                      hx-include="[name=csrfmiddlewaretoken]"
                      hx-target="#save-status"
                      hx-swap="innerHTML">{{ question.pk|partial_value:partial_answers }}</textarea>

            {% elif question.question_type == "yes_no" %}
            <label for="q_{{ question.pk }}">
                {{ question.question_text }}{% if question.required %} <abbr title="{% trans 'required' %}" aria-hidden="true">*</abbr>{% endif %}
            </label>
            <select id="q_{{ question.pk }}" name="q_{{ question.pk }}"
                    {% if question.required %}required aria-required="true"{% endif %}
                    hx-post="{% url 'portal:survey_autosave' assignment_id=assignment.pk %}"
                    hx-trigger="change"
                    hx-vals='{"question_id": "{{ question.pk }}"}'
                    hx-include="[name=csrfmiddlewaretoken]"
                    hx-target="#save-status"
                    hx-swap="innerHTML">
                <option value="">—</option>
                <option value="1" {% if question.pk|partial_value:partial_answers == "1" %}selected{% endif %}>{% trans "Yes" %}</option>
                <option value="0" {% if question.pk|partial_value:partial_answers == "0" %}selected{% endif %}>{% trans "No" %}</option>
            </select>

            {% elif question.question_type == "single_choice" %}
            <fieldset class="survey-question-group">
                <legend>
                    {{ question.question_text }}{% if question.required %} <abbr title="{% trans 'required' %}" aria-hidden="true">*</abbr>{% endif %}
                </legend>
                {% for opt in question.options_json %}
                <label>
                    <input type="radio" name="q_{{ question.pk }}" value="{{ opt.value }}"
                           {% if question.pk|partial_value:partial_answers == opt.value %}checked{% endif %}
                           {% if question.required %}required{% endif %}
                           hx-post="{% url 'portal:survey_autosave' assignment_id=assignment.pk %}"
                           hx-trigger="change"
                           hx-vals='{"question_id": "{{ question.pk }}"}'
                           hx-include="[name=csrfmiddlewaretoken]"
                           hx-target="#save-status"
                           hx-swap="innerHTML">
                    {{ opt.label }}
                </label>
                {% endfor %}
            </fieldset>

            {% elif question.question_type == "multiple_choice" %}
            <fieldset class="survey-question-group">
                <legend>
                    {{ question.question_text }}{% if question.required %} <abbr title="{% trans 'required' %}" aria-hidden="true">*</abbr>{% endif %}
                </legend>
                {% for opt in question.options_json %}
                <label>
                    <input type="checkbox" name="q_{{ question.pk }}" value="{{ opt.value }}"
                           {% if opt.value|in_multi_value:question.pk|partial_value:partial_answers %}checked{% endif %}
                           onchange="htmxSaveCheckboxGroup(this)"
                           data-save-url="{% url 'portal:survey_autosave' assignment_id=assignment.pk %}"
                           data-question-id="{{ question.pk }}">
                    {{ opt.label }}
                </label>
                {% endfor %}
            </fieldset>

            {% elif question.question_type == "rating_scale" %}
            <fieldset class="survey-question-group">
                <legend>
                    {{ question.question_text }}{% if question.required %} <abbr title="{% trans 'required' %}" aria-hidden="true">*</abbr>{% endif %}
                </legend>
                <div role="group" class="rating-scale">
                {% for opt in question.options_json %}
                    <label style="text-align:center">
                        <input type="radio" name="q_{{ question.pk }}" value="{{ opt.value }}"
                               {% if question.pk|partial_value:partial_answers == opt.value %}checked{% endif %}
                               {% if question.required %}required{% endif %}
                               hx-post="{% url 'portal:survey_autosave' assignment_id=assignment.pk %}"
                               hx-trigger="change"
                               hx-vals='{"question_id": "{{ question.pk }}"}'
                               hx-include="[name=csrfmiddlewaretoken]"
                               hx-target="#save-status"
                               hx-swap="innerHTML">
                        {{ opt.label }}
                    </label>
                {% endfor %}
                </div>
            </fieldset>
            {% endif %}

        </div>
        {% endfor %}
    </fieldset>
    {% endfor %}

    <div class="survey-nav">
        {% if is_multi_page and page_num > 1 %}
        <a href="?page={{ page_num|add:"-1" }}" class="outline" role="button">← {% trans "Back" %}</a>
        {% endif %}

        {% if is_multi_page and not is_last_page %}
        <button type="submit" name="action" value="next">{% trans "Next" %} →</button>
        {% else %}
        <button type="submit" name="action" value="submit">{% trans "Submit" %}</button>
        {% endif %}
    </div>
</form>

<p><a href="{% url 'portal:surveys' %}">← {% trans "Back to surveys" %}</a></p>

<style>
.survey-progress { margin-bottom: 1rem; }
.survey-progress progress { width: 100%; height: 0.5rem; margin-top: 0.25rem; }
.survey-question-group { border: none; padding: 0; margin: 0; }
.survey-question-group legend { font-weight: normal; padding: 0; margin-bottom: 0.5rem; }
.survey-nav { display: flex; gap: 1rem; justify-content: flex-end; margin-top: 1rem; }
.save-indicator { color: var(--pico-muted-color); font-size: 0.875rem; }
.save-error { color: var(--pico-del-color); font-size: 0.875rem; }
@media (prefers-reduced-motion: no-preference) {
    .save-indicator {
        animation: fade-out 2s ease-in forwards;
        animation-delay: 1s;
    }
}
@keyframes fade-out {
    from { opacity: 1; }
    to { opacity: 0; }
}
</style>

<script>
/* Auto-save for multiple_choice checkboxes — collects all checked values */
function htmxSaveCheckboxGroup(el) {
    const name = el.name;
    const form = el.closest('form');
    const checked = form.querySelectorAll('input[name="' + name + '"]:checked');
    const values = Array.from(checked).map(cb => cb.value).join(';');
    const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]').value;

    fetch(el.dataset.saveUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'HX-Request': 'true',
            'X-CSRFToken': csrfToken,
        },
        body: 'question_id=' + el.dataset.questionId + '&value=' + encodeURIComponent(values),
    })
    .then(r => r.text())
    .then(html => { document.getElementById('save-status').innerHTML = html; })
    .catch(() => {
        document.getElementById('save-status').innerHTML =
            '<span role="status" class="save-error">Could not save</span>';
    });
}

/* Focus management: after page load, focus page heading if multi-page */
document.addEventListener('DOMContentLoaded', function() {
    const progress = document.querySelector('.survey-progress');
    if (progress) {
        const heading = document.querySelector('h1');
        if (heading) {
            heading.setAttribute('tabindex', '-1');
            heading.focus();
        }
    }
});
</script>
{% endblock %}
```

**NOTE:** This template uses custom template filters `partial_value` and `in_multi_value`. These need to be created.

**Step 2: Create template tags**

Create `apps/portal/templatetags/survey_tags.py`:

```python
"""Template tags for portal survey forms."""
from django import template

register = template.Library()


@register.filter
def partial_value(question_pk, partial_answers):
    """Look up a question's saved value from partial_answers dict."""
    if not partial_answers or not question_pk:
        return ""
    return partial_answers.get(int(question_pk), "")


@register.filter
def in_multi_value(opt_value, saved_value):
    """Check if opt_value is in a semicolon-separated saved_value string."""
    if not saved_value:
        return False
    return str(opt_value) in str(saved_value).split(";")
```

Also ensure `apps/portal/templatetags/__init__.py` exists.

**Step 3: Run tests**

Run: `pytest tests/test_portal_surveys.py -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add apps/portal/templates/portal/survey_fill.html apps/portal/templatetags/
git commit -m "feat: rewrite survey fill template with HTMX auto-save and multi-page"
```

---

## Task 6: Review Page View and Template

Add the read-only view for completed survey responses.

**Files:**
- Modify: `apps/portal/views.py` (add `portal_survey_review`)
- Modify: `apps/portal/urls.py` (add review URL)
- Create: `apps/portal/templates/portal/survey_review.html`
- Modify: `apps/portal/templates/portal/surveys_list.html` (link completed items)
- Test: `tests/test_portal_surveys.py`

**Step 1: Write the failing test**

Add to `tests/test_portal_surveys.py`:

```python
@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-review",
)
class SurveyReviewViewTests(TestCase):
    """Test the read-only review page for completed surveys."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="review_staff", password="testpass123",
            display_name="Review Staff",
        )
        self.survey = Survey.objects.create(
            name="Review Survey", status="active", created_by=self.staff,
            show_scores_to_participant=True,
        )
        self.section = SurveySection.objects.create(
            survey=self.survey, title="Health", sort_order=1,
            scoring_method="sum", max_score=10,
        )
        self.q1 = SurveyQuestion.objects.create(
            section=self.section, question_text="How are you?",
            question_type="rating_scale", sort_order=1,
            options_json=[
                {"value": "1", "label": "Bad", "score": 1},
                {"value": "5", "label": "Good", "score": 5},
            ],
        )
        self.client_file = ClientFile.objects.create(
            record_id="REV-001", status="active",
        )
        self.client_file.first_name = "Review"
        self.client_file.last_name = "Test"
        self.client_file.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="review@example.com",
            client_file=self.client_file,
            display_name="Review P",
            password="testpass123",
        )
        from apps.admin_settings.models import FeatureToggle
        FeatureToggle.objects.update_or_create(
            feature_name="surveys", defaults={"is_enabled": True},
        )
        from apps.surveys.models import SurveyResponse, SurveyAnswer
        self.assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="completed",
        )
        self.response_obj = SurveyResponse.objects.create(
            survey=self.survey,
            assignment=self.assignment,
            client_file=self.client_file,
            channel="portal",
        )
        answer = SurveyAnswer(
            response=self.response_obj, question=self.q1,
        )
        answer.value = "5"
        answer.numeric_value = 5
        answer.save()

    def _portal_login(self):
        session = self.client.session
        session["portal_participant_id"] = self.participant.pk
        session.save()

    def test_review_page_renders(self):
        self._portal_login()
        response = self.client.get(
            f"/my/surveys/{self.assignment.pk}/review/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Review Survey")
        self.assertContains(response, "How are you?")

    def test_review_shows_scores(self):
        self._portal_login()
        response = self.client.get(
            f"/my/surveys/{self.assignment.pk}/review/",
        )
        self.assertContains(response, "5")
        self.assertContains(response, "10")  # max_score

    def test_review_404_for_pending(self):
        """Cannot review a survey that isn't completed."""
        self.assignment.status = "pending"
        self.assignment.save()
        self._portal_login()
        response = self.client.get(
            f"/my/surveys/{self.assignment.pk}/review/",
        )
        self.assertEqual(response.status_code, 404)
```

**Step 2: Implement the review view**

Add to `apps/portal/views.py`:

```python
@portal_login_required
def portal_survey_review(request, assignment_id):
    """Read-only view of a completed survey response."""
    from apps.surveys.engine import is_surveys_enabled
    from apps.surveys.models import SurveyAssignment, SurveyResponse, SurveyAnswer
    from apps.portal.survey_helpers import (
        filter_visible_sections, calculate_section_scores,
    )

    if not is_surveys_enabled():
        raise Http404

    participant = request.participant_user
    client_file = _get_client_file(request)

    assignment = get_object_or_404(
        SurveyAssignment,
        pk=assignment_id,
        participant_user=participant,
        status="completed",
    )
    survey = assignment.survey

    response_obj = SurveyResponse.objects.filter(
        assignment=assignment, client_file=client_file,
    ).first()
    if not response_obj:
        raise Http404

    # Build answers dict {question_pk: value}
    answers = SurveyAnswer.objects.filter(response=response_obj)
    answers_dict = {a.question_id: a.value for a in answers}

    all_sections = list(
        survey.sections.filter(is_active=True)
        .prefetch_related("questions")
        .order_by("sort_order")
    )
    visible_sections = filter_visible_sections(all_sections, answers_dict)

    # Calculate scores if configured
    scores = []
    if survey.show_scores_to_participant:
        scores = calculate_section_scores(visible_sections, answers_dict)

    return render(request, "portal/survey_review.html", {
        "participant": participant,
        "survey": survey,
        "assignment": assignment,
        "response_obj": response_obj,
        "sections": visible_sections,
        "answers": answers_dict,
        "scores": scores,
    })
```

Add URL in `apps/portal/urls.py`:

```python
path("surveys/<int:assignment_id>/review/", views.portal_survey_review, name="survey_review"),
```

**Step 3: Create review template**

Create `apps/portal/templates/portal/survey_review.html`:

```html
{% extends "portal/base_portal.html" %}
{% load i18n %}
{% load survey_tags %}

{% block title %}{{ survey.name }}{% endblock %}

{% block content %}
<h1>{{ survey.name }}</h1>
<p><small>{% blocktrans with date=response_obj.submitted_at|date:"N j, Y" %}Submitted on {{ date }}{% endblocktrans %}</small></p>

{% for section in sections %}
<section>
    <h2>{{ section.title }}</h2>

    {% for question in section.questions.all %}
    <div style="margin-bottom:1rem">
        <strong>{{ question.question_text }}</strong>
        {% with answer=question.pk|partial_value:answers %}
        {% if answer %}
        <p style="margin-top:0.25rem; padding-left:1rem; border-left:3px solid var(--pico-muted-border-color)">
            {% if question.question_type == "yes_no" %}
                {% if answer == "1" %}{% trans "Yes" %}{% elif answer == "0" %}{% trans "No" %}{% else %}{{ answer }}{% endif %}
            {% elif question.question_type == "single_choice" or question.question_type == "rating_scale" %}
                {% for opt in question.options_json %}
                    {% if opt.value == answer %}{{ opt.label }}{% endif %}
                {% endfor %}
            {% elif question.question_type == "multiple_choice" %}
                {{ answer }}
            {% else %}
                {{ answer }}
            {% endif %}
        </p>
        {% else %}
        <p style="margin-top:0.25rem; color:var(--pico-muted-color)"><em>{% trans "No answer" %}</em></p>
        {% endif %}
        {% endwith %}
    </div>
    {% endfor %}
</section>
{% endfor %}

{% if scores %}
<section>
    <h2>{% trans "Your Scores" %}</h2>
    <table aria-label="{% trans 'Survey scores' %}">
        <thead>
            <tr>
                <th scope="col">{% trans "Section" %}</th>
                <th scope="col">{% trans "Score" %}</th>
            </tr>
        </thead>
        <tbody>
        {% for s in scores %}
            <tr>
                <td>{{ s.title }}</td>
                <td>{{ s.score }} / {{ s.max_score }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</section>
{% endif %}

<p><a href="{% url 'portal:surveys' %}">← {% trans "Back to surveys" %}</a></p>
{% endblock %}
```

**Step 4: Update surveys_list.html to link completed items to review**

In `apps/portal/templates/portal/surveys_list.html`, change the completed responses table rows to link to the review page. Replace the `<td>{{ r.survey.name }}</td>` line with:

```html
<td><a href="{% url 'portal:survey_review' assignment_id=r.assignment_id %}">{{ r.survey.name }}</a></td>
```

**Step 5: Run tests**

Run: `pytest tests/test_portal_surveys.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add apps/portal/views.py apps/portal/urls.py \
    apps/portal/templates/portal/survey_review.html \
    apps/portal/templates/portal/surveys_list.html \
    tests/test_portal_surveys.py
git commit -m "feat: add read-only review page for completed surveys"
```

---

## Task 7: Thank-You Page with Scores

Enhance the thank-you page to show section scores when configured.

**Files:**
- Modify: `apps/portal/views.py` (update `portal_survey_thank_you`)
- Modify: `apps/portal/templates/portal/survey_thank_you.html`

**Step 1: Update the view**

In `portal_survey_thank_you`, add score calculation:

```python
@portal_login_required
def portal_survey_thank_you(request, assignment_id):
    """Thank-you page after completing a survey — with optional scores."""
    from apps.surveys.engine import is_surveys_enabled
    from apps.surveys.models import SurveyAssignment, SurveyResponse, SurveyAnswer
    from apps.portal.survey_helpers import (
        filter_visible_sections, calculate_section_scores,
    )

    if not is_surveys_enabled():
        raise Http404

    participant = request.participant_user
    client_file = _get_client_file(request)

    assignment = get_object_or_404(
        SurveyAssignment,
        pk=assignment_id,
        participant_user=participant,
    )
    survey = assignment.survey

    scores = []
    if survey.show_scores_to_participant:
        response_obj = SurveyResponse.objects.filter(
            assignment=assignment, client_file=client_file,
        ).first()
        if response_obj:
            answers = SurveyAnswer.objects.filter(response=response_obj)
            answers_dict = {a.question_id: a.value for a in answers}
            all_sections = list(
                survey.sections.filter(is_active=True)
                .prefetch_related("questions")
                .order_by("sort_order")
            )
            visible = filter_visible_sections(all_sections, answers_dict)
            scores = calculate_section_scores(visible, answers_dict)

    return render(request, "portal/survey_thank_you.html", {
        "participant": participant,
        "survey": survey,
        "scores": scores,
    })
```

**Step 2: Update the template**

Replace `apps/portal/templates/portal/survey_thank_you.html`:

```html
{% extends "portal/base_portal.html" %}
{% load i18n %}

{% block title %}{% trans "Thank You" %}{% endblock %}

{% block content %}
<article style="text-align:center; padding:2rem">
    <h1>{% trans "Thank you!" %}</h1>
    <p>{% blocktrans with name=survey.name %}Your response to "{{ name }}" has been submitted.{% endblocktrans %}</p>

    {% if scores %}
    <section style="text-align:left; margin:1.5rem auto; max-width:400px">
        <h2>{% trans "Your Scores" %}</h2>
        <table aria-label="{% trans 'Survey scores' %}">
            <tbody>
            {% for s in scores %}
                <tr>
                    <td>{{ s.title }}</td>
                    <td><strong>{{ s.score }}</strong> / {{ s.max_score }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </section>
    {% endif %}

    <a href="{% url 'portal:surveys' %}" role="button" class="outline">{% trans "Back to surveys" %}</a>
    <a href="{% url 'portal:dashboard' %}" role="button">{% trans "Go to Home" %}</a>
</article>
{% endblock %}
```

**Step 3: Run tests**

Run: `pytest tests/test_portal_surveys.py tests/test_surveys.py -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add apps/portal/views.py apps/portal/templates/portal/survey_thank_you.html
git commit -m "feat: add section scores to survey thank-you page"
```

---

## Task 8: Dashboard Badge Enhancement

Update the dashboard card to show "Questions for You" branding, badge, and smart linking (1 survey = go directly to form).

**Files:**
- Modify: `apps/portal/views.py` (update dashboard context)
- Modify: `apps/portal/templates/portal/dashboard.html`

**Step 1: Update the dashboard view**

In the `dashboard` function, change the `pending_surveys` block to also fetch the single assignment for direct linking:

```python
# Replace the pending_surveys section (lines ~590-602) with:
pending_surveys = 0
single_survey_url = None
try:
    from apps.surveys.engine import is_surveys_enabled
    from apps.surveys.models import SurveyAssignment
    if is_surveys_enabled():
        survey_assignments = SurveyAssignment.objects.filter(
            participant_user=participant,
            status__in=("pending", "in_progress"),
            survey__portal_visible=True,
        )
        pending_surveys = survey_assignments.count()
        if pending_surveys == 1:
            single_survey_url = f"/my/surveys/{survey_assignments.first().pk}/fill/"
except Exception:
    pass
```

Add `"single_survey_url": single_survey_url,` to the context dict.

**Step 2: Update the dashboard template**

Replace the surveys card block in `dashboard.html` (the `{% if features.surveys and pending_surveys %}` section):

```html
{% if features.surveys and pending_surveys %}
<a href="{% if single_survey_url %}{{ single_survey_url }}{% else %}{% url 'portal:surveys' %}{% endif %}" class="portal-card">
    <article>
        <svg aria-hidden="true" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
        <h2>{% trans "Questions for You" %}</h2>
        <p>{% blocktrans with worker_term=term.worker %}Forms and check-ins from your {{ worker_term }}.{% endblocktrans %}</p>
        <span class="badge" aria-label="{% blocktrans count counter=pending_surveys %}{{ counter }} survey pending{% plural %}{{ counter }} surveys pending{% endblocktrans %}">{{ pending_surveys }}</span>
    </article>
</a>
{% endif %}
```

**Step 3: Run tests**

Run: `pytest tests/test_portal_surveys.py tests/test_surveys.py -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add apps/portal/views.py apps/portal/templates/portal/dashboard.html
git commit -m "feat: update dashboard card with Questions for You branding and smart link"
```

---

## Task 9: Translations

Extract new translatable strings and add French translations.

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po`

**Step 1: Run translate_strings to extract**

```bash
python manage.py translate_strings
```

**Step 2: Add French translations for new strings**

Open `locale/fr/LC_MESSAGES/django.po` and add translations for these new strings:

| English | French |
|---|---|
| Questions for You | Questions pour vous |
| Forms and check-ins from your %(worker_term)s. | Formulaires et suivis de votre %(worker_term)s. |
| Page %(current)s of %(total)s | Page %(current)s de %(total)s |
| Survey progress | Progression du sondage |
| Back | Retour |
| Next | Suivant |
| Your Scores | Vos scores |
| Section | Section |
| Score | Score |
| Submitted on %(date)s | Soumis le %(date)s |
| No answer | Aucune réponse |
| %(counter)s survey pending (singular) | %(counter)s sondage en attente |
| %(counter)s surveys pending (plural) | %(counter)s sondages en attente |

**Step 3: Compile translations**

```bash
python manage.py translate_strings
```

**Step 4: Commit**

```bash
git add locale/
git commit -m "i18n: add French translations for portal survey feature"
```

---

## Task 10: Final Verification

Run all related tests to confirm everything works together.

**Step 1: Run survey tests**

```bash
pytest tests/test_surveys.py tests/test_portal_surveys.py -v
```

Expected: ALL PASS

**Step 2: Run related tests**

```bash
pytest -m "not browser and not scenario_eval" -v --timeout=120
```

Expected: ALL PASS (full suite minus browser tests)

**Step 3: Final commit — update TODO.md**

Mark PORTAL-Q1 as complete in TODO.md:

```
- [x] Build "Questions for You" portal feature — auto-save, multi-page, conditional sections, review page, dashboard badge — 2026-02-20 (PORTAL-Q1)
```

```bash
git add TODO.md
git commit -m "chore: mark PORTAL-Q1 as complete"
```
