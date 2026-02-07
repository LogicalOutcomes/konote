"""Registration forms."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.clients.models import CustomFieldDefinition, CustomFieldGroup
from apps.clients.validators import (
    normalize_phone_number, validate_phone_number,
)
from apps.programs.models import Program

from .models import RegistrationLink


class RegistrationLinkForm(forms.ModelForm):
    """Form for creating/editing registration links."""

    class Meta:
        model = RegistrationLink
        fields = [
            "program",
            "title",
            "description",
            "field_groups",
            "auto_approve",
            "max_registrations",
            "closes_at",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "closes_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "field_groups": forms.CheckboxSelectMultiple(),
        }
        help_texts = {
            "title": "A descriptive name shown to registrants (e.g., 'Summer Soccer 2025 Registration').",
            "description": "Instructions or information displayed on the registration form.",
            "auto_approve": "If checked, submissions are approved immediately without staff review.",
            "max_registrations": "Leave blank for unlimited registrations.",
            "closes_at": "Leave blank for no deadline.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active, non-confidential programs — registration links
        # cannot be created for confidential programs (safety risk: partner
        # discovers DV intake URL in browser history).
        self.fields["program"].queryset = Program.objects.filter(
            status="active", is_confidential=False,
        )
        # Only show active field groups
        self.fields["field_groups"].queryset = CustomFieldGroup.objects.filter(status="active")


class PublicRegistrationForm(forms.Form):
    """Dynamic form for public registration submissions.

    Builds fields based on the RegistrationLink's configuration.
    """

    # Core fields (always present)
    first_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
    )
    preferred_name = forms.CharField(
        max_length=255,
        required=False,
        label=_("Preferred Name"),
        widget=forms.TextInput(attrs={
            "placeholder": _("What name do you prefer to be called?"),
        }),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    phone = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "tel", "type": "tel"}),
    )

    # Consent checkbox (always required)
    consent = forms.BooleanField(
        required=True,
        label=_("I consent to my information being collected and stored for this registration."),
    )

    def __init__(self, *args, registration_link=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.registration_link = registration_link

        if registration_link:
            # Build custom fields from the link's field groups
            field_groups = registration_link.field_groups.filter(status="active")
            field_definitions = CustomFieldDefinition.objects.filter(
                group__in=field_groups,
                status="active",
            ).order_by("group__sort_order", "sort_order")

            for field_def in field_definitions:
                field_key = f"custom_{field_def.pk}"
                self.fields[field_key] = self._create_field_for_definition(field_def)

    def _create_field_for_definition(self, field_def):
        """Create a form field from a CustomFieldDefinition."""
        common_attrs = {
            "required": field_def.is_required,
            "label": field_def.name,
        }

        if field_def.input_type == "checkbox":
            return forms.BooleanField(**common_attrs, required=False)

        elif field_def.input_type == "number":
            return forms.CharField(
                **common_attrs,
                widget=forms.NumberInput(),
            )

        elif field_def.input_type == "date":
            return forms.DateField(
                **common_attrs,
                widget=forms.DateInput(attrs={"type": "date"}),
            )

        elif field_def.input_type == "select" and field_def.options_json:
            choices = [("", "-- Select --")] + [
                (opt, opt) for opt in field_def.options_json
            ]
            return forms.ChoiceField(
                **common_attrs,
                choices=choices,
            )

        elif field_def.input_type == "textarea":
            return forms.CharField(
                **common_attrs,
                widget=forms.Textarea(attrs={"rows": 3}),
            )

        else:  # Default to text input
            return forms.CharField(
                **common_attrs,
                widget=forms.TextInput(
                    attrs={"placeholder": field_def.placeholder or ""}
                ),
            )

    def clean_phone(self):
        """Validate and normalise the phone number to (XXX) XXX-XXXX format."""
        value = self.cleaned_data.get("phone", "")
        if value:
            validate_phone_number(value)
            value = normalize_phone_number(value)
        return value

    def get_custom_field_values(self):
        """Extract custom field values from cleaned data.

        Returns a dict of {field_def_pk: value} for storage in JSONField.
        """
        values = {}
        for key, value in self.cleaned_data.items():
            if key.startswith("custom_"):
                pk = key.replace("custom_", "")
                values[pk] = value
        return values
