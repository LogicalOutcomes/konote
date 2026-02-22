"""Plan forms — ModelForms for sections, targets, metrics."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.programs.models import Program

from .models import MetricDefinition, PlanSection, PlanTarget


class PlanSectionForm(forms.ModelForm):
    """Form for creating/editing a plan section."""

    program = forms.ModelChoiceField(
        queryset=Program.objects.filter(status="active"),
        required=False,
        empty_label=_("No program"),
    )

    class Meta:
        model = PlanSection
        fields = ["name", "program", "sort_order"]
        widgets = {
            "sort_order": forms.NumberInput(attrs={"min": 0}),
        }
        labels = {
            "sort_order": _("Display order"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs["placeholder"] = _("Section name")
        self.fields["sort_order"].initial = 0


class PlanSectionStatusForm(forms.ModelForm):
    """Form for changing section status with a reason."""

    class Meta:
        model = PlanSection
        fields = ["status", "status_reason"]
        widgets = {
            "status": forms.Select(choices=PlanSection.STATUS_CHOICES),
            "status_reason": forms.Textarea(attrs={"rows": 3, "placeholder": _("Reason for status change (optional)")}),
        }
        labels = {
            "status_reason": _("Why is this being changed?"),
        }


class PlanTargetForm(forms.Form):
    """Form for creating/editing a plan target.

    name, description, and client_goal are encrypted properties on the model,
    not regular Django fields, so we use a plain Form.
    """

    client_goal = forms.CharField(
        required=False,
        label=_("What does the participant want to work on?"),
        help_text=_("Write what they said, in their own words."),
        widget=forms.TextInput(attrs={"placeholder": _("In their own words…")}),
    )
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": _("Target name")}),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": _("Describe this target")}),
    )

    field_order = ["client_goal", "name", "description"]


class PlanTargetStatusForm(forms.Form):
    """Form for changing target status with a reason.

    status_reason is an encrypted property, so we use a plain Form.
    """

    status = forms.ChoiceField(choices=PlanTarget.STATUS_CHOICES)
    status_reason = forms.CharField(
        required=False,
        label=_("Why is this being changed?"),
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": _("Reason for status change (optional)")}),
    )


class MetricAssignmentForm(forms.Form):
    """Form for assigning a single metric to a target."""

    metrics = forms.ModelChoiceField(
        queryset=MetricDefinition.objects.filter(is_enabled=True, status="active"),
        widget=forms.RadioSelect,
        required=False,
        label=_("Which measurement will best help you both see progress?"),
        help_text=_("Choose the one metric most meaningful to both of you. You can change it later."),
    )


class MetricDefinitionForm(forms.ModelForm):
    """Form for creating/editing a metric definition.

    Pass requesting_user to scope owning_program choices for PMs.
    """

    class Meta:
        model = MetricDefinition
        fields = ["name", "name_fr", "definition", "definition_fr", "category", "min_value", "max_value", "unit", "unit_fr", "owning_program"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Metric name")}),
            "name_fr": forms.TextInput(attrs={"placeholder": _("French metric name (optional)")}),
            "definition": forms.Textarea(attrs={"rows": 4, "placeholder": _("What this metric measures and how to score it")}),
            "definition_fr": forms.Textarea(attrs={"rows": 4, "placeholder": _("French definition (optional)")}),
            "min_value": forms.NumberInput(attrs={"step": "any"}),
            "max_value": forms.NumberInput(attrs={"step": "any"}),
            "unit": forms.TextInput(attrs={"placeholder": _("e.g., score, days, %")}),
            "unit_fr": forms.TextInput(attrs={"placeholder": _("e.g., pointage, jours, %")}),
        }

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if requesting_user and not requesting_user.is_admin:
            from apps.programs.models import Program, UserProgramRole
            pm_program_ids = set(
                UserProgramRole.objects.filter(
                    user=requesting_user, role="program_manager", status="active",
                ).values_list("program_id", flat=True)
            )
            self.fields["owning_program"].queryset = Program.objects.filter(
                pk__in=pm_program_ids, status="active",
            )
            self.fields["owning_program"].empty_label = None
            self.fields["owning_program"].required = True


class GoalForm(forms.Form):
    """Combined goal creation form — section + target + metrics in one step.

    Uses plain Form (not ModelForm) because target name/description/client_goal
    are encrypted properties on the model, not regular Django fields.
    """

    client_goal = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": _("In their own words…"),
        }),
    )
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            "placeholder": _("e.g., Find stable housing"),
            "autocomplete": "off",
        }),
    )
    section_choice = forms.ChoiceField(required=False)
    new_section_name = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            "placeholder": _("New section name"),
        }),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": _("SMART outcome or additional context"),
        }),
    )
    metrics = forms.ModelChoiceField(
        queryset=MetricDefinition.objects.filter(is_enabled=True, status="active"),
        widget=forms.RadioSelect,
        required=False,
        label=_("Which measurement will best help you both see progress?"),
        help_text=_("Choose the one metric most meaningful to both of you. You can change it later."),
    )

    field_order = ["client_goal", "name", "section_choice", "new_section_name",
                   "description", "metrics"]

    def __init__(self, *args, client_file=None, participant_name="", **kwargs):
        super().__init__(*args, **kwargs)

        # Dynamic label with participant name
        if participant_name:
            self.fields["client_goal"].label = (
                _("What does %s want to work on?") % participant_name
            )
        else:
            self.fields["client_goal"].label = _(
                "What does the participant want to work on?"
            )
        self.fields["client_goal"].help_text = _(
            "Write what they said, in their own words."
        )
        self.fields["name"].label = _("Give this goal a short name")
        self.fields["name"].help_text = _("A concise name for this goal.")
        self.fields["section_choice"].label = _(
            "Area of the plan"
        )
        self.fields["description"].label = _("Add more detail (optional)")
        self.fields["metrics"].label = _("How will you measure progress?")
        self.fields["metrics"].help_text = _(
            "You can add or change metrics later too."
        )

        # Populate section choices from client's active sections
        if client_file:
            sections = PlanSection.objects.filter(
                client_file=client_file, status="default",
            ).order_by("sort_order")
            choices = [(str(s.pk), s.name) for s in sections]
            choices.append(("new", _("+ Create new section")))
            self.fields["section_choice"].choices = choices

    def clean(self):
        cleaned = super().clean()
        section_choice = cleaned.get("section_choice", "")
        new_name = cleaned.get("new_section_name", "").strip()

        if section_choice == "new" and not new_name:
            self.add_error(
                "new_section_name",
                _("Please enter a name for the new section."),
            )
        elif not section_choice:
            raise forms.ValidationError(
                _("Please select a section or create a new one.")
            )

        return cleaned


class MetricImportForm(forms.Form):
    """Form for uploading a CSV file of metric definitions."""

    csv_file = forms.FileField(
        label=_("CSV File"),
        help_text=_("Upload a CSV with columns: name, definition, category, min_value, max_value, unit. Optional French columns: name_fr, definition_fr, unit_fr"),
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data["csv_file"]
        if not csv_file.name.endswith(".csv"):
            raise forms.ValidationError(_("File must be a .csv file."))
        if csv_file.size > 1024 * 1024:  # 1MB limit
            raise forms.ValidationError(_("File too large. Maximum size is 1MB."))
        return csv_file
