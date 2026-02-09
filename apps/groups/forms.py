"""Group forms for session logging, membership, milestones, and outcomes."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.programs.models import Program

from .models import Group, GroupSession, ProjectMilestone


# ---------------------------------------------------------------------------
# 1. GroupForm (ModelForm)
# ---------------------------------------------------------------------------

class GroupForm(forms.ModelForm):
    """Create or edit a group."""

    class Meta:
        model = Group
        fields = ["name", "group_type", "program", "description"]

    def __init__(self, *args, user_program_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only offer programs that support group sessions
        qs = Program.objects.filter(
            status="active", service_model__in=["group", "both"],
        )
        if user_program_ids is not None:
            qs = qs.filter(pk__in=user_program_ids)
        self.fields["program"].queryset = qs
        self.fields["program"].required = False
        self.fields["program"].empty_label = _("No program")

        # Radio buttons for group type (descriptions rendered in template)
        self.fields["group_type"].widget = forms.RadioSelect(
            choices=Group.GROUP_TYPE_CHOICES,
        )
        self.fields["group_type"].initial = "group"


# ---------------------------------------------------------------------------
# 2. SessionLogForm (plain Form -- notes is encrypted, not a model field)
# ---------------------------------------------------------------------------

class SessionLogForm(forms.Form):
    """Quick session log: date, vibe, and optional notes."""

    session_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("Session date"),
    )
    group_vibe = forms.ChoiceField(
        choices=GroupSession.GROUP_VIBE_CHOICES,
        required=False,
        label=_("Group vibe"),
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label=_("Session notes"),
    )


# ---------------------------------------------------------------------------
# 3. SessionAttendanceForm (dynamic fields per member)
# ---------------------------------------------------------------------------

class SessionAttendanceForm(forms.Form):
    """Dynamic attendance + highlight fields for each group member.

    Creates present_{pk} (BooleanField) and highlight_{pk} (CharField) fields
    for every active membership passed via the ``members`` kwarg.
    """

    def __init__(self, *args, members=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._members = list(members or [])
        for member in self._members:
            self.fields[f"present_{member.pk}"] = forms.BooleanField(
                required=False,
                label=member.display_name,
            )
            self.fields[f"highlight_{member.pk}"] = forms.CharField(
                required=False,
                max_length=500,
                label=_("Highlight for %(name)s") % {"name": member.display_name},
            )

    def get_attendance_data(self):
        """Return list of (membership, present, highlight_notes) tuples."""
        result = []
        for member in self._members:
            present = self.cleaned_data.get(f"present_{member.pk}", False)
            highlight = self.cleaned_data.get(
                f"highlight_{member.pk}", ""
            ).strip()
            result.append((member, present, highlight))
        return result


# ---------------------------------------------------------------------------
# 4. ProjectMilestoneForm (ModelForm)
# ---------------------------------------------------------------------------

class ProjectMilestoneForm(forms.ModelForm):
    """Create or edit a project milestone."""

    class Meta:
        model = ProjectMilestone
        fields = ["title", "status", "due_date", "notes"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }


# ---------------------------------------------------------------------------
# 5. ProjectOutcomeForm (plain Form -- description could be long)
# ---------------------------------------------------------------------------

class ProjectOutcomeForm(forms.Form):
    """Record an outcome for a project-type group."""

    outcome_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("Outcome date"),
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        label=_("Description"),
    )
    evidence = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label=_("Evidence"),
    )


# ---------------------------------------------------------------------------
# 6. MembershipAddForm (plain Form -- conditional validation)
# ---------------------------------------------------------------------------

class MembershipAddForm(forms.Form):
    """Add a member to a group: either an existing client or a named non-client.

    Validates that exactly one of client_file or member_name is provided,
    and that role is one of the allowed choices.
    """

    ROLE_CHOICES = [
        ("member", _("Member")),
        ("leader", _("Leader")),
    ]

    client_file = forms.IntegerField(
        required=False,
        label=_("Participant"),
    )
    member_name = forms.CharField(
        max_length=255,
        required=False,
        label=_("Name"),
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial="member",
        label=_("Role"),
    )

    def clean(self):
        cleaned_data = super().clean()
        client_file = cleaned_data.get("client_file")
        member_name = cleaned_data.get("member_name", "").strip()
        # Store the stripped value back
        cleaned_data["member_name"] = member_name

        if client_file and member_name:
            raise forms.ValidationError(
                _("Please select a participant or enter a name, not both.")
            )
        if not client_file and not member_name:
            raise forms.ValidationError(
                _("Please select a participant or enter a name.")
            )
        return cleaned_data
