"""Forms for the taxonomy review workflow."""
from django import forms

from apps.admin_settings.models import TaxonomyMapping
from apps.admin_settings.taxonomy_review import SUBJECT_TYPES, get_taxonomy_list_choices


class TaxonomyBatchSuggestForm(forms.Form):
    subject_type = forms.ChoiceField(choices=SUBJECT_TYPES)
    taxonomy_list_name = forms.ChoiceField(choices=[])
    max_items = forms.IntegerField(min_value=1, max_value=250, initial=25)
    max_suggestions = forms.IntegerField(min_value=1, max_value=5, initial=3)
    only_unmapped = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["taxonomy_list_name"].choices = get_taxonomy_list_choices()


class TaxonomyQueueFilterForm(forms.Form):
    mapping_status = forms.ChoiceField(required=False, choices=[])
    taxonomy_system = forms.ChoiceField(required=False, choices=[])
    taxonomy_list_name = forms.ChoiceField(required=False, choices=[])
    subject_type = forms.ChoiceField(required=False, choices=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mapping_status"].choices = [("", "All statuses")] + list(TaxonomyMapping.MAPPING_STATUSES)
        self.fields["taxonomy_system"].choices = [("", "All taxonomies")] + list(TaxonomyMapping.TAXONOMY_SYSTEMS)
        self.fields["taxonomy_list_name"].choices = [("", "All code lists")] + get_taxonomy_list_choices()
        self.fields["subject_type"].choices = [("", "All item types")] + SUBJECT_TYPES


class TaxonomyBulkActionForm(forms.Form):
    ACTION_CHOICES = [
        ("approve", "Approve selected"),
        ("reject", "Reject selected"),
    ]

    action = forms.ChoiceField(choices=ACTION_CHOICES)
    mapping_ids = forms.CharField(widget=forms.HiddenInput())

    def clean_mapping_ids(self):
        raw_value = self.cleaned_data["mapping_ids"]
        ids = []
        for part in str(raw_value or "").split(","):
            part = part.strip()
            if not part:
                continue
            try:
                ids.append(int(part))
            except ValueError as exc:
                raise forms.ValidationError("Invalid selection.") from exc
        if not ids:
            raise forms.ValidationError("Select at least one mapping.")
        return ids


class TaxonomyQuestionForm(forms.Form):
    question = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))


class TaxonomyManualSearchForm(forms.Form):
    query = forms.CharField(required=False, max_length=100)


class TaxonomyManualPickForm(forms.Form):
    code = forms.CharField(max_length=100)


class TaxonomyReclassifyForm(forms.Form):
    taxonomy_list_name = forms.ChoiceField(choices=[])
    max_suggestions = forms.IntegerField(min_value=1, max_value=5, initial=3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["taxonomy_list_name"].choices = get_taxonomy_list_choices()
