"""Forms for admin settings views."""
from django import forms
from django.utils.translation import gettext_lazy as _

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
    ("none", _("Not configured")),
    ("sharepoint", _("SharePoint / OneDrive")),
    ("google_drive", _("Google Drive")),
]


class InstanceSettingsForm(forms.Form):
    """Form for instance-level settings."""

    product_name = forms.CharField(
        max_length=255, required=False, label=_("Product Name"),
        help_text=_("Shown in the header and page titles."),
    )
    support_email = forms.EmailField(
        required=False, label=_("Support Email"),
        help_text=_("Displayed in the footer or help pages."),
    )
    logo_url = forms.URLField(
        required=False, label=_("Logo URL"),
        help_text=_("URL to your organisation's logo image."),
    )
    date_format = forms.ChoiceField(
        choices=[
            ("Y-m-d", "2026-02-02 (ISO)"),
            ("M d, Y", "Feb 02, 2026"),
            ("d/m/Y", "02/02/2026"),
            ("m/d/Y", "02/02/2026 (US)"),
        ],
        label=_("Date Format"),
    )
    session_timeout_minutes = forms.IntegerField(
        min_value=5, max_value=480, initial=30,
        label=_("Session Timeout (minutes)"),
        help_text=_("Inactive sessions expire after this many minutes."),
    )

    # Document storage settings
    document_storage_provider = forms.ChoiceField(
        choices=DOCUMENT_STORAGE_CHOICES,
        initial="none",
        label=_("Document Storage Provider"),
        help_text=_("External system where participant documents are stored."),
    )
    document_storage_url_template = forms.CharField(
        max_length=500, required=False, label=_("URL Template"),
        help_text=_('URL with {record_id} placeholder. Example for SharePoint: '
                  'https://contoso.sharepoint.com/sites/konote/Participants/{record_id}/'),
        widget=forms.TextInput(attrs={"placeholder": "https://example.com/participants/{record_id}/"}),
    )

    # Privacy officer contact (PIPEDA compliance)
    privacy_officer_name = forms.CharField(
        max_length=255, required=False, label=_("Privacy Officer Name"),
        help_text=_("Displayed in privacy notices and erasure communications."),
    )
    privacy_officer_email = forms.EmailField(
        required=False, label=_("Privacy Officer Email"),
        help_text=_("Contact email for privacy requests and data access inquiries."),
    )

    # Participant portal footer contact
    portal_footer_text = forms.CharField(
        max_length=500, required=False, label=_("Portal Footer Text (English)"),
        help_text=_("Shown at the bottom of the participant portal. "
                     "Example: Your contact is Casey Worker casey@ngo.org"),
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    portal_footer_text_fr = forms.CharField(
        max_length=500, required=False, label=_("Portal Footer Text (French)"),
        help_text=_("French version. Leave blank to use the English text."),
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    SETTING_KEYS = [
        "product_name", "support_email", "logo_url",
        "date_format", "session_timeout_minutes",
        "document_storage_provider", "document_storage_url_template",
        "privacy_officer_name", "privacy_officer_email",
        "portal_footer_text", "portal_footer_text_fr",
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


class MessagingSettingsForm(forms.Form):
    """Form for the messaging settings page — profile selection, Safety-First, templates."""

    messaging_profile = forms.ChoiceField(
        choices=[
            ("record_keeping", _("Record-Keeping Only")),
            ("staff_sent", _("Staff-Sent Messages")),
            ("full_automation", _("Full Automation")),
        ],
        label=_("Messaging Profile"),
        widget=forms.RadioSelect,
    )
    safety_first_mode = forms.BooleanField(
        required=False,
        label=_("Safety-First Mode"),
        help_text=_(
            "Disables all outbound messaging and calendar feeds. "
            "For programs where contacting clients could create safety risks."
        ),
    )
    reminder_window_hours = forms.IntegerField(
        min_value=1, max_value=72, initial=24,
        label=_("Reminder Window (hours)"),
        help_text=_("How many hours before a meeting to send the reminder."),
    )
    sender_display_name = forms.CharField(
        max_length=100, required=False,
        label=_("Sender Display Name"),
        help_text=_(
            "Shown as the sender name on messages. "
            "Use a neutral name for sensitive services (e.g. 'Appt Reminder' instead of the org name)."
        ),
    )
    support_contact_name = forms.CharField(
        max_length=255, required=False,
        label=_("Support Contact Name"),
        help_text=_("Shown in error messages when messaging fails."),
    )
    support_contact_phone = forms.CharField(
        max_length=50, required=False,
        label=_("Support Contact Phone"),
    )

    # Message templates
    reminder_sms_en = forms.CharField(
        required=False,
        label=_("SMS Reminder Template (English)"),
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text=_("Use {date}, {time}, {org_phone} as placeholders. Keep under 160 characters per segment."),
    )
    reminder_sms_fr = forms.CharField(
        required=False,
        label=_("SMS Reminder Template (French)"),
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    reminder_email_body_en = forms.CharField(
        required=False,
        label=_("Email Reminder Template (English)"),
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text=_("Use {date}, {time}, {org_phone} as placeholders."),
    )
    reminder_email_body_fr = forms.CharField(
        required=False,
        label=_("Email Reminder Template (French)"),
        widget=forms.Textarea(attrs={"rows": 5}),
    )

    SETTING_KEYS = [
        "messaging_profile", "safety_first_mode", "reminder_window_hours",
        "sender_display_name", "support_contact_name", "support_contact_phone",
        "reminder_sms_en", "reminder_sms_fr",
        "reminder_email_body_en", "reminder_email_body_fr",
    ]

    def __init__(self, *args, **kwargs):
        current_settings = kwargs.pop("current_settings", {})
        super().__init__(*args, **kwargs)
        for key in self.SETTING_KEYS:
            if key in current_settings:
                if key == "safety_first_mode":
                    self.fields[key].initial = current_settings[key] == "true"
                else:
                    self.fields[key].initial = current_settings[key]

    def save(self):
        from .models import InstanceSetting
        for key in self.SETTING_KEYS:
            value = self.cleaned_data.get(key, "")
            if key == "safety_first_mode":
                value = "true" if value else "false"
            value = str(value).strip()
            if value and value != "false":
                InstanceSetting.objects.update_or_create(
                    setting_key=key, defaults={"setting_value": value}
                )
            elif key == "safety_first_mode":
                # Always store safety_first_mode so it's explicit
                InstanceSetting.objects.update_or_create(
                    setting_key=key, defaults={"setting_value": "false"}
                )
            else:
                InstanceSetting.objects.filter(setting_key=key).delete()
