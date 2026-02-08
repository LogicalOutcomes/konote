"""Program forms."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.auth_app.models import User

from .models import Program, UserProgramRole

# Keywords that suggest a program may handle sensitive/confidential data.
# Used to show a suggestion banner when creating a new program.
CONFIDENTIAL_KEYWORDS = [
    "domestic violence",
    "dv",
    "violence against women",
    "vaw",
    "sexual assault",
    "sexual abuse",
    "crisis",
    "shelter",
    "safe house",
    "safehouse",
    "transition house",
    "hiv",
    "aids",
    "harm reduction",
    "needle exchange",
    "substance use",
    "addiction",
    "mental health",
    "psychiatric",
    "counselling",
    "witness protection",
]


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ["name", "name_fr", "description", "colour_hex", "service_model", "status", "is_confidential"]
        widgets = {
            "colour_hex": forms.TextInput(attrs={"type": "color"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "service_model": _("How do staff record their work?"),
            "is_confidential": _("Yes, this is a confidential program"),
        }
        help_texts = {
            "service_model": _(
                "One-on-one: staff write individual notes and plans for each participant. "
                "Group sessions: staff log sessions with attendance for the whole group. "
                "Both: staff do both."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On creation, require an explicit choice (no pre-selected default)
        if not self.instance.pk:
            self.fields["service_model"].widget = forms.Select(
                choices=[("", _("— Choose one —"))] + list(Program.SERVICE_MODEL_CHOICES),
            )
            self.fields["service_model"].required = True

    def clean_is_confidential(self):
        """Enforce one-way rule: once confidential, cannot be unchecked."""
        new_value = self.cleaned_data.get("is_confidential", False)
        if self.instance and self.instance.pk and self.instance.is_confidential:
            if not new_value:
                raise forms.ValidationError(
                    _("A confidential program cannot be changed back to standard. "
                      "This requires a formal Privacy Impact Assessment.")
                )
        return new_value

    @staticmethod
    def suggest_confidential(program_name):
        """Return True if the program name matches any confidential keywords."""
        name_lower = (program_name or "").lower()
        return any(kw in name_lower for kw in CONFIDENTIAL_KEYWORDS)


class UserProgramRoleForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))
    role = forms.ChoiceField(choices=UserProgramRole.ROLE_CHOICES)

    def __init__(self, *args, program=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.program = program
