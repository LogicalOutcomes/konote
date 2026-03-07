"""Bulk operation forms — wizard-style filter and confirmation."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.programs.models import Program

from .forms import DISCHARGE_REASON_CHOICES


class BulkClientIdsMixin:
    """Shared clean_client_ids for bulk confirm forms."""

    def clean_client_ids(self):
        raw = self.cleaned_data["client_ids"]
        try:
            ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
        except (ValueError, TypeError):
            raise forms.ValidationError(_("Invalid participant selection."))
        if not ids:
            raise forms.ValidationError(_("No participants selected."))
        return ids


class BulkFilterForm(forms.Form):
    """Step 1: Filter participants for a bulk operation."""

    source_program = forms.ModelChoiceField(
        queryset=Program.objects.none(),
        label=_("From program"),
        empty_label=_("— All programs —"),
        required=False,
    )
    status_filter = forms.ChoiceField(
        choices=[
            ("active", _("Active")),
            ("on_hold", _("On Hold")),
            ("all", _("All accessible")),
        ],
        initial="active",
        label=_("Status"),
        required=False,
    )

    def __init__(self, *args, available_programs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if available_programs is not None:
            self.fields["source_program"].queryset = available_programs


class BulkTransferConfirmForm(BulkClientIdsMixin, forms.Form):
    """Step 3: Confirm bulk transfer — destination program + reason."""

    client_ids = forms.CharField(widget=forms.HiddenInput)
    destination_program = forms.ModelChoiceField(
        queryset=Program.objects.none(),
        label=_("Transfer to program"),
        empty_label=_("— Select program —"),
    )
    transfer_reason = forms.CharField(
        required=False,
        label=_("Reason for transfer (optional)"),
        widget=forms.Textarea(attrs={
            "rows": 2,
            "placeholder": _("Why are these participants being transferred?"),
        }),
    )

    def __init__(self, *args, available_programs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if available_programs is not None:
            self.fields["destination_program"].queryset = available_programs


class BulkDischargeConfirmForm(BulkClientIdsMixin, forms.Form):
    """Step 3: Confirm bulk discharge — reason + optional details."""

    client_ids = forms.CharField(widget=forms.HiddenInput)
    source_program = forms.ModelChoiceField(
        queryset=Program.objects.none(),
        widget=forms.HiddenInput,
    )
    end_reason = forms.ChoiceField(
        choices=DISCHARGE_REASON_CHOICES,
        widget=forms.RadioSelect,
        label=_("Reason for discharge"),
    )
    status_reason = forms.CharField(
        required=False,
        label=_("Additional details (optional)"),
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, available_programs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if available_programs is not None:
            self.fields["source_program"].queryset = available_programs
