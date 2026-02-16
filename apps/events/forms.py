"""Forms for events and alerts."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.programs.models import Program, UserProgramRole

from .models import Alert, Event, EventType


class EventTypeForm(forms.ModelForm):
    """Form for creating/editing event types.

    Pass requesting_user to scope owning_program choices for PMs.
    """

    class Meta:
        model = EventType
        fields = ["name", "description", "colour_hex", "owning_program", "status"]
        widgets = {
            "colour_hex": forms.TextInput(attrs={"type": "color"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if requesting_user and not requesting_user.is_admin:
            pm_program_ids = set(
                UserProgramRole.objects.filter(
                    user=requesting_user, role="program_manager", status="active",
                ).values_list("program_id", flat=True)
            )
            self.fields["owning_program"].queryset = Program.objects.filter(
                pk__in=pm_program_ids, status="active",
            )
            self.fields["owning_program"].empty_label = None
            self.fields["owning_program"].required = True


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
                self.initial["start_date"] = timezone.localtime(self.instance.start_timestamp).date()
            if self.instance.end_timestamp:
                self.initial["end_date"] = timezone.localtime(self.instance.end_timestamp).date()

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
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": _(
                "Example: Client has expressed thoughts of self-harm during "
                "last two sessions. Safety plan is in place\u2009—\u2009see case "
                "notes from Jan 15. All staff should check in about the "
                "safety plan at each visit."
            ),
        }),
        label=_("Alert Content"),
    )


class AlertCancelForm(forms.Form):
    """Form for cancelling an alert with a reason."""

    status_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": _("Reason for cancellation...")}),
        label=_("Cancellation Reason"),
        required=True,
    )


class AlertRecommendCancelForm(forms.Form):
    """Form for staff to recommend cancellation of an alert."""

    assessment = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": _("Explain why this alert should be cancelled..."),
        }),
        label=_("Assessment"),
        required=True,
    )


class AlertReviewRecommendationForm(forms.Form):
    """Form for PM to approve or reject a cancellation recommendation."""

    action = forms.ChoiceField(
        choices=[("approve", _("Approve")), ("reject", _("Reject"))],
        widget=forms.HiddenInput(),
    )
    review_note = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 3,
            "aria-describedby": "review-note-help",
        }),
        label=_("Your Feedback"),
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("action") == "reject" and not cleaned_data.get("review_note", "").strip():
            self.add_error("review_note", _("A note is required when rejecting a recommendation."))
        return cleaned_data


DEFAULT_LOCATION_OPTIONS = ["In person", "Phone", "Video call"]


def _build_location_choices(location_options):
    """Build (value, label) choices from a list of location option strings."""
    choices = [("", _("Select a location…"))]
    for opt in location_options:
        opt = opt.strip()
        if opt:
            choices.append((opt, opt))
    choices.append(("__other__", _("Other")))
    return choices


class MeetingQuickCreateForm(forms.Form):
    """Quick-create form — 3 fields, under 60 seconds to fill in."""

    start_timestamp = forms.DateTimeField(
        label=_("Date and Time"),
        widget=forms.DateTimeInput(attrs={
            "type": "datetime-local",
            "aria-describedby": "meeting-start-required meeting-start-help",
        }),
    )
    location = forms.ChoiceField(
        required=False,
        label=_("Location"),
    )
    location_custom = forms.CharField(
        max_length=255, required=False,
        label=_("Custom Location"),
        widget=forms.TextInput(attrs={
            "placeholder": _("Type your location"),
        }),
    )
    send_reminder = forms.BooleanField(
        required=False, initial=True,
        label=_("Send reminder to client"),
    )

    def __init__(self, *args, location_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        options = location_choices or DEFAULT_LOCATION_OPTIONS
        self.fields["location"].choices = _build_location_choices(options)

    def clean(self):
        cleaned_data = super().clean()
        location = cleaned_data.get("location", "")
        if location == "__other__":
            custom = cleaned_data.get("location_custom", "").strip()
            if not custom:
                self.add_error("location_custom", _("Please type a location."))
            cleaned_data["location"] = custom
        return cleaned_data


class MeetingEditForm(forms.Form):
    """Full edit form for meetings — all fields available."""

    start_timestamp = forms.DateTimeField(
        label=_("Date and Time"),
        widget=forms.DateTimeInput(attrs={
            "type": "datetime-local",
            "aria-describedby": "meeting-start-required meeting-start-help",
        }),
    )
    location = forms.ChoiceField(
        required=False,
        label=_("Location"),
    )
    location_custom = forms.CharField(
        max_length=255, required=False,
        label=_("Custom Location"),
        widget=forms.TextInput(attrs={
            "placeholder": _("Type your location"),
        }),
    )
    duration_minutes = forms.IntegerField(
        required=False, min_value=5, max_value=480,
        label=_("Duration (minutes)"),
    )
    status = forms.ChoiceField(
        choices=[
            ("scheduled", _("Scheduled")),
            ("completed", _("Completed")),
            ("cancelled", _("Cancelled")),
            ("no_show", _("No Show")),
        ],
        label=_("Status"),
    )

    def __init__(self, *args, location_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        options = location_choices or DEFAULT_LOCATION_OPTIONS
        self.fields["location"].choices = _build_location_choices(options)
        # If editing and current location isn't in the choices, pre-select "Other"
        if self.initial.get("location"):
            current = self.initial["location"]
            known_values = [v for v, _ in self.fields["location"].choices if v not in ("", "__other__")]
            if current not in known_values:
                self.initial["location_custom"] = current
                self.initial["location"] = "__other__"

    def clean(self):
        cleaned_data = super().clean()
        location = cleaned_data.get("location", "")
        if location == "__other__":
            custom = cleaned_data.get("location_custom", "").strip()
            if not custom:
                self.add_error("location_custom", _("Please type a location."))
            cleaned_data["location"] = custom
        return cleaned_data
