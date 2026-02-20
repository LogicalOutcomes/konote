# Surveys & Portal Questions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a survey system with automatic trigger rules, and a participant-facing "Questions for You" portal experience.

**Architecture:** New `apps/surveys/` Django app for all survey models, forms, views, and trigger engine. Portal-side views added to existing `apps/portal/`. Surveys are connected to participants via `SurveyAssignment`; trigger rules evaluate on page load and Django signals. Feature-toggled via `features.surveys`.

**Tech Stack:** Django 5, PostgreSQL, HTMX, Pico CSS, Fernet encryption.

**Design docs:**
- `tasks/surveys-design.md` (SURVEY1)
- `tasks/portal-questions-design.md` (PORTAL-Q1)

---

## Phase 1: Foundation Models & Migrations

### Task 1: Create the surveys app skeleton

**Files:**
- Create: `apps/surveys/__init__.py`
- Create: `apps/surveys/apps.py`
- Create: `apps/surveys/models.py`
- Create: `apps/surveys/admin.py`
- Create: `apps/surveys/forms.py` (empty placeholder)
- Create: `apps/surveys/views.py` (empty placeholder)
- Create: `apps/surveys/urls.py` (empty placeholder)
- Create: `apps/surveys/manage_urls.py` (empty placeholder)
- Create: `apps/surveys/signals.py` (empty placeholder)
- Modify: `konote/settings/base.py:50-64` — add `"apps.surveys"` to INSTALLED_APPS

**Step 1: Create the app directory and files**

Create `apps/surveys/__init__.py` (empty).

Create `apps/surveys/apps.py`:
```python
from django.apps import AppConfig


class SurveysConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.surveys"
    verbose_name = "Surveys"

    def ready(self):
        import apps.surveys.signals  # noqa: F401
```

Create empty placeholder files: `forms.py`, `views.py`, `urls.py`, `manage_urls.py`, `signals.py`, `admin.py` — each with a module docstring only.

**Step 2: Add to INSTALLED_APPS**

In `konote/settings/base.py`, add `"apps.surveys"` after `"apps.communications"` in the INSTALLED_APPS list.

**Step 3: Commit**

```bash
git add apps/surveys/ konote/settings/base.py
git commit -m "feat(surveys): create surveys app skeleton"
```

---

### Task 2: Survey, SurveySection, SurveyQuestion models

**Files:**
- Modify: `apps/surveys/models.py`
- Create: `tests/test_surveys.py`

**Step 1: Write the failing test**

Create `tests/test_surveys.py`:
```python
"""Tests for the surveys app.

Run with:
    pytest tests/test_surveys.py -v
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.auth_app.models import User
from apps.surveys.models import Survey, SurveySection, SurveyQuestion
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SurveyModelTests(TestCase):
    """Test Survey, SurveySection, and SurveyQuestion creation."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="survey_staff",
            password="testpass123",
            display_name="Survey Staff",
        )

    def test_create_survey_with_sections_and_questions(self):
        survey = Survey.objects.create(
            name="Test Survey",
            name_fr="Sondage test",
            created_by=self.staff,
        )
        section = SurveySection.objects.create(
            survey=survey,
            title="About You",
            title_fr="À propos de vous",
            sort_order=1,
        )
        q1 = SurveyQuestion.objects.create(
            section=section,
            question_text="How are you?",
            question_text_fr="Comment allez-vous?",
            question_type="single_choice",
            sort_order=1,
            required=True,
            options_json=[
                {"value": "good", "label": "Good", "label_fr": "Bien", "score": 2},
                {"value": "ok", "label": "OK", "label_fr": "Correct", "score": 1},
                {"value": "bad", "label": "Bad", "label_fr": "Mal", "score": 0},
            ],
        )
        self.assertEqual(survey.sections.count(), 1)
        self.assertEqual(section.questions.count(), 1)
        self.assertEqual(q1.question_type, "single_choice")
        self.assertEqual(str(survey), "Test Survey")

    def test_survey_defaults(self):
        survey = Survey.objects.create(
            name="Defaults Test",
            created_by=self.staff,
        )
        self.assertEqual(survey.status, "draft")
        self.assertFalse(survey.is_anonymous)
        self.assertFalse(survey.show_scores_to_participant)
        self.assertTrue(survey.portal_visible)

    def test_section_with_scoring(self):
        survey = Survey.objects.create(name="Scored", created_by=self.staff)
        section = SurveySection.objects.create(
            survey=survey,
            title="Health",
            sort_order=1,
            scoring_method="sum",
            max_score=20,
        )
        self.assertEqual(section.scoring_method, "sum")
        self.assertEqual(section.max_score, 20)

    def test_section_with_page_break(self):
        survey = Survey.objects.create(name="Paged", created_by=self.staff)
        s1 = SurveySection.objects.create(
            survey=survey, title="Page 1", sort_order=1, page_break=False,
        )
        s2 = SurveySection.objects.create(
            survey=survey, title="Page 2", sort_order=2, page_break=True,
        )
        self.assertFalse(s1.page_break)
        self.assertTrue(s2.page_break)

    def test_conditional_section(self):
        survey = Survey.objects.create(name="Conditional", created_by=self.staff)
        s1 = SurveySection.objects.create(
            survey=survey, title="Main", sort_order=1,
        )
        trigger_q = SurveyQuestion.objects.create(
            section=s1,
            question_text="Do you have children?",
            question_type="yes_no",
            sort_order=1,
            required=True,
        )
        s2 = SurveySection.objects.create(
            survey=survey,
            title="Childcare",
            sort_order=2,
            condition_question=trigger_q,
            condition_value="yes",
        )
        self.assertEqual(s2.condition_question, trigger_q)
        self.assertEqual(s2.condition_value, "yes")

    def test_question_types(self):
        survey = Survey.objects.create(name="Types", created_by=self.staff)
        section = SurveySection.objects.create(
            survey=survey, title="All Types", sort_order=1,
        )
        for qt in ["single_choice", "multiple_choice", "rating_scale",
                    "short_text", "long_text", "yes_no"]:
            q = SurveyQuestion.objects.create(
                section=section,
                question_text=f"Test {qt}",
                question_type=qt,
                sort_order=1,
            )
            self.assertEqual(q.question_type, qt)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py -v`
Expected: FAIL — models don't exist yet.

**Step 3: Write the models**

In `apps/surveys/models.py`:
```python
"""Survey models: surveys, sections, questions, and responses.

Surveys are structured feedback instruments with optional sections,
scoring, conditional branching, and bilingual support (EN/FR).
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field


class Survey(models.Model):
    """A structured feedback form with sections and questions."""

    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("active", _("Active")),
        ("closed", _("Closed")),
        ("archived", _("Archived")),
    ]

    name = models.CharField(max_length=255)
    name_fr = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(default="", blank=True)
    description_fr = models.TextField(default="", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    is_anonymous = models.BooleanField(
        default=False,
        help_text=_("If true, responses are never linked to a participant file."),
    )
    show_scores_to_participant = models.BooleanField(
        default=False,
        help_text=_("Whether participants see section scores after submission."),
    )
    portal_visible = models.BooleanField(
        default=True,
        help_text=_("Whether this survey appears in the participant portal."),
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="surveys_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "surveys"
        db_table = "surveys"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class SurveySection(models.Model):
    """A group of questions within a survey.

    Sections can serve as visual groupings, page breaks, scored subscales,
    or conditional blocks (shown only when a trigger question has a specific
    answer).
    """

    SCORING_CHOICES = [
        ("none", _("No scoring")),
        ("sum", _("Sum")),
        ("average", _("Average")),
    ]

    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="sections",
    )
    title = models.CharField(max_length=255)
    title_fr = models.CharField(max_length=255, blank=True, default="")
    instructions = models.TextField(default="", blank=True)
    instructions_fr = models.TextField(default="", blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    page_break = models.BooleanField(
        default=False,
        help_text=_("If true, this section starts a new page in the form."),
    )
    scoring_method = models.CharField(
        max_length=10, choices=SCORING_CHOICES, default="none",
    )
    max_score = models.PositiveIntegerField(null=True, blank=True)
    condition_question = models.ForeignKey(
        "SurveyQuestion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dependent_sections",
        help_text=_("Section only shows when this question has the condition value."),
    )
    condition_value = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "surveys"
        db_table = "survey_sections"
        ordering = ["survey", "sort_order"]

    def __str__(self):
        return f"{self.survey.name} — {self.title}"


class SurveyQuestion(models.Model):
    """A single question within a survey section."""

    TYPE_CHOICES = [
        ("single_choice", _("Single choice")),
        ("multiple_choice", _("Multiple choice")),
        ("rating_scale", _("Rating scale")),
        ("short_text", _("Short text")),
        ("long_text", _("Long text")),
        ("yes_no", _("Yes / No")),
    ]

    section = models.ForeignKey(
        SurveySection, on_delete=models.CASCADE, related_name="questions",
    )
    question_text = models.CharField(max_length=1000)
    question_text_fr = models.CharField(max_length=1000, blank=True, default="")
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    sort_order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=False)
    options_json = models.JSONField(
        default=list,
        blank=True,
        help_text=_("For choice questions: list of {value, label, label_fr, score}."),
    )
    min_value = models.IntegerField(null=True, blank=True)
    max_value = models.IntegerField(null=True, blank=True)

    class Meta:
        app_label = "surveys"
        db_table = "survey_questions"
        ordering = ["section", "sort_order"]

    def __str__(self):
        return f"Q{self.sort_order}: {self.question_text[:50]}"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_surveys.py -v`
Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add apps/surveys/models.py tests/test_surveys.py
git commit -m "feat(surveys): add Survey, SurveySection, SurveyQuestion models with tests"
```

---

### Task 3: SurveyTriggerRule model

**Files:**
- Modify: `apps/surveys/models.py`
- Modify: `tests/test_surveys.py`

**Step 1: Write the failing test**

Add to `tests/test_surveys.py`:
```python
from apps.events.models import EventType
from apps.programs.models import Program
from apps.surveys.models import SurveyTriggerRule


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class TriggerRuleModelTests(TestCase):
    """Test SurveyTriggerRule creation and constraints."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="trigger_staff", password="testpass123",
            display_name="Trigger Staff",
        )
        self.survey = Survey.objects.create(name="Trigger Test", created_by=self.staff)
        self.program = Program.objects.create(name="Youth Program")

    def test_create_enrolment_trigger(self):
        rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="enrolment",
            program=self.program,
            repeat_policy="once_per_enrolment",
            auto_assign=True,
            created_by=self.staff,
        )
        self.assertEqual(rule.trigger_type, "enrolment")
        self.assertTrue(rule.auto_assign)
        self.assertTrue(rule.is_active)

    def test_create_time_trigger(self):
        rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="time",
            program=self.program,
            recurrence_days=30,
            anchor="enrolment_date",
            repeat_policy="recurring",
            auto_assign=True,
            created_by=self.staff,
        )
        self.assertEqual(rule.recurrence_days, 30)
        self.assertEqual(rule.anchor, "enrolment_date")

    def test_create_event_trigger(self):
        et = EventType.objects.create(name="Crisis")
        rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="event",
            event_type=et,
            repeat_policy="once_per_participant",
            auto_assign=False,
            created_by=self.staff,
        )
        self.assertEqual(rule.event_type, et)
        self.assertFalse(rule.auto_assign)

    def test_create_characteristic_trigger(self):
        rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            include_existing=True,
            created_by=self.staff,
        )
        self.assertTrue(rule.include_existing)

    def test_trigger_with_due_days(self):
        rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="enrolment",
            program=self.program,
            repeat_policy="once_per_enrolment",
            auto_assign=True,
            due_days=7,
            created_by=self.staff,
        )
        self.assertEqual(rule.due_days, 7)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py::TriggerRuleModelTests -v`
Expected: FAIL — SurveyTriggerRule doesn't exist.

**Step 3: Write the model**

Add to `apps/surveys/models.py` after SurveyQuestion:
```python
class SurveyTriggerRule(models.Model):
    """Defines when a survey should be automatically assigned.

    Supports four trigger types:
    - event: fires when a specific event type is created for a participant
    - enrolment: fires when a participant is enrolled in a program
    - time: fires after N days from an anchor date (enrolment or last completion)
    - characteristic: fires based on program membership (evaluated on access)
    """

    TRIGGER_TYPE_CHOICES = [
        ("event", _("Event")),
        ("enrolment", _("Enrolment")),
        ("time", _("Time-based")),
        ("characteristic", _("Characteristic")),
    ]

    REPEAT_POLICY_CHOICES = [
        ("once_per_participant", _("Once per participant")),
        ("once_per_enrolment", _("Once per enrolment")),
        ("recurring", _("Recurring")),
    ]

    ANCHOR_CHOICES = [
        ("enrolment_date", _("Enrolment date")),
        ("last_completed", _("Last completion")),
    ]

    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="trigger_rules",
    )
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPE_CHOICES)
    event_type = models.ForeignKey(
        "events.EventType",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="survey_trigger_rules",
    )
    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="survey_trigger_rules",
    )
    recurrence_days = models.PositiveIntegerField(null=True, blank=True)
    anchor = models.CharField(
        max_length=20, choices=ANCHOR_CHOICES, default="enrolment_date",
    )
    repeat_policy = models.CharField(
        max_length=25, choices=REPEAT_POLICY_CHOICES, default="once_per_participant",
    )
    auto_assign = models.BooleanField(
        default=True,
        help_text=_("If true, assignment is automatic. If false, staff must approve."),
    )
    include_existing = models.BooleanField(
        default=False,
        help_text=_("When activated, also assign to participants who already match."),
    )
    is_active = models.BooleanField(default=True)
    due_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Set a due date this many days after assignment."),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="survey_rules_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "surveys"
        db_table = "survey_trigger_rules"

    def __str__(self):
        return f"{self.get_trigger_type_display()} rule for {self.survey.name}"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_surveys.py::TriggerRuleModelTests -v`
Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add apps/surveys/models.py tests/test_surveys.py
git commit -m "feat(surveys): add SurveyTriggerRule model with tests"
```

---

### Task 4: SurveyAssignment, SurveyResponse, SurveyAnswer, PartialAnswer models

**Files:**
- Modify: `apps/surveys/models.py`
- Modify: `tests/test_surveys.py`

**Step 1: Write the failing test**

Add to `tests/test_surveys.py`:
```python
from apps.clients.models import ClientFile
from apps.portal.models import ParticipantUser
from apps.surveys.models import (
    SurveyAssignment, SurveyResponse, SurveyAnswer, PartialAnswer,
)


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-surveys",
)
class AssignmentResponseModelTests(TestCase):
    """Test SurveyAssignment, SurveyResponse, SurveyAnswer, PartialAnswer."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="assign_staff", password="testpass123",
            display_name="Assign Staff",
        )
        self.survey = Survey.objects.create(name="Assignment Test", created_by=self.staff)
        self.section = SurveySection.objects.create(
            survey=self.survey, title="Section 1", sort_order=1,
        )
        self.question = SurveyQuestion.objects.create(
            section=self.section, question_text="Rate this",
            question_type="rating_scale", sort_order=1, min_value=1, max_value=5,
        )
        self.client_file = ClientFile.objects.create(
            record_id="SURV-001", status="active",
        )
        self.client_file.first_name = "Survey"
        self.client_file.last_name = "Participant"
        self.client_file.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="survey@example.com",
            client_file=self.client_file,
            display_name="Survey P",
            password="testpass123",
        )

    def test_create_assignment(self):
        assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="pending",
        )
        self.assertEqual(assignment.status, "pending")
        self.assertIsNone(assignment.triggered_by_rule)

    def test_assignment_status_flow(self):
        assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="awaiting_approval",
        )
        assignment.status = "pending"
        assignment.save()
        assignment.status = "in_progress"
        assignment.save()
        assignment.status = "completed"
        assignment.save()
        self.assertEqual(assignment.status, "completed")

    def test_create_response_and_answer(self):
        assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="completed",
        )
        response = SurveyResponse.objects.create(
            survey=self.survey,
            assignment=assignment,
            client_file=self.client_file,
            channel="portal",
        )
        answer = SurveyAnswer.objects.create(
            response=response,
            question=self.question,
            value="4",
            numeric_value=4,
        )
        self.assertEqual(response.answers.count(), 1)
        self.assertEqual(answer.numeric_value, 4)

    def test_partial_answer_upsert(self):
        assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="in_progress",
        )
        pa, created = PartialAnswer.objects.update_or_create(
            assignment=assignment,
            question=self.question,
            defaults={"value_encrypted": b"test-encrypted-value"},
        )
        self.assertTrue(created)
        pa2, created2 = PartialAnswer.objects.update_or_create(
            assignment=assignment,
            question=self.question,
            defaults={"value_encrypted": b"updated-value"},
        )
        self.assertFalse(created2)
        self.assertEqual(pa.pk, pa2.pk)

    def test_anonymous_response(self):
        """Anonymous survey responses have no client_file or assignment."""
        anon_survey = Survey.objects.create(
            name="Anon Survey", created_by=self.staff, is_anonymous=True,
        )
        response = SurveyResponse.objects.create(
            survey=anon_survey,
            channel="link",
            respondent_name_display="Anonymous Person",
        )
        self.assertIsNone(response.client_file)
        self.assertIsNone(response.assignment)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py::AssignmentResponseModelTests -v`
Expected: FAIL — models don't exist.

**Step 3: Write the models**

Add to `apps/surveys/models.py`:
```python
class SurveyAssignment(models.Model):
    """Tracks which surveys are assigned to which participants."""

    STATUS_CHOICES = [
        ("awaiting_approval", _("Awaiting approval")),
        ("pending", _("Pending")),
        ("in_progress", _("In progress")),
        ("completed", _("Completed")),
        ("dismissed", _("Dismissed")),
    ]

    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="assignments",
    )
    participant_user = models.ForeignKey(
        "portal.ParticipantUser",
        on_delete=models.CASCADE,
        related_name="survey_assignments",
    )
    client_file = models.ForeignKey(
        "clients.ClientFile",
        on_delete=models.CASCADE,
        related_name="survey_assignments",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    triggered_by_rule = models.ForeignKey(
        SurveyTriggerRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
    )
    trigger_reason = models.CharField(max_length=255, blank=True, default="")
    due_date = models.DateField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="survey_assignments_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "surveys"
        db_table = "survey_assignments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.survey.name} → {self.participant_user}"


class SurveyResponse(models.Model):
    """A completed survey submission."""

    CHANNEL_CHOICES = [
        ("link", _("Shareable link")),
        ("portal", _("Participant portal")),
        ("staff_entered", _("Staff data entry")),
    ]

    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="responses",
    )
    assignment = models.ForeignKey(
        SurveyAssignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responses",
    )
    client_file = models.ForeignKey(
        "clients.ClientFile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="survey_responses",
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    respondent_name_display = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_("Optional name for link responses. Not encrypted (non-PII)."),
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    token = models.CharField(max_length=64, blank=True, default="", unique=False)

    class Meta:
        app_label = "surveys"
        db_table = "survey_responses"
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Response to {self.survey.name} ({self.get_channel_display()})"


class SurveyAnswer(models.Model):
    """A single answer to a survey question."""

    response = models.ForeignKey(
        SurveyResponse, on_delete=models.CASCADE, related_name="answers",
    )
    question = models.ForeignKey(
        SurveyQuestion, on_delete=models.CASCADE, related_name="answers",
    )
    _value_encrypted = models.BinaryField(default=b"", blank=True)
    numeric_value = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("For scales/scores. Stored as plain integer for aggregation."),
    )

    class Meta:
        app_label = "surveys"
        db_table = "survey_answers"

    def __str__(self):
        return f"Answer to Q{self.question.sort_order}"

    @property
    def value(self):
        return decrypt_field(self._value_encrypted)

    @value.setter
    def value(self, val):
        self._value_encrypted = encrypt_field(val)


class PartialAnswer(models.Model):
    """In-progress answer for auto-save. Moved to SurveyAnswer on submit."""

    assignment = models.ForeignKey(
        SurveyAssignment, on_delete=models.CASCADE, related_name="partial_answers",
    )
    question = models.ForeignKey(
        SurveyQuestion, on_delete=models.CASCADE, related_name="partial_answers",
    )
    value_encrypted = models.BinaryField(default=b"")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "surveys"
        db_table = "survey_partial_answers"
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "question"],
                name="unique_partial_answer_per_question",
            ),
        ]

    def __str__(self):
        return f"Partial answer for Q{self.question.sort_order}"
```

**Note:** The `SurveyAnswer.value` property uses Fernet encryption for free-text answers. The `numeric_value` field is stored as a plain integer for aggregation queries. In tests, set `value` as a plain string (the test uses the simplified field directly for PartialAnswer — production code will use the encrypted property).

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_surveys.py::AssignmentResponseModelTests -v`
Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add apps/surveys/models.py tests/test_surveys.py
git commit -m "feat(surveys): add SurveyAssignment, SurveyResponse, SurveyAnswer, PartialAnswer models"
```

---

### Task 5: Generate and run migrations, add feature toggle

**Files:**
- Create: `apps/surveys/migrations/0001_initial.py` (generated)
- Modify: `apps/admin_settings/management/commands/apply_setup.py` (or seed data — add `surveys` feature toggle)

**Step 1: Generate migrations**

Run: `python manage.py makemigrations surveys`
Expected: Creates `0001_initial.py` with all 7 models.

**Step 2: Run migrations**

Run: `python manage.py migrate`
Expected: All tables created successfully.

**Step 3: Add the feature toggle**

Check how existing feature toggles are seeded (look at `apply_setup` or `seed_demo_data` command). Add `surveys` feature toggle with `is_enabled=False` by default.

**Step 4: Run all survey tests**

Run: `pytest tests/test_surveys.py -v`
Expected: All tests PASS.

**Step 5: Commit**

```bash
git add apps/surveys/migrations/ apps/admin_settings/
git commit -m "feat(surveys): add initial migration and surveys feature toggle"
```

---

## Phase 2: Trigger Engine

### Task 6: Evaluation engine — core logic

**Files:**
- Create: `apps/surveys/engine.py`
- Modify: `tests/test_surveys.py`

**Step 1: Write the failing test**

Add to `tests/test_surveys.py`:
```python
from datetime import timedelta
from django.utils import timezone
from apps.clients.models import ClientProgramEnrolment
from apps.surveys.engine import evaluate_survey_rules


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-engine",
)
class EvaluationEngineTests(TestCase):
    """Test the survey trigger evaluation engine."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="engine_staff", password="testpass123",
            display_name="Engine Staff",
        )
        self.program = Program.objects.create(name="Engine Program")
        self.survey = Survey.objects.create(
            name="Engine Survey", status="active", created_by=self.staff,
        )
        SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )
        self.client_file = ClientFile.objects.create(
            record_id="ENG-001", status="active",
        )
        self.client_file.first_name = "Engine"
        self.client_file.last_name = "Test"
        self.client_file.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="engine@example.com",
            client_file=self.client_file,
            display_name="Engine P",
            password="testpass123",
        )
        self.enrolment = ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
        )

    def test_characteristic_rule_creates_assignment(self):
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 1)
        self.assertEqual(new_assignments[0].status, "pending")

    def test_characteristic_rule_no_duplicate(self):
        rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        evaluate_survey_rules(self.client_file, self.participant)
        # Run again — should not create duplicate
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 0)
        self.assertEqual(SurveyAssignment.objects.count(), 1)

    def test_time_rule_not_due_yet(self):
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="time",
            program=self.program,
            recurrence_days=30,
            anchor="enrolment_date",
            repeat_policy="recurring",
            auto_assign=True,
            created_by=self.staff,
        )
        # Enrolment was just now — 30 days haven't passed
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 0)

    def test_time_rule_due(self):
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="time",
            program=self.program,
            recurrence_days=30,
            anchor="enrolment_date",
            repeat_policy="recurring",
            auto_assign=True,
            created_by=self.staff,
        )
        # Backdate enrolment to 31 days ago
        self.enrolment.enrolled_at = timezone.now() - timedelta(days=31)
        self.enrolment.save()
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 1)

    def test_staff_confirms_creates_awaiting_approval(self):
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=False,
            created_by=self.staff,
        )
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(new_assignments[0].status, "awaiting_approval")

    def test_skips_discharged_client(self):
        self.client_file.status = "discharged"
        self.client_file.save()
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 0)

    def test_skips_inactive_survey(self):
        self.survey.status = "draft"
        self.survey.save()
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 0)

    def test_overload_protection(self):
        """Don't assign if participant has 5+ pending surveys."""
        for i in range(5):
            s = Survey.objects.create(
                name=f"Overload {i}", status="active", created_by=self.staff,
            )
            SurveySection.objects.create(survey=s, title="S", sort_order=1)
            SurveyAssignment.objects.create(
                survey=s,
                participant_user=self.participant,
                client_file=self.client_file,
                status="pending",
            )
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 0)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py::EvaluationEngineTests -v`
Expected: FAIL — `engine.py` doesn't exist.

**Step 3: Write the evaluation engine**

Create `apps/surveys/engine.py`:
```python
"""Survey trigger rule evaluation engine.

Evaluates active trigger rules against a specific participant and
creates SurveyAssignment records when rules match. Called on:
- Portal dashboard load (time + characteristic rules)
- Staff client view load (time + characteristic rules)
- Event creation via signal (event rules)
- Enrolment creation via signal (enrolment rules)
"""
import logging
from datetime import timedelta

from django.db import IntegrityError
from django.utils import timezone

from apps.surveys.models import (
    SurveyAssignment,
    SurveyTriggerRule,
)

logger = logging.getLogger(__name__)

MAX_PENDING_SURVEYS = 5


def evaluate_survey_rules(client_file, participant_user=None):
    """Evaluate all active trigger rules for a participant.

    Args:
        client_file: The ClientFile to evaluate rules for.
        participant_user: The ParticipantUser (optional — may be None
            if participant has no portal account).

    Returns:
        List of newly created SurveyAssignment instances.
    """
    if client_file.status == "discharged":
        return []

    if participant_user and not participant_user.is_active:
        return []

    if participant_user is None:
        return []

    # Check overload
    pending_count = SurveyAssignment.objects.filter(
        participant_user=participant_user,
        status__in=["pending", "in_progress", "awaiting_approval"],
    ).count()
    if pending_count >= MAX_PENDING_SURVEYS:
        logger.info(
            "Skipping rule evaluation for %s — %d pending surveys (limit: %d)",
            participant_user, pending_count, MAX_PENDING_SURVEYS,
        )
        return []

    # Get active rules for active surveys only
    rules = SurveyTriggerRule.objects.filter(
        is_active=True,
        survey__status="active",
    ).select_related("survey", "program", "event_type")

    # Filter to time and characteristic rules (event/enrolment handled by signals)
    access_rules = rules.filter(trigger_type__in=["time", "characteristic"])

    new_assignments = []
    for rule in access_rules:
        assignment = _evaluate_single_rule(rule, client_file, participant_user)
        if assignment:
            new_assignments.append(assignment)
            # Re-check overload after each assignment
            if pending_count + len(new_assignments) >= MAX_PENDING_SURVEYS:
                break

    return new_assignments


def evaluate_event_rules(client_file, participant_user, event):
    """Evaluate event-type trigger rules after an event is created.

    Args:
        client_file: The participant's ClientFile.
        participant_user: The ParticipantUser (may be None).
        event: The newly created Event instance.

    Returns:
        List of newly created SurveyAssignment instances.
    """
    if client_file.status == "discharged":
        return []
    if participant_user and not participant_user.is_active:
        return []
    if participant_user is None:
        return []
    if not event.event_type:
        return []

    rules = SurveyTriggerRule.objects.filter(
        is_active=True,
        survey__status="active",
        trigger_type="event",
        event_type=event.event_type,
    ).select_related("survey")

    new_assignments = []
    for rule in rules:
        assignment = _evaluate_single_rule(rule, client_file, participant_user)
        if assignment:
            new_assignments.append(assignment)

    return new_assignments


def evaluate_enrolment_rules(client_file, participant_user, enrolment):
    """Evaluate enrolment-type trigger rules after a program enrolment.

    Args:
        client_file: The participant's ClientFile.
        participant_user: The ParticipantUser (may be None).
        enrolment: The newly created ClientProgramEnrolment instance.

    Returns:
        List of newly created SurveyAssignment instances.
    """
    if client_file.status == "discharged":
        return []
    if participant_user and not participant_user.is_active:
        return []
    if participant_user is None:
        return []

    rules = SurveyTriggerRule.objects.filter(
        is_active=True,
        survey__status="active",
        trigger_type="enrolment",
        program=enrolment.program,
    ).select_related("survey")

    new_assignments = []
    for rule in rules:
        assignment = _evaluate_single_rule(rule, client_file, participant_user)
        if assignment:
            new_assignments.append(assignment)

    return new_assignments


def _evaluate_single_rule(rule, client_file, participant_user):
    """Check if a single rule matches and create assignment if so.

    Returns:
        SurveyAssignment if created, None otherwise.
    """
    # Check program membership for rules that require it
    if rule.program:
        from apps.clients.models import ClientProgramEnrolment
        is_enrolled = ClientProgramEnrolment.objects.filter(
            client_file=client_file,
            program=rule.program,
            status="enrolled",
        ).exists()
        if not is_enrolled:
            return None

    # Check repeat policy
    if not _repeat_policy_allows(rule, participant_user, client_file):
        return None

    # For time-based rules, check if enough time has elapsed
    if rule.trigger_type == "time":
        if not _time_elapsed(rule, client_file, participant_user):
            return None

    # Create assignment
    status = "pending" if rule.auto_assign else "awaiting_approval"
    due_date = None
    if rule.due_days:
        due_date = (timezone.now() + timedelta(days=rule.due_days)).date()

    try:
        assignment, created = SurveyAssignment.objects.get_or_create(
            survey=rule.survey,
            participant_user=participant_user,
            status__in=["pending", "in_progress", "awaiting_approval"],
            defaults={
                "client_file": client_file,
                "status": status,
                "triggered_by_rule": rule,
                "trigger_reason": str(rule),
                "due_date": due_date,
            },
        )
        if created:
            return assignment
    except (IntegrityError, SurveyAssignment.MultipleObjectsReturned):
        pass

    return None


def _repeat_policy_allows(rule, participant_user, client_file):
    """Check if the repeat policy allows a new assignment."""
    existing = SurveyAssignment.objects.filter(
        survey=rule.survey,
        participant_user=participant_user,
    )

    if rule.repeat_policy == "once_per_participant":
        return not existing.exists()

    elif rule.repeat_policy == "once_per_enrolment":
        if rule.program:
            from apps.clients.models import ClientProgramEnrolment
            enrolment = ClientProgramEnrolment.objects.filter(
                client_file=client_file,
                program=rule.program,
                status="enrolled",
            ).order_by("-enrolled_at").first()
            if enrolment:
                return not existing.filter(
                    created_at__gte=enrolment.enrolled_at,
                ).exists()
        return not existing.exists()

    elif rule.repeat_policy == "recurring":
        # Don't stack: no new assignment if one is already pending/in_progress
        return not existing.filter(
            status__in=["pending", "in_progress", "awaiting_approval"],
        ).exists()

    return False


def _time_elapsed(rule, client_file, participant_user):
    """Check if enough time has elapsed for a time-based trigger."""
    if not rule.recurrence_days:
        return False

    anchor_date = None

    if rule.anchor == "enrolment_date" and rule.program:
        from apps.clients.models import ClientProgramEnrolment
        enrolment = ClientProgramEnrolment.objects.filter(
            client_file=client_file,
            program=rule.program,
            status="enrolled",
        ).order_by("-enrolled_at").first()
        if enrolment:
            anchor_date = enrolment.enrolled_at

    elif rule.anchor == "last_completed":
        last_completed = SurveyAssignment.objects.filter(
            survey=rule.survey,
            participant_user=participant_user,
            status="completed",
        ).order_by("-completed_at").first()
        if last_completed and last_completed.completed_at:
            anchor_date = last_completed.completed_at
        else:
            # No previous completion — fall back to enrolment date
            if rule.program:
                from apps.clients.models import ClientProgramEnrolment
                enrolment = ClientProgramEnrolment.objects.filter(
                    client_file=client_file,
                    program=rule.program,
                    status="enrolled",
                ).order_by("-enrolled_at").first()
                if enrolment:
                    anchor_date = enrolment.enrolled_at

    if anchor_date is None:
        return False

    elapsed = timezone.now() - anchor_date
    return elapsed >= timedelta(days=rule.recurrence_days)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_surveys.py::EvaluationEngineTests -v`
Expected: All 8 tests PASS.

**Step 5: Commit**

```bash
git add apps/surveys/engine.py tests/test_surveys.py
git commit -m "feat(surveys): add trigger rule evaluation engine with tests"
```

---

### Task 7: Django signals for event and enrolment triggers

**Files:**
- Modify: `apps/surveys/signals.py`
- Modify: `tests/test_surveys.py`

**Step 1: Write the failing test**

Add to `tests/test_surveys.py`:
```python
from apps.events.models import Event, EventType


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-signals",
)
class SignalTriggerTests(TestCase):
    """Test that event/enrolment creation triggers survey assignment."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="signal_staff", password="testpass123",
            display_name="Signal Staff",
        )
        self.program = Program.objects.create(name="Signal Program")
        self.event_type = EventType.objects.create(name="Intake")
        self.survey = Survey.objects.create(
            name="Signal Survey", status="active", created_by=self.staff,
        )
        SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )
        self.client_file = ClientFile.objects.create(
            record_id="SIG-001", status="active",
        )
        self.client_file.first_name = "Signal"
        self.client_file.last_name = "Test"
        self.client_file.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="signal@example.com",
            client_file=self.client_file,
            display_name="Signal P",
            password="testpass123",
        )

    def test_event_signal_creates_assignment(self):
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="event",
            event_type=self.event_type,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        # Creating an event with matching type should trigger assignment
        Event.objects.create(
            client_file=self.client_file,
            event_type=self.event_type,
            start_timestamp=timezone.now(),
        )
        self.assertEqual(
            SurveyAssignment.objects.filter(
                survey=self.survey,
                participant_user=self.participant,
            ).count(),
            1,
        )

    def test_enrolment_signal_creates_assignment(self):
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="enrolment",
            program=self.program,
            repeat_policy="once_per_enrolment",
            auto_assign=True,
            created_by=self.staff,
        )
        # Creating an enrolment should trigger assignment
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
        )
        self.assertEqual(
            SurveyAssignment.objects.filter(
                survey=self.survey,
                participant_user=self.participant,
            ).count(),
            1,
        )
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_surveys.py::SignalTriggerTests -v`
Expected: FAIL — signals not wired.

**Step 3: Write the signals**

In `apps/surveys/signals.py`:
```python
"""Django signals for survey trigger evaluation.

Listens for Event and ClientProgramEnrolment creation to immediately
evaluate matching trigger rules. Uses transaction.on_commit() to ensure
the triggering record is committed before creating assignments.
"""
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.clients.models import ClientProgramEnrolment
from apps.events.models import Event

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Event)
def evaluate_event_survey_rules(sender, instance, created, **kwargs):
    """When a new Event is created, check for matching event trigger rules."""
    if not created:
        return
    if not instance.event_type:
        return
    if not instance.client_file:
        return

    def _evaluate():
        from apps.surveys.engine import evaluate_event_rules

        client_file = instance.client_file
        participant_user = getattr(client_file, "portal_account", None)
        if participant_user is None:
            return

        try:
            new_assignments = evaluate_event_rules(
                client_file, participant_user, instance,
            )
            if new_assignments:
                logger.info(
                    "Event %s triggered %d survey assignment(s) for client %s",
                    instance.event_type.name,
                    len(new_assignments),
                    client_file.pk,
                )
        except Exception:
            logger.exception("Error evaluating event survey rules")

    transaction.on_commit(_evaluate)


@receiver(post_save, sender=ClientProgramEnrolment)
def evaluate_enrolment_survey_rules(sender, instance, created, **kwargs):
    """When a new enrolment is created, check for matching enrolment rules."""
    if not created:
        return
    if not instance.client_file:
        return

    def _evaluate():
        from apps.surveys.engine import evaluate_enrolment_rules

        client_file = instance.client_file
        participant_user = getattr(client_file, "portal_account", None)
        if participant_user is None:
            return

        try:
            new_assignments = evaluate_enrolment_rules(
                client_file, participant_user, instance,
            )
            if new_assignments:
                logger.info(
                    "Enrolment in %s triggered %d survey assignment(s) for client %s",
                    instance.program.name,
                    len(new_assignments),
                    client_file.pk,
                )
        except Exception:
            logger.exception("Error evaluating enrolment survey rules")

    transaction.on_commit(_evaluate)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_surveys.py::SignalTriggerTests -v`
Expected: Both tests PASS.

**Note:** If `on_commit` doesn't fire in tests (Django TestCase wraps in transactions), use `TransactionTestCase` or call the evaluate functions directly. The signal tests may need adjustment depending on Django's test transaction behaviour.

**Step 5: Commit**

```bash
git add apps/surveys/signals.py tests/test_surveys.py
git commit -m "feat(surveys): add Django signals for event/enrolment trigger evaluation"
```

---

## Phase 3: Staff-Side Survey Builder

### Task 8: Survey forms (create/edit)

**Files:**
- Modify: `apps/surveys/forms.py`
- Modify: `tests/test_surveys.py`

Write Django ModelForms for:
- `SurveyForm` — name, description, anonymous, portal_visible, show_scores_to_participant
- `SurveySectionForm` — title, instructions, page_break, scoring_method, max_score
- `SurveyQuestionForm` — question_text, question_type, required, options_json, min_value, max_value
- `SurveyTriggerRuleForm` — trigger_type, event_type, program, recurrence_days, anchor, repeat_policy, auto_assign, include_existing, due_days

Write tests covering form validation:
- Required fields
- Invalid question types rejected
- Options required for choice questions
- Recurrence_days required for time triggers

**Step 1:** Write failing tests for form validation
**Step 2:** Run tests — expect FAIL
**Step 3:** Implement forms
**Step 4:** Run tests — expect PASS
**Step 5:** Commit

---

### Task 9: CSV import parser

**Files:**
- Create: `apps/surveys/csv_import.py`
- Modify: `tests/test_surveys.py`

Write a function `parse_survey_csv(file_obj)` that:
- Reads CSV with columns: section, question, type, required, options, score_values, instructions, page_break, section_fr, question_fr, options_fr
- Groups rows by section name
- Returns a data structure: `{"sections": [{"title": "...", "questions": [...]}]}`
- Validates: required columns present, valid question types, matching option/score counts

Write tests covering:
- Valid CSV with multiple sections
- Missing required columns
- Invalid question type
- Mismatched options/score_values count
- Bilingual CSV with FR columns

**Step 1:** Write failing tests
**Step 2:** Run tests — expect FAIL
**Step 3:** Implement parser
**Step 4:** Run tests — expect PASS
**Step 5:** Commit

---

### Task 10: Staff survey views (CRUD)

**Files:**
- Modify: `apps/surveys/views.py`
- Create: `apps/surveys/manage_urls.py`
- Modify: `konote/urls.py` — add `path("manage/surveys/", include("apps.surveys.manage_urls"))`
- Create templates:
  - `apps/surveys/templates/surveys/survey_list.html`
  - `apps/surveys/templates/surveys/survey_create.html`
  - `apps/surveys/templates/surveys/survey_detail.html`
  - `apps/surveys/templates/surveys/survey_edit.html`
  - `apps/surveys/templates/surveys/trigger_rule_form.html`
  - `apps/surveys/templates/surveys/csv_import.html`
  - `apps/surveys/templates/surveys/csv_preview.html`

Views needed:
- `survey_list` — GET — list all surveys with status, response count, active rules
- `survey_create` — GET/POST — Step 1: survey content (manual or CSV import)
- `survey_detail` — GET — tabs: Questions, Responses, Rules, Settings
- `survey_edit` — GET/POST — edit survey content
- `trigger_rule_create` — GET/POST — Step 2: "When should this go out?"
- `csv_import` — GET/POST — upload CSV, show preview, save as draft
- `survey_activate` — POST — move from draft to active, activate rules
- `survey_close` — POST — close survey, deactivate rules

All views require `@login_required` and `@requires_permission("survey.manage", ...)` (or equivalent PM/admin check).

**Step 1:** Write tests for view access control (admin/PM can access, regular staff cannot)
**Step 2:** Write tests for survey CRUD (create, list, edit, activate, close)
**Step 3:** Implement views
**Step 4:** Create templates (extend `base.html`, use Pico CSS, HTMX for inline editing)
**Step 5:** Wire up URLs in `manage_urls.py` and add to `konote/urls.py`
**Step 6:** Run tests — expect PASS
**Step 7:** Commit

---

### Task 11: Manual assignment and bulk management views

**Files:**
- Modify: `apps/surveys/views.py`
- Modify: `apps/surveys/manage_urls.py`
- Create templates:
  - `apps/surveys/templates/surveys/pending_approvals.html`
  - `apps/surveys/templates/surveys/_client_survey_section.html` (partial for client file)

Views needed:
- `manual_assign` — POST — staff assigns a survey to a specific participant
- `approve_assignment` — POST — staff approves an awaiting_approval assignment
- `dismiss_assignment` — POST — staff dismisses an awaiting_approval assignment
- `pending_approvals` — GET — list all awaiting_approval assignments for PM's programs

**Step 1:** Write tests for assignment, approval, dismissal
**Step 2:** Implement views
**Step 3:** Create templates
**Step 4:** Run tests — expect PASS
**Step 5:** Commit

---

## Phase 4: Portal Experience

### Task 12: Portal questions list view and dashboard card

**Files:**
- Modify: `apps/portal/views.py`
- Modify: `apps/portal/urls.py`
- Modify: `apps/portal/templates/portal/dashboard.html`
- Create: `apps/portal/templates/portal/questions_list.html`
- Modify: `apps/portal/tests/` — add test file

Views needed:
- `questions_list` — GET — list pending/in-progress and completed assignments

Dashboard card:
- Add "Questions for You" card to dashboard, conditional on `features.surveys`
- Badge with pending + in_progress count
- Link to `/my/questions/` (or directly to form if only one pending)

**Step 1:** Write tests — list view with pending and completed assignments, dashboard card rendering
**Step 2:** Implement view
**Step 3:** Create template
**Step 4:** Update dashboard template
**Step 5:** Wire up URL
**Step 6:** Run tests — expect PASS
**Step 7:** Commit

---

### Task 13: Portal form-filling view (scrolling + multi-page)

**Files:**
- Modify: `apps/portal/views.py`
- Modify: `apps/portal/urls.py`
- Create: `apps/portal/templates/portal/question_form.html`
- Create: `apps/portal/templates/portal/question_form_page.html`

Views needed:
- `question_form` — GET — show the full form (scrolling) or first page (multi-page)
- `question_form_page` — GET — show a specific page for multi-page surveys

Template logic:
- Check if survey has page_break sections → multi-page layout with Next/Back
- No page breaks → scrolling form with all questions
- Render question types: radio buttons (single choice), checkboxes (multiple choice), number input (rating scale), text input/textarea
- Progress indicator: "Page X of Y" or "Question X of Y"
- Section headings and instructions
- Conditional sections hidden until trigger question is answered

**Step 1:** Write tests — form renders with correct question types, multi-page navigation
**Step 2:** Implement views
**Step 3:** Create templates
**Step 4:** Run tests — expect PASS
**Step 5:** Commit

---

### Task 14: Auto-save and conditional section evaluation

**Files:**
- Modify: `apps/portal/views.py`
- Modify: `apps/portal/urls.py`

Views needed:
- `question_autosave` — POST (HTMX) — save a single answer as PartialAnswer (on blur)
- `question_save_page` — POST (HTMX) — save all answers on current page, return next page

Auto-save logic:
1. Receive question_id + answer value
2. Encrypt the answer value
3. Upsert into PartialAnswer (update_or_create)
4. Return 204 No Content (or HTMX swap for page navigation)

Conditional section logic:
1. After saving answers on a page, re-evaluate conditional sections
2. If a section's condition is newly met, include it in the page flow
3. If condition is no longer met, clear partial answers for that section's questions

**Step 1:** Write tests — auto-save creates/updates PartialAnswer, conditional section visibility
**Step 2:** Implement views
**Step 3:** Run tests — expect PASS
**Step 4:** Commit

---

### Task 15: Submit and review views

**Files:**
- Modify: `apps/portal/views.py`
- Modify: `apps/portal/urls.py`
- Create: `apps/portal/templates/portal/question_confirm.html`
- Create: `apps/portal/templates/portal/question_review.html`

Views needed:
- `question_submit` — POST — validate required fields, move PartialAnswers to SurveyResponse/SurveyAnswer, set assignment to completed, calculate section scores
- `question_review` — GET — read-only view of completed answers with section headings and scores

Submit logic:
1. Validate all required questions have answers
2. Create SurveyResponse (channel="portal", client_file, assignment)
3. For each PartialAnswer: create SurveyAnswer (decrypt partial, re-encrypt into answer)
4. Delete PartialAnswer rows
5. Set assignment.status = "completed", assignment.completed_at = now
6. Calculate section scores (sum/average of numeric_value)
7. Redirect to confirmation page showing scores if applicable

**Step 1:** Write tests — submit creates response/answers, clears partials, calculates scores
**Step 2:** Implement views
**Step 3:** Create templates
**Step 4:** Run tests — expect PASS
**Step 5:** Commit

---

## Phase 5: Polish & Translations

### Task 16: Translations

**Files:**
- Modify all new templates to use `{% trans %}` and `{% blocktrans %}`
- Update `locale/fr/LC_MESSAGES/django.po`

**Step 1:** Wrap all user-facing strings in translation tags
**Step 2:** Run `python manage.py translate_strings`
**Step 3:** Fill in French translations in `.po` file
**Step 4:** Run `python manage.py translate_strings` again to compile
**Step 5:** Commit `.po` and `.mo` files

---

### Task 17: Feature toggle wiring and auto-deactivation

**Files:**
- Modify: `apps/surveys/models.py` — add `post_save` signal on Survey to deactivate rules when status changes to closed/archived
- Modify templates — wrap survey nav/cards in `{% if features.surveys %}`

**Step 1:** Write test — closing survey deactivates its trigger rules
**Step 2:** Implement signal
**Step 3:** Add feature toggle checks to templates and views
**Step 4:** Run tests — expect PASS
**Step 5:** Commit

---

### Task 18: Integration testing

**Files:**
- Modify: `tests/test_surveys.py`

Write end-to-end tests covering:
1. Create survey with CSV import → set trigger rule → enrol participant → verify assignment created
2. Portal participant opens form → fills in → auto-saves → submits → verify response stored
3. Staff-confirms flow: rule creates awaiting_approval → staff approves → participant sees pending
4. Conditional section: answer trigger question → verify conditional section appears
5. Overload protection: 5 pending surveys → new rule doesn't create 6th
6. Survey closed mid-progress: in_progress assignment still completable

**Step 1:** Write integration tests
**Step 2:** Run tests — expect PASS
**Step 3:** Commit

---

## Dependency Graph

```
Task 1 (app skeleton)
  └→ Task 2 (core models)
       └→ Task 3 (trigger rule model)
            └→ Task 4 (assignment/response models)
                 └→ Task 5 (migrations + feature toggle)
                      ├→ Task 6 (evaluation engine)
                      │    └→ Task 7 (signals)
                      ├→ Task 8 (forms)
                      │    ├→ Task 9 (CSV import)
                      │    └→ Task 10 (staff CRUD views)
                      │         └→ Task 11 (assignment management views)
                      └→ Task 12 (portal list + dashboard card)
                           └→ Task 13 (form-filling view)
                                └→ Task 14 (auto-save + conditional)
                                     └→ Task 15 (submit + review)
                                          └→ Task 16 (translations)
                                               └→ Task 17 (feature toggle wiring)
                                                    └→ Task 18 (integration tests)
```

**Parallelisable:** After Task 5 (migrations), Tasks 6-7 (engine), Tasks 8-11 (staff views), and Tasks 12-15 (portal views) can be worked on in parallel by separate agents since they touch different files.
