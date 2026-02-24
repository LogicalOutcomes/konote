"""Forms for field collection admin configuration."""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ProgramFieldConfig


class ProgramFieldConfigForm(forms.ModelForm):
    """Form for configuring field collection on a single program."""

    class Meta:
        model = ProgramFieldConfig
        fields = ["enabled", "data_tier", "profile"]
        widgets = {
            "enabled": forms.CheckboxInput(),
            "data_tier": forms.Select(attrs={"aria-label": _("Data tier")}),
            "profile": forms.Select(attrs={"aria-label": _("Collection profile")}),
        }
