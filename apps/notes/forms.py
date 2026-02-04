"""Forms for progress notes."""
from django import forms

from .models import ProgressNote, ProgressNoteTemplate, ProgressNoteTemplateSection


class QuickNoteForm(forms.ModelForm):
    """Simple form for quick notes — just a text area."""

    consent_confirmed = forms.BooleanField(
        required=True,
        label="We created this note together",
        help_text="Confirm you reviewed this note with the participant.",
        error_messages={
            "required": "Please confirm you reviewed this note together.",
        },
    )

    class Meta:
        model = ProgressNote
        fields = ["notes_text", "follow_up_date"]
        widgets = {
            "notes_text": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Write your note here...",
                "required": True,
            }),
            "follow_up_date": forms.DateInput(attrs={
                "type": "date",
            }),
        }
        labels = {
            "follow_up_date": "Follow up by",
        }
        help_texts = {
            "follow_up_date": "(optional — adds to your home page reminders)",
        }

    def clean_notes_text(self):
        text = self.cleaned_data.get("notes_text", "").strip()
        if not text:
            raise forms.ValidationError("Note text is required.")
        return text


class FullNoteForm(forms.Form):
    """Top-level form for a full structured progress note."""

    template = forms.ModelChoiceField(
        queryset=ProgressNoteTemplate.objects.filter(status="active"),
        required=False,
        label="This note is for...",
        empty_label="Freeform",
    )
    session_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        help_text="Change if this note is for a different day.",
    )
    summary = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Optional summary..."}),
        required=False,
    )
    follow_up_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        label="Follow up by",
        help_text="(optional — adds to your home page reminders)",
    )
    participant_reflection = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 2,
            "placeholder": "Their words...",
        }),
        required=False,
        label="Participant's reflection",
        help_text="Record their words, not your interpretation.",
    )
    consent_confirmed = forms.BooleanField(
        required=True,
        label="We created this note together",
        help_text="Confirm you reviewed this note with the participant.",
        error_messages={
            "required": "Please confirm you reviewed this note together.",
        },
    )


class TargetNoteForm(forms.Form):
    """Notes for a single plan target within a full note."""

    target_id = forms.IntegerField(widget=forms.HiddenInput())
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Notes for this target..."}),
        required=False,
    )


class MetricValueForm(forms.Form):
    """A single metric value input."""

    metric_def_id = forms.IntegerField(widget=forms.HiddenInput())
    value = forms.CharField(required=False, max_length=100)

    def __init__(self, *args, metric_def=None, **kwargs):
        super().__init__(*args, **kwargs)
        if metric_def:
            self.metric_def = metric_def
            label = metric_def.name
            if metric_def.unit:
                label += f" ({metric_def.unit})"
            self.fields["value"].label = label
            # Set help text from definition
            help_parts = []
            if metric_def.definition:
                help_parts.append(metric_def.definition)
            if metric_def.min_value is not None or metric_def.max_value is not None:
                range_str = "Range: "
                if metric_def.min_value is not None:
                    range_str += str(metric_def.min_value)
                range_str += " – "
                if metric_def.max_value is not None:
                    range_str += str(metric_def.max_value)
                help_parts.append(range_str)
            self.fields["value"].help_text = " | ".join(help_parts)
            # Set input type and constraints for numeric metrics
            attrs = {}
            if metric_def.min_value is not None:
                attrs["min"] = metric_def.min_value
            if metric_def.max_value is not None:
                attrs["max"] = metric_def.max_value
            if attrs:
                attrs["type"] = "number"
                attrs["step"] = "any"
                self.fields["value"].widget = forms.NumberInput(attrs=attrs)

    def clean_value(self):
        val = self.cleaned_data.get("value", "").strip()
        if not val:
            return ""
        # Validate against min/max if the metric defines them
        if hasattr(self, "metric_def"):
            try:
                numeric = float(val)
            except ValueError:
                raise forms.ValidationError("Enter a valid number.")
            if self.metric_def.min_value is not None and numeric < self.metric_def.min_value:
                raise forms.ValidationError(
                    f"Value must be at least {self.metric_def.min_value}."
                )
            if self.metric_def.max_value is not None and numeric > self.metric_def.max_value:
                raise forms.ValidationError(
                    f"Value must be at most {self.metric_def.max_value}."
                )
        return val


class NoteTemplateForm(forms.ModelForm):
    """Form for creating/editing progress note templates."""

    class Meta:
        model = ProgressNoteTemplate
        fields = ["name", "status"]


class NoteTemplateSectionForm(forms.ModelForm):
    """Form for a section within a note template."""

    class Meta:
        model = ProgressNoteTemplateSection
        fields = ["name", "section_type", "sort_order"]


class NoteCancelForm(forms.Form):
    """Form for cancelling a progress note."""

    status_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Reason for cancellation..."}),
        label="Reason",
    )
