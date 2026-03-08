"""Forms for evaluation planning (CIDS Full Tier)."""
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import EvaluationComponent, EvaluationEvidenceLink, EvaluationFramework


class EvaluationFrameworkForm(forms.ModelForm):
    class Meta:
        model = EvaluationFramework
        fields = [
            "name",
            "status",
            "summary",
            "output_summary",
            "outcome_chain_summary",
            "risk_summary",
            "counterfactual_summary",
            "partner_requirements_summary",
        ]
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 4}),
            "output_summary": forms.Textarea(attrs={"rows": 3}),
            "outcome_chain_summary": forms.Textarea(attrs={"rows": 3}),
            "risk_summary": forms.Textarea(attrs={"rows": 3}),
            "counterfactual_summary": forms.Textarea(attrs={"rows": 3}),
            "partner_requirements_summary": forms.Textarea(attrs={"rows": 3}),
        }


class EvaluationComponentForm(forms.ModelForm):
    class Meta:
        model = EvaluationComponent
        fields = [
            "component_type",
            "name",
            "description",
            "sequence_order",
            "parent",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, framework=None, **kwargs):
        super().__init__(*args, **kwargs)
        if framework:
            self.fields["parent"].queryset = EvaluationComponent.objects.filter(
                framework=framework, is_active=True,
            )


class EvaluationEvidenceLinkForm(forms.ModelForm):
    class Meta:
        model = EvaluationEvidenceLink
        fields = [
            "title",
            "source_type",
            "storage_path",
            "external_reference",
            "excerpt_text",
            "contains_pii",
        ]
        widgets = {
            "excerpt_text": forms.Textarea(attrs={"rows": 3}),
        }


class EvaluatorAttestationForm(forms.Form):
    scope = forms.MultipleChoiceField(
        choices=[
            ("impact_model", _("Impact model")),
            ("outcome_measurement", _("Outcome measurement")),
            ("risk_assessment", _("Risk assessment")),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )
    attestation_text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        help_text=_("Optional notes about the attestation scope or limitations."),
    )
