"""Forms for circles — family, household, and support network management."""
from django import forms
from django.utils.translation import gettext_lazy as _


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
        widget=forms.TextInput(attrs={"placeholder": _("e.g. parent, spouse, sibling")}),
    )
    is_primary_contact = forms.BooleanField(
        required=False,
        label=_("Primary contact"),
        help_text=_("Who does the agency call first?"),
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
