"""Forms for plan template administration (PLAN4)."""
from django import forms

from apps.plans.models import PlanTemplate, PlanTemplateSection, PlanTemplateTarget
from apps.programs.models import Program


class PlanTemplateForm(forms.ModelForm):
    """Create or edit a plan template."""

    class Meta:
        model = PlanTemplate
        fields = ["name", "description", "status"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


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
