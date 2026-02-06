"""Forms for admin settings views."""
from django import forms

from .models import DEFAULT_TERMS, TerminologyOverride


class FeatureToggleForm(forms.Form):
    """Form for enabling/disabling a feature toggle."""

    feature_key = forms.CharField(max_length=100)
    action = forms.ChoiceField(choices=[("enable", "Enable"), ("disable", "Disable")])


class TerminologyForm(forms.Form):
    """Dynamic form with fields for English and French terminology.

    Each term has two fields:
    - {key}: English term (required)
    - {key}_fr: French term (optional, falls back to English)
    """

    def __init__(self, *args, **kwargs):
        current_terms_en = kwargs.pop("current_terms_en", {})
        current_terms_fr = kwargs.pop("current_terms_fr", {})
        super().__init__(*args, **kwargs)

        for key, defaults in DEFAULT_TERMS.items():
            default_en, default_fr = defaults

            # English field
            self.fields[key] = forms.CharField(
                max_length=255,
                initial=current_terms_en.get(key, default_en),
                label=key.replace("_", " ").title(),
                help_text=f"Default: {default_en}",
            )

            # French field
            self.fields[f"{key}_fr"] = forms.CharField(
                max_length=255,
                required=False,
                initial=current_terms_fr.get(key, ""),
                label=key.replace("_", " ").title() + " (FR)",
                help_text=f"Default: {default_fr}. Leave blank to use English.",
            )

    def save(self):
        """Create/update/delete overrides based on form data."""
        for key, defaults in DEFAULT_TERMS.items():
            default_en, default_fr = defaults
            value_en = self.cleaned_data[key].strip()
            value_fr = self.cleaned_data.get(f"{key}_fr", "").strip()

            # Check if we need an override (either EN or FR differs from default)
            en_is_default = value_en == default_en
            fr_is_default = value_fr == "" or value_fr == default_fr

            if en_is_default and fr_is_default:
                # No override needed — delete if one exists
                TerminologyOverride.objects.filter(term_key=key).delete()
            else:
                TerminologyOverride.objects.update_or_create(
                    term_key=key,
                    defaults={
                        "display_value": value_en,
                        "display_value_fr": value_fr,
                    },
                )


DOCUMENT_STORAGE_CHOICES = [
    ("none", "Not configured"),
    ("sharepoint", "SharePoint / OneDrive"),
    ("google_drive", "Google Drive"),
]


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

    # Document storage settings
    document_storage_provider = forms.ChoiceField(
        choices=DOCUMENT_STORAGE_CHOICES,
        initial="none",
        label="Document Storage Provider",
        help_text="External system where client documents are stored.",
    )
    document_storage_url_template = forms.CharField(
        max_length=500, required=False, label="URL Template",
        help_text='URL with {record_id} placeholder. Example for SharePoint: '
                  'https://contoso.sharepoint.com/sites/KoNote2/Clients/{record_id}/',
        widget=forms.TextInput(attrs={"placeholder": "https://example.com/clients/{record_id}/"}),
    )

    # Privacy officer contact (PIPEDA compliance)
    privacy_officer_name = forms.CharField(
        max_length=255, required=False, label="Privacy Officer Name",
        help_text="Displayed in privacy notices and erasure communications.",
    )
    privacy_officer_email = forms.EmailField(
        required=False, label="Privacy Officer Email",
        help_text="Contact email for privacy requests and data access inquiries.",
    )

    SETTING_KEYS = [
        "product_name", "support_email", "logo_url",
        "date_format", "session_timeout_minutes",
        "document_storage_provider", "document_storage_url_template",
        "privacy_officer_name", "privacy_officer_email",
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
