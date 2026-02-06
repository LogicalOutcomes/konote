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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["program"].queryset = Program.objects.filter(status="active")
        self.fields["program"].required = False
        self.fields["program"].empty_label = _("No programme")


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
# 3. HighlightForm (plain Form)
# ---------------------------------------------------------------------------

class HighlightForm(forms.Form):
    """Per-member observation during a session."""

    membership_id = forms.IntegerField(widget=forms.HiddenInput)
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label=_("Observation"),
    )


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
