"""Forms for circles — family, household, and support network management."""
import ast
import json

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.admin_settings.models import InstanceSetting


CIRCLE_RELATIONSHIP_CHOICES_SETTING = "circle_relationship_choices"


def _normalise_relationship_choices(values):
    """Return a de-duplicated list of non-empty relationship labels."""
    seen = set()
    normalised = []
    for value in values:
        label = str(value).strip()
        if not label:
            continue
        if label in seen:
            continue
        seen.add(label)
        normalised.append(label)
    return normalised


def get_circle_relationship_choices():
    """Return configured relationship labels for circle memberships.

    The setting accepts any of the following formats:
    - newline-separated text
    - pipe-separated text
    - comma-separated text
    - JSON or Python-style list strings

    Returning an empty list preserves the default shared-product behaviour:
    a free-text relationship field.
    """
    raw_value = (InstanceSetting.get(CIRCLE_RELATIONSHIP_CHOICES_SETTING, "") or "").strip()
    if not raw_value:
        return []

    if raw_value.startswith("["):
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(raw_value)
            except (ValueError, SyntaxError, TypeError, json.JSONDecodeError):
                continue
            if isinstance(parsed, (list, tuple)):
                return _normalise_relationship_choices(parsed)

    if "\n" in raw_value:
        parts = raw_value.splitlines()
    elif "|" in raw_value:
        parts = raw_value.split("|")
    elif "," in raw_value:
        parts = raw_value.split(",")
    else:
        parts = [raw_value]

    return _normalise_relationship_choices(parts)


class CircleForm(forms.Form):
    """Create or edit a circle.

    Plain Form (not ModelForm) because the name field is encrypted
    and can't be handled by Django's ORM field mapping.
    """

    name = forms.CharField(
        max_length=255,
        label=_("Name"),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Garcia Family")}),
    )
    status = forms.ChoiceField(
        choices=[
            ("active", _("Active")),
            ("archived", _("Archived")),
        ],
        initial="active",
        label=_("Status"),
    )


class CircleMembershipForm(forms.Form):
    """Add a member to a circle.

    Supports two modes:
    - Linked participant: client_file is set, member_name is ignored
    - Non-participant: client_file is empty, member_name is required
    """

    client_file = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )
    member_name = forms.CharField(
        max_length=255,
        required=False,
        label=_("Name (non-participant)"),
        help_text=_("For people who are not enrolled as participants."),
    )
    relationship_label = forms.CharField(
        max_length=100,
        required=False,
        label=_("Relationship"),
        help_text=_("Optional — describes this person's role in the circle."),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. parent, spouse, sibling")}),
    )
    is_primary_contact = forms.BooleanField(
        required=False,
        label=_("Primary contact"),
        help_text=_("Who does the agency call first?"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        relationship_choices = get_circle_relationship_choices()
        if relationship_choices:
            self.fields["relationship_label"] = forms.ChoiceField(
                choices=[("", _("— Select —"))] + [
                    (label, label) for label in relationship_choices
                ],
                required=False,
                label=_("Relationship"),
                help_text=_("Optional — choose this person's role in the circle."),
                error_messages={
                    "invalid_choice": _(
                        "Select one of the configured relationship types."
                    ),
                },
            )

    def clean(self):
        cleaned = super().clean()
        client_file = cleaned.get("client_file")
        member_name = cleaned.get("member_name", "").strip()

        if client_file and member_name:
            raise forms.ValidationError(
                _("Choose either a participant or enter a name — not both.")
            )
        if not client_file and not member_name:
            raise forms.ValidationError(
                _("Please select a participant or enter a name.")
            )

        return cleaned
