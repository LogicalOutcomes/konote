"""Forms for Outcome Insights — programme + time period selection."""
from datetime import date, timedelta

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.programs.models import Program


# Time period presets — simpler than fiscal year math
TIME_PERIOD_CHOICES = [
    ("3m", _("Last 3 months")),
    ("6m", _("Last 6 months")),
    ("12m", _("Last 12 months")),
    ("custom", _("Custom range")),
]


class InsightsFilterForm(forms.Form):
    """Simple two-choice form: programme + time period."""

    program = forms.ModelChoiceField(
        queryset=Program.objects.filter(status="active"),
        required=True,
        label=_("Programme"),
        empty_label=_("— Select a programme —"),
    )

    time_period = forms.ChoiceField(
        choices=TIME_PERIOD_CHOICES,
        initial="6m",
        label=_("Time period"),
    )

    date_from = forms.DateField(
        required=False,
        label=_("From"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        required=False,
        label=_("To"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Scope to programmes the user has active roles in
        if user:
            from apps.programs.access import get_accessible_programs
            self.fields["program"].queryset = get_accessible_programs(user)

    def clean(self):
        cleaned = super().clean()
        period = cleaned.get("time_period")

        if period == "custom":
            if not cleaned.get("date_from"):
                self.add_error("date_from", _("Required for custom range."))
            if not cleaned.get("date_to"):
                self.add_error("date_to", _("Required for custom range."))
            if (
                cleaned.get("date_from")
                and cleaned.get("date_to")
                and cleaned["date_from"] > cleaned["date_to"]
            ):
                self.add_error("date_to", _("Must be after the start date."))
        else:
            # Calculate dates from preset
            today = date.today()
            months = {"3m": 3, "6m": 6, "12m": 12}.get(period, 6)
            cleaned["date_to"] = today
            cleaned["date_from"] = today - timedelta(days=months * 30)

        return cleaned
