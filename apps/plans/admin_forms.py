"""Forms for plan template administration (PLAN4)."""
from django import forms

from apps.plans.models import PlanTemplate, PlanTemplateSection, PlanTemplateTarget
from apps.programs.models import Program, UserProgramRole


class PlanTemplateForm(forms.ModelForm):
    """Create or edit a plan template.

    Pass requesting_user to scope owning_program choices for PMs.
    """

    class Meta:
        model = PlanTemplate
        fields = ["name", "description", "owning_program", "status"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if requesting_user and not requesting_user.is_admin:
            # PMs can only assign to their own programs
            pm_program_ids = set(
                UserProgramRole.objects.filter(
                    user=requesting_user, role="program_manager", status="active",
                ).values_list("program_id", flat=True)
            )
            self.fields["owning_program"].queryset = Program.objects.filter(
                pk__in=pm_program_ids, status="active",
            )
            self.fields["owning_program"].empty_label = None  # Must pick a program
            self.fields["owning_program"].required = True


class PlanTemplateSectionForm(forms.ModelForm):
    """Add or edit a section within a plan template."""

    program = forms.ModelChoiceField(
        queryset=Program.objects.filter(status="active"),
        required=False,
        empty_label="— No program —",
    )

    class Meta:
        model = PlanTemplateSection
        fields = ["name", "program", "sort_order"]


class PlanTemplateTargetForm(forms.ModelForm):
    """Add or edit a target within a template section."""

    class Meta:
        model = PlanTemplateTarget
        fields = ["name", "description", "sort_order"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
