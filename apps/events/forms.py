"""Forms for events and alerts."""
from django import forms
from django.utils.translation import gettext_lazy as _

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

    # Additional fields for date-only mode
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("Start Date"),
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("End Date"),
    )

    class Meta:
        model = Event
        fields = ["title", "description", "all_day", "start_timestamp", "end_timestamp", "event_type", "related_note"]
        widgets = {
            "start_timestamp": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_timestamp": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "all_day": forms.CheckboxInput(attrs={
                "role": "switch",
                "aria-describedby": "all_day_help",
            }),
        }
        labels = {
            "all_day": _("All day event"),
        }
        help_texts = {
            "all_day": _("Toggle on to hide time fields and record date only."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["event_type"].queryset = EventType.objects.filter(status="active")
        self.fields["end_timestamp"].required = False
        self.fields["related_note"].required = False
        self.fields["start_timestamp"].required = False  # Conditional based on all_day

        # If editing an existing all-day event, populate date fields
        if self.instance and self.instance.pk and self.instance.all_day:
            if self.instance.start_timestamp:
                self.initial["start_date"] = self.instance.start_timestamp.date()
            if self.instance.end_timestamp:
                self.initial["end_date"] = self.instance.end_timestamp.date()

    def clean(self):
        cleaned_data = super().clean()
        all_day = cleaned_data.get("all_day", False)

        if all_day:
            # Use date fields instead of datetime fields
            start_date = cleaned_data.get("start_date")
            end_date = cleaned_data.get("end_date")

            if not start_date:
                self.add_error("start_date", _("Start date is required for all-day events."))
            else:
                # Convert date to datetime at midnight (start of day)
                from django.utils import timezone
                import datetime
                cleaned_data["start_timestamp"] = timezone.make_aware(
                    datetime.datetime.combine(start_date, datetime.time.min)
                )

            if end_date:
                cleaned_data["end_timestamp"] = timezone.make_aware(
                    datetime.datetime.combine(end_date, datetime.time.max)
                )
            else:
                cleaned_data["end_timestamp"] = None
        else:
            # Standard datetime mode - start_timestamp is required
            if not cleaned_data.get("start_timestamp"):
                self.add_error("start_timestamp", _("Start date and time is required."))

        return cleaned_data


class AlertForm(forms.Form):
    """Form for creating an alert on a client file."""

    content = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": _("Describe the alert...")}),
        label=_("Alert Content"),
    )


class AlertCancelForm(forms.Form):
    """Form for cancelling an alert with a reason."""

    status_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": _("Reason for cancellation...")}),
        label=_("Cancellation Reason"),
        required=True,
    )
