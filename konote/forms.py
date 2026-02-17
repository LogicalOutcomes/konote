"""Forms for AI-powered HTMX endpoints."""
from django import forms


class SuggestMetricsForm(forms.Form):
    """Form for the suggest-metrics AI endpoint."""

    target_description = forms.CharField(max_length=1000)


class ImproveOutcomeForm(forms.Form):
    """Form for the improve-outcome AI endpoint."""

    draft_text = forms.CharField(max_length=5000)


class GenerateNarrativeForm(forms.Form):
    """Form for the generate-narrative AI endpoint."""

    program_id = forms.IntegerField()
    date_from = forms.DateField()
    date_to = forms.DateField()


class SuggestNoteStructureForm(forms.Form):
    """Form for the suggest-note-structure AI endpoint."""

    target_id = forms.IntegerField()


class GoalBuilderChatForm(forms.Form):
    """Form for the goal-builder chat AI endpoint."""

    message = forms.CharField(max_length=1000)


class GoalBuilderSaveForm(forms.Form):
    """Form for saving a goal from the Goal Builder."""

    name = forms.CharField(max_length=255)
    description = forms.CharField(required=False, widget=forms.Textarea)
    client_goal = forms.CharField(required=False, widget=forms.Textarea)
    section_id = forms.IntegerField(required=False)
    new_section_name = forms.CharField(max_length=255, required=False)
    # Metric fields
    existing_metric_id = forms.IntegerField(required=False)
    metric_name = forms.CharField(max_length=255, required=False)
    metric_definition = forms.CharField(required=False, widget=forms.Textarea)
    metric_min = forms.FloatField(required=False)
    metric_max = forms.FloatField(required=False)
    metric_unit = forms.CharField(max_length=50, required=False)

    def clean(self):
        cleaned = super().clean()
        # Must provide either section_id or new_section_name
        if not cleaned.get("section_id") and not cleaned.get("new_section_name"):
            raise forms.ValidationError("Please select an existing section or enter a new section name.")
        # Must provide either existing_metric_id or custom metric fields
        if not cleaned.get("existing_metric_id"):
            if not cleaned.get("metric_name"):
                raise forms.ValidationError("Please provide a metric name for the custom metric.")
        return cleaned
