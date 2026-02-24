"""Client forms."""
from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.programs.models import Program

from .models import ClientFile, CustomFieldDefinition, CustomFieldGroup
from .validators import normalize_phone_number, validate_phone_number


class ConsentRecordForm(forms.Form):
    """Form to record client consent for data collection (PIPEDA/PHIPA compliance)."""

    CONSENT_TYPE_CHOICES = [
        ("written", _("Written consent")),
        ("verbal", _("Verbal consent")),
        ("electronic", _("Electronic consent")),
    ]

    consent_type = forms.ChoiceField(
        choices=CONSENT_TYPE_CHOICES,
        label=_("Consent type"),
        initial="written",
    )
    consent_date = forms.DateField(
        label=_("Date consent was obtained"),
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=timezone.now,
    )
    notes = forms.CharField(
        required=False,
        label=_("Notes (optional)"),
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": _("Any additional details about how consent was obtained...")}),
    )


class ClientContactForm(forms.Form):
    """Narrow form for editing client phone number only.

    Used by front desk (client.edit_contact: ALLOW) and staff (SCOPED).
    Does NOT include address or emergency contact — safety implications for DV.
    Replace with PER_FIELD form in Phase 2.
    """

    phone = forms.CharField(
        max_length=20, required=False,
        label=_("Phone Number"),
        widget=forms.TextInput(attrs={
            "type": "tel",
            "placeholder": _("(613) 555-1234"),
            "autofocus": True,
            "aria-describedby": "phone-errors",
        }),
    )

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone:
            validate_phone_number(phone)
            phone = normalize_phone_number(phone)
        return phone


class ClientFileForm(forms.Form):
    """Form for client PII — plain form since fields are encrypted properties."""

    first_name = forms.CharField(max_length=255, label=_("First Name"))
    last_name = forms.CharField(max_length=255, label=_("Last Name"))
    preferred_name = forms.CharField(
        max_length=255, required=False,
        label=_("Preferred Name"),
        widget=forms.TextInput(attrs={"placeholder": _("What do you prefer to be called?")}),
    )
    middle_name = forms.CharField(max_length=255, required=False, label=_("Middle Name"))
    phone = forms.CharField(
        max_length=20, required=False,
        label=_("Phone Number"),
        widget=forms.TextInput(attrs={"type": "tel", "placeholder": _("(613) 555-1234")}),
    )
    birth_date = forms.DateField(required=False, label=_("Date of Birth"), widget=forms.DateInput(attrs={"type": "date"}))
    record_id = forms.CharField(max_length=100, required=False, label=_("Record ID"))
    status = forms.ChoiceField(choices=ClientFile.STATUS_CHOICES, label=_("Status"))

    # Messaging consent (Phase 3 — one-checkbox workflow at intake)
    email = forms.CharField(
        max_length=255, required=False,
        label=_("Email Address"),
        widget=forms.EmailInput(attrs={"placeholder": _("client@example.com")}),
    )
    preferred_language = forms.ChoiceField(
        choices=[("en", _("English")), ("fr", _("French"))],
        initial="en",
        label=_("Preferred Language for Messages"),
    )
    sms_consent = forms.BooleanField(
        required=False,
        label=_("Client consents to text message reminders"),
        help_text=_("CASL compliance: express consent is recorded with today's date."),
    )
    email_consent = forms.BooleanField(
        required=False,
        label=_("Client consents to email reminders"),
    )

    # Program enrolment — used by create view only (edit no longer manages programs).
    # Transfer view has its own form (ClientTransferForm).
    programs = forms.ModelMultipleChoiceField(
        queryset=Program.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_("Programs"),
        error_messages={"required": _("Please select at least one program.")},
    )

    def __init__(self, *args, available_programs=None, circle_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if available_programs is not None:
            self.fields["programs"].queryset = available_programs
            self.fields["programs"].required = True
            # Pre-select when user has exactly one program (IMPROVE-2)
            if not self.is_bound and available_programs.count() == 1:
                self.initial["programs"] = [available_programs.first().pk]

        # Circle fields — only added when circles feature toggle is on
        if circle_choices is not None:
            self.fields["existing_circle"] = forms.ChoiceField(
                choices=[("", _("— None —"))] + list(circle_choices),
                required=False,
                label=_("Link to existing circle"),
                help_text=_("Optional — link to an existing circle or create a new one below."),
            )
            self.fields["new_circle_name"] = forms.CharField(
                max_length=255,
                required=False,
                label=_("Or create a new circle"),
                widget=forms.TextInput(attrs={"placeholder": _("e.g. Garcia Family")}),
            )

    def clean(self):
        cleaned = super().clean()
        existing = cleaned.get("existing_circle", "")
        new_name = cleaned.get("new_circle_name", "").strip()
        if existing and new_name:
            raise forms.ValidationError(
                _("Choose either an existing circle or create a new one — not both.")
            )
        return cleaned

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone:
            validate_phone_number(phone)
            phone = normalize_phone_number(phone)
        return phone


class ClientTransferForm(forms.Form):
    """Form for transferring a client between programs.

    Separated from ClientFileForm so transfers have their own permission
    (client.transfer) and audit trail. Gated by @requires_permission.
    """

    programs = forms.ModelMultipleChoiceField(
        queryset=Program.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label=_("Programs"),
        error_messages={"required": _("Please select at least one program.")},
    )

    cross_program_sharing = forms.ChoiceField(
        required=False,
        choices=[
            ("default", _("Follow agency setting")),
            ("consent", _("Share across programs")),
            ("restrict", _("Restrict to one program")),
        ],
        initial="default",
        label=_("Cross-program note sharing"),
        help_text=_(
            "Controls whether clinical notes from other programs are visible "
            "for this participant. Most participants should use the agency default."
        ),
        widget=forms.Select,
    )

    transfer_reason = forms.CharField(
        required=False,
        label=_("Reason for transfer (optional)"),
        widget=forms.Textarea(attrs={
            "rows": 2,
            "placeholder": _("Why is this participant being added to or removed from a program?"),
        }),
    )

    def __init__(self, *args, available_programs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if available_programs is not None:
            self.fields["programs"].queryset = available_programs


class CustomFieldGroupForm(forms.ModelForm):
    class Meta:
        model = CustomFieldGroup
        fields = ["title", "sort_order", "status"]
        labels = {
            "sort_order": _("Display order"),
        }


class CustomFieldValuesForm(forms.Form):
    """Dynamic form for saving custom field values on a client.

    Builds one field per active custom field definition, keyed as 'custom_{pk}'.
    """

    def __init__(self, *args, field_definitions=None, **kwargs):
        super().__init__(*args, **kwargs)
        if field_definitions:
            for field_def in field_definitions:
                field_key = f"custom_{field_def.pk}"
                if field_def.input_type == "checkbox":
                    self.fields[field_key] = forms.BooleanField(
                        required=False, label=field_def.name,
                    )
                elif field_def.input_type == "number":
                    self.fields[field_key] = forms.CharField(
                        required=field_def.is_required,
                        label=field_def.name,
                    )
                elif field_def.input_type == "select" and field_def.options_json:
                    choices = [("", _("— Select —"))] + [
                        (opt, opt) for opt in field_def.options_json
                    ]
                    self.fields[field_key] = forms.ChoiceField(
                        choices=choices,
                        required=field_def.is_required,
                        label=field_def.name,
                    )
                elif field_def.input_type == "select_other" and field_def.options_json:
                    choices = [("", _("— Select —"))] + [
                        (opt, opt) for opt in field_def.options_json
                    ] + [("__other__", _("Other"))]
                    self.fields[field_key] = forms.ChoiceField(
                        choices=choices,
                        required=field_def.is_required,
                        label=field_def.name,
                    )
                    # Additional text field for "Other" free-text entry
                    self.fields[f"{field_key}_other"] = forms.CharField(
                        required=False,
                        label=_("Other (please specify)"),
                        widget=forms.TextInput(attrs={"placeholder": field_def.placeholder or ""}),
                    )
                else:
                    self.fields[field_key] = forms.CharField(
                        required=field_def.is_required,
                        label=field_def.name,
                        widget=forms.Textarea(attrs={"rows": 2})
                        if field_def.input_type == "textarea"
                        else forms.TextInput(attrs={"placeholder": field_def.placeholder or ""}),
                    )


class CustomFieldDefinitionForm(forms.ModelForm):
    class Meta:
        model = CustomFieldDefinition
        fields = [
            "group", "name", "input_type", "placeholder", "is_required",
            "is_sensitive", "front_desk_access", "options_json", "sort_order", "status",
        ]
        widgets = {
            "options_json": forms.Textarea(attrs={"rows": 3, "placeholder": _('["Option 1", "Option 2"]')}),
        }
        labels = {
            "sort_order": _("Display order"),
        }
        help_texts = {
            "front_desk_access": _("Set front desk access to 'View and edit' for contact info, emergency contacts, and safety alerts."),
        }


# --- Erasure forms ---

class ErasureRequestForm(forms.Form):
    """Form for requesting client data erasure with tier selection and acknowledgements."""

    REASON_CATEGORY_CHOICES = [
        ("client_requested", _("Participant requested")),
        ("retention_expired", _("Retention period expired")),
        ("discharged", _("Participant discharged")),
        ("other", _("Other")),
    ]

    TIER_CHOICES = [
        ("anonymise", _("Anonymise — Remove identifying information, keep service records")),
        ("anonymise_purge", _("Anonymise + Purge Notes — Remove identifying information and all narrative content")),
        ("full_erasure", _("Full Erasure — Delete all records permanently")),
    ]

    erasure_tier = forms.ChoiceField(
        choices=TIER_CHOICES,
        widget=forms.RadioSelect,
        initial="anonymise",
        label=_("Erasure level"),
    )

    reason_category = forms.ChoiceField(
        choices=REASON_CATEGORY_CHOICES,
        label=_("Reason for erasure"),
    )
    request_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": _("Explain why this data should be erased. Do not include participant names."),
        }),
        label=_("Details"),
        help_text=_("Required. Provide context such as participant request date, retention policy reference, etc."),
    )

    # Acknowledgement checkboxes — all three required
    ack_permanent = forms.BooleanField(
        label=_("I understand all data for this participant will be permanently "
                "anonymised or erased once all program managers approve."),
        required=True,
    )
    ack_authorised = forms.BooleanField(
        label=_("I have verified this erasure request is authorised and documented "
                "(e.g., participant request, retention policy, privacy officer approval)."),
        required=True,
    )
    ack_notify = forms.BooleanField(
        label=_("I understand all program managers will be notified and must "
                "approve before erasure proceeds."),
        required=True,
    )

    def __init__(self, *args, available_tiers=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.available_tiers = available_tiers or {}
        # Mark unavailable tiers in the widget
        if available_tiers:
            disabled_tiers = [
                tier for tier, info in available_tiers.items()
                if not info.get("available", True)
            ]
            if disabled_tiers:
                self.fields["erasure_tier"].widget.attrs["data-disabled-tiers"] = ",".join(disabled_tiers)

    def clean_erasure_tier(self):
        tier = self.cleaned_data["erasure_tier"]
        if self.available_tiers:
            tier_info = self.available_tiers.get(tier, {})
            if not tier_info.get("available", True):
                raise forms.ValidationError(
                    tier_info.get("reason", _("This erasure level is not available."))
                )
        return tier


class ErasureApprovalForm(forms.Form):
    """Form for approving an erasure request (optional notes)."""

    review_notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": _("Optional notes.")}),
        label=_("Review notes"),
        required=False,
    )


class ErasureRejectForm(forms.Form):
    """Form for rejecting an erasure request (notes required)."""

    review_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": _("Explain why this erasure request is being rejected."),
        }),
        label=_("Reason for rejection"),
        help_text=_("Required. This will be visible to the person who requested the erasure."),
    )


class MergeConfirmForm(forms.Form):
    """Confirmation form for merging two client records.

    Dynamic fields are built in __init__ based on the comparison data:
    - pii_{field_name}: RadioSelect for differing PII fields
    - custom_{field_def_id}: RadioSelect for conflicting custom fields
    - primary: which client PK to keep
    - ack_permanent: acknowledgement checkbox
    """

    primary = forms.IntegerField(widget=forms.HiddenInput)

    ack_permanent = forms.BooleanField(
        label=_("I understand this cannot be undone"),
        required=True,
        error_messages={
            "required": _("You must acknowledge that this action cannot be undone."),
        },
    )

    def __init__(self, *args, pii_fields=None, field_conflicts=None,
                 client_a_pk=None, client_b_pk=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Add radio buttons for differing PII fields
        if pii_fields:
            for field_info in pii_fields:
                if not field_info["differs"]:
                    continue
                field_name = f"pii_{field_info['field_name']}"
                self.fields[field_name] = forms.ChoiceField(
                    choices=[
                        (str(client_a_pk), field_info["value_a"] or _("(empty)")),
                        (str(client_b_pk), field_info["value_b"] or _("(empty)")),
                    ],
                    widget=forms.RadioSelect,
                    label=field_info["label"],
                    initial=str(client_a_pk),
                )

        # Add radio buttons for conflicting custom fields
        if field_conflicts:
            for conflict in field_conflicts:
                field_name = f"custom_{conflict['field_def_id']}"
                self.fields[field_name] = forms.ChoiceField(
                    choices=[
                        (str(client_a_pk), conflict["value_a"] or _("(empty)")),
                        (str(client_b_pk), conflict["value_b"] or _("(empty)")),
                    ],
                    widget=forms.RadioSelect,
                    label=conflict["field_name"],
                    initial=str(client_a_pk),
                )
