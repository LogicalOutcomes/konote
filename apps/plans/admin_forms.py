"""Forms for plan template administration (PLAN4)."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.plans.models import PlanTemplate, PlanTemplateSection, PlanTemplateTarget
from apps.auth_app.constants import ROLE_PROGRAM_MANAGER
from apps.programs.models import Program, UserProgramRole


class PlanTemplateForm(forms.ModelForm):
    """Create or edit a plan template.

    Pass requesting_user to scope owning_program choices for PMs.
    """

    class Meta:
        model = PlanTemplate
        fields = ["name", "name_fr", "description", "description_fr", "owning_program", "status"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].help_text = _("The name staff will recognise when choosing this plan template.")
        self.fields["name_fr"].help_text = _("French name, if you want a different label in the French interface.")
        self.fields["description"].help_text = _("Optional summary of when this template should be used.")
        self.fields["description_fr"].help_text = _("French summary, if needed.")
        self.fields["owning_program"].help_text = _("Leave blank to make this template available across the whole organisation. Choose a program to keep it program-specific.")
        self.fields["status"].help_text = _("Archived templates stay on old records but are hidden for new use.")
        if requesting_user and not requesting_user.is_admin:
            # PMs can only assign to their own programs
            pm_program_ids = set(
                UserProgramRole.objects.filter(
                    user=requesting_user, role=ROLE_PROGRAM_MANAGER, status="active",
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
        fields = ["name", "name_fr", "program", "sort_order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].help_text = _("Section heading shown inside the plan, such as Housing or Employment.")
        self.fields["name_fr"].help_text = _("French section heading, if needed.")
        self.fields["program"].help_text = _("Optional. Use this when the section only makes sense for one program.")
        self.fields["sort_order"].help_text = _("Lower numbers appear earlier in the template.")


class PlanTemplateTargetForm(forms.ModelForm):
    """Add or edit a target within a template section."""

    class Meta:
        model = PlanTemplateTarget
        fields = ["name", "name_fr", "description", "description_fr", "sort_order"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].help_text = _("Specific goal staff and participants will work toward inside this section.")
        self.fields["name_fr"].help_text = _("French target name, if needed.")
        self.fields["description"].help_text = _("Optional detail about what success looks like or how the goal should be used.")
        self.fields["description_fr"].help_text = _("French detail, if needed.")
        self.fields["sort_order"].help_text = _("Lower numbers appear earlier within the section.")
