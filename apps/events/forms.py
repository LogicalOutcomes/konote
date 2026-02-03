"""Forms for events and alerts."""
from django import forms

from .models import Alert, Event, EventType


class EventTypeForm(forms.ModelForm):
    """Admin form for creating/editing event types."""

    class Meta:
        model = EventType
        fields = ["name", "description", "colour_hex", "status"]
        widgets = {
            "colour_hex": forms.TextInput(attrs={"type": "color"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class EventForm(forms.ModelForm):
    """Form for creating/editing events on a client timeline."""

    class Meta:
        model = Event
        fields = ["title", "description", "start_timestamp", "end_timestamp", "event_type", "related_note"]
        widgets = {
            "start_timestamp": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_timestamp": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["event_type"].queryset = EventType.objects.filter(status="active")
        self.fields["end_timestamp"].required = False
        self.fields["related_note"].required = False


class AlertForm(forms.Form):
    """Form for creating an alert on a client file."""

    content = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Describe the alert..."}),
        label="Alert Content",
    )


class AlertCancelForm(forms.Form):
    """Form for cancelling an alert with a reason."""

    status_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Reason for cancellation..."}),
        label="Cancellation Reason",
        required=True,
    )
