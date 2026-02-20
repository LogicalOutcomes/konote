"""Survey forms for validation."""
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Survey, SurveyQuestion, SurveySection, SurveyTriggerRule


class SurveyForm(forms.ModelForm):
    """Form for creating/editing a survey."""

    class Meta:
        model = Survey
        fields = [
            "name", "name_fr", "description", "description_fr",
            "is_anonymous", "show_scores_to_participant", "portal_visible",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "description_fr": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "name": _("Survey name"),
            "name_fr": _("Survey name (French)"),
            "description": _("Description"),
            "description_fr": _("Description (French)"),
            "is_anonymous": _("Anonymous survey"),
            "show_scores_to_participant": _("Show scores to participant"),
            "portal_visible": _("Visible in participant portal"),
        }
        help_texts = {
            "is_anonymous": _(
                "If checked, responses are never linked to a participant file."
            ),
            "show_scores_to_participant": _(
                "If checked, participants will see section scores after submitting."
            ),
            "portal_visible": _(
                "Uncheck to hide this survey from the participant portal."
            ),
        }


class SurveySectionForm(forms.ModelForm):
    """Form for a survey section."""

    class Meta:
        model = SurveySection
        fields = [
            "title", "title_fr", "instructions", "instructions_fr",
            "sort_order", "page_break", "scoring_method", "max_score",
            "condition_question", "condition_value",
        ]
        widgets = {
            "instructions": forms.Textarea(attrs={"rows": 2}),
            "instructions_fr": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "title": _("Section title"),
            "title_fr": _("Section title (French)"),
            "instructions": _("Instructions"),
            "instructions_fr": _("Instructions (French)"),
            "sort_order": _("Display order"),
            "page_break": _("Start new page"),
            "scoring_method": _("Scoring method"),
            "max_score": _("Maximum score"),
            "condition_question": _("Show only when"),
            "condition_value": _("is answered"),
        }
        help_texts = {
            "condition_question": _("Leave blank to always show this section."),
            "condition_value": _("The answer value that makes this section visible."),
        }


class SurveyQuestionForm(forms.ModelForm):
    """Form for a survey question."""

    class Meta:
        model = SurveyQuestion
        fields = [
            "question_text", "question_text_fr", "question_type",
            "sort_order", "required", "options_json", "min_value", "max_value",
        ]
        widgets = {
            "options_json": forms.HiddenInput(),
        }
        labels = {
            "question_text": _("Question"),
            "question_text_fr": _("Question (French)"),
            "question_type": _("Question type"),
            "sort_order": _("Display order"),
            "required": _("Required"),
            "min_value": _("Minimum value"),
            "max_value": _("Maximum value"),
        }
        help_texts = {
            "min_value": _("For rating scales only."),
            "max_value": _("For rating scales only."),
        }


class QuestionOptionForm(forms.Form):
    """Form for a single answer option (for choice-type questions)."""

    value = forms.CharField(max_length=255, label=_("Value"))
    label = forms.CharField(max_length=500, label=_("Label"))
    label_fr = forms.CharField(
        max_length=500, required=False, label=_("Label (French)"),
    )
    score = forms.IntegerField(required=False, label=_("Score"))


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


class TriggerRuleForm(forms.ModelForm):
    """Form for creating/editing a survey trigger rule."""

    # Anchor is only relevant for time-based rules; default to enrolment_date.
    anchor = forms.ChoiceField(
        choices=SurveyTriggerRule.ANCHOR_CHOICES,
        required=False,
        label=_("Count days from"),
    )

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

    def clean_anchor(self):
        """Default anchor to enrolment_date when not provided."""
        value = self.cleaned_data.get("anchor")
        if not value:
            return "enrolment_date"
        return value


class CSVImportForm(forms.Form):
    """Form for uploading a survey via CSV."""

    csv_file = forms.FileField(label=_("CSV file"))
    survey_name = forms.CharField(max_length=255, label=_("Survey name"))
    survey_name_fr = forms.CharField(
        max_length=255, required=False, label=_("Survey name (French)"),
    )
