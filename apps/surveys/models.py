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
