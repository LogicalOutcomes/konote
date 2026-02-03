"""Forms for admin settings views."""
from django import forms

from .models import DEFAULT_TERMS, TerminologyOverride


class TerminologyForm(forms.Form):
    """Dynamic form with one field per terminology key."""

    def __init__(self, *args, **kwargs):
        current_terms = kwargs.pop("current_terms", {})
        super().__init__(*args, **kwargs)
        for key, default in DEFAULT_TERMS.items():
            self.fields[key] = forms.CharField(
                max_length=255,
                initial=current_terms.get(key, default),
                label=key.replace("_", " ").title(),
                help_text=f"Default: {default}",
            )

    def save(self):
        """Create/update/delete overrides based on form data."""
        for key, default in DEFAULT_TERMS.items():
            value = self.cleaned_data[key].strip()
            if value == default:
                # No override needed — delete if one exists
                TerminologyOverride.objects.filter(term_key=key).delete()
            else:
                TerminologyOverride.objects.update_or_create(
                    term_key=key, defaults={"display_value": value}
                )


class InstanceSettingsForm(forms.Form):
    """Form for instance-level settings."""

    product_name = forms.CharField(
        max_length=255, required=False, label="Product Name",
        help_text="Shown in the header and page titles.",
    )
    support_email = forms.EmailField(
        required=False, label="Support Email",
        help_text="Displayed in the footer or help pages.",
    )
    logo_url = forms.URLField(
        required=False, label="Logo URL",
        help_text="URL to your organisation's logo image.",
    )
    date_format = forms.ChoiceField(
        choices=[
            ("Y-m-d", "2026-02-02 (ISO)"),
            ("M d, Y", "Feb 02, 2026"),
            ("d/m/Y", "02/02/2026"),
            ("m/d/Y", "02/02/2026 (US)"),
        ],
        label="Date Format",
    )
    session_timeout_minutes = forms.IntegerField(
        min_value=5, max_value=480, initial=30,
        label="Session Timeout (minutes)",
        help_text="Inactive sessions expire after this many minutes.",
    )

    SETTING_KEYS = [
        "product_name", "support_email", "logo_url",
        "date_format", "session_timeout_minutes",
    ]

    def __init__(self, *args, **kwargs):
        current_settings = kwargs.pop("current_settings", {})
        super().__init__(*args, **kwargs)
        for key in self.SETTING_KEYS:
            if key in current_settings:
                self.fields[key].initial = current_settings[key]

    def save(self):
        from .models import InstanceSetting
        for key in self.SETTING_KEYS:
            value = str(self.cleaned_data.get(key, "")).strip()
            if value:
                InstanceSetting.objects.update_or_create(
                    setting_key=key, defaults={"setting_value": value}
                )
            else:
                InstanceSetting.objects.filter(setting_key=key).delete()
