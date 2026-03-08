"""Plan forms — ModelForms for sections, targets, metrics."""
import json

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.auth_app.constants import ROLE_PROGRAM_MANAGER
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
    Includes CIDS metadata fields with dropdowns populated from CidsCodeList.
    """

    class Meta:
        model = MetricDefinition
        fields = [
            "name", "name_fr", "definition", "definition_fr", "category",
            "metric_type", "min_value", "max_value", "warn_min", "warn_max",
            "unit", "unit_fr",
            "higher_is_better", "threshold_low", "threshold_high",
            "achievement_options", "achievement_success_values",
            "target_rate", "target_band_high_pct",
            "cadence_sessions",
            "owning_program",
            # Assessment fields
            "is_standardized_instrument",
            "assessment_at_intake", "assessment_at_discharge",
            "assessment_interval_days",
            # CIDS metadata fields
            "iris_metric_code", "sdg_goals",
            "cids_indicator_uri", "cids_unit_description",
            "cids_defined_by", "cids_has_baseline", "cids_theme_override",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Metric name")}),
            "name_fr": forms.TextInput(attrs={"placeholder": _("French metric name (optional)")}),
            "definition": forms.Textarea(attrs={"rows": 4, "placeholder": _("What this metric measures and how to score it")}),
            "definition_fr": forms.Textarea(attrs={"rows": 4, "placeholder": _("French definition (optional)")}),
            "min_value": forms.NumberInput(attrs={"step": "any"}),
            "max_value": forms.NumberInput(attrs={"step": "any"}),
            "unit": forms.TextInput(attrs={"placeholder": _("e.g., score, days, %")}),
            "unit_fr": forms.TextInput(attrs={"placeholder": _("e.g., pointage, jours, %")}),
            "warn_min": forms.NumberInput(attrs={"step": "any"}),
            "warn_max": forms.NumberInput(attrs={"step": "any"}),
            "cadence_sessions": forms.NumberInput(attrs={"min": "1", "max": "99"}),
            "threshold_low": forms.NumberInput(attrs={"step": "any"}),
            "threshold_high": forms.NumberInput(attrs={"step": "any"}),
            "target_rate": forms.NumberInput(attrs={"step": "any", "min": "0", "max": "100"}),
            "target_band_high_pct": forms.NumberInput(attrs={"step": "any", "min": "0", "max": "100"}),
            "achievement_options": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": _('e.g. ["Employed", "In training", "Unemployed"]'),
            }),
            "achievement_success_values": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": _('e.g. ["Employed"]'),
            }),
        }

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Help text for non-technical admins
        self.fields["name"].help_text = _("The name shown when staff select this metric for a goal.")
        self.fields["name_fr"].help_text = _("French name, shown when a user's language is French. Leave blank to use the English name.")
        self.fields["definition"].help_text = _("Describe what this metric measures and how to score it. Shown to staff during note entry.")
        self.fields["definition_fr"].help_text = _("French definition. Leave blank to use the English definition.")
        self.fields["category"].help_text = _("Used to group similar metrics together in the library.")
        self.fields["metric_type"].help_text = _("Scale = a numeric score. Achievement = named outcomes such as employed or housed. Open text = narrative only.")
        self.fields["min_value"].help_text = _("Usual minimum score for this metric.")
        self.fields["max_value"].help_text = _("Usual maximum score for this metric.")
        self.fields["higher_is_better"].help_text = _("Uncheck for metrics where lower scores indicate improvement (e.g. PHQ-9 depression scale).")
        self.fields["warn_min"].help_text = _("Optional soft warning minimum. Staff can still save lower values, but KoNote will ask them to confirm the score.")
        self.fields["warn_max"].help_text = _("Optional soft warning maximum. Staff can still save higher values, but KoNote will ask them to confirm the score.")
        self.fields["cadence_sessions"].label = _("Recording cadence (sessions)")
        self.fields["cadence_sessions"].help_text = _("How many sessions between prompts for this metric. Leave blank to prompt every session.")
        self.fields["threshold_low"].help_text = _("Optional reporting threshold for the low end of the target range.")
        self.fields["threshold_high"].help_text = _("Optional reporting threshold for the high end of the target range.")
        self.fields["achievement_options"].help_text = _("For achievement metrics, list the answer choices staff can select.")
        self.fields["achievement_success_values"].help_text = _("Which of the achievement options count as success in reports.")
        self.fields["target_rate"].help_text = _("Optional target percentage used for reporting or dashboards.")
        self.fields["target_band_high_pct"].help_text = _("Optional upper bound for the target percentage band.")
        self.fields["owning_program"].help_text = _("Leave blank to make this metric available organisation-wide. Choose a program to keep it program-specific.")
        # Assessment fields
        self.fields["is_standardized_instrument"].help_text = _("Check if this is a published, validated instrument (e.g. PHQ-9, GAD-7).")
        self.fields["assessment_at_intake"].help_text = _("Administer this assessment at intake (first session).")
        self.fields["assessment_at_discharge"].help_text = _("Administer this assessment at discharge.")
        self.fields["assessment_interval_days"].label = _("Assessment interval (days)")
        self.fields["assessment_interval_days"].help_text = _("Days between scheduled administrations (e.g. 90 for quarterly). Leave blank for no schedule.")
        self.fields["iris_metric_code"].help_text = _("Optional external IRIS+ mapping. Usually reviewed later by an admin or reporting lead unless you already know the exact code.")
        self.fields["sdg_goals"].help_text = _("Optional reporting classification. Usually assigned later during reporting review, not required when creating the metric.")
        self.fields["cids_indicator_uri"].help_text = _("Stable identifier for this metric in CIDS exports. KoNote will create a local one automatically if you leave this blank.")
        self.fields["cids_unit_description"].help_text = _("Human-readable unit label for export. KoNote usually copies this from the plain-language unit automatically.")
        self.fields["cids_defined_by"].help_text = _("Who defined this indicator. KoNote fills this automatically unless you need to record a known external source.")
        self.fields["cids_has_baseline"].help_text = _("Optional baseline wording for reporting. This is usually added later, once reporting definitions are settled.")
        self.fields["cids_theme_override"].help_text = _("Optional reporting override when later classification needs a different theme. Usually left blank at creation time.")

        if requesting_user and not requesting_user.is_admin:
            from apps.programs.models import Program, UserProgramRole
            pm_program_ids = set(
                UserProgramRole.objects.filter(
                    user=requesting_user, role=ROLE_PROGRAM_MANAGER, status="active",
                ).values_list("program_id", flat=True)
            )
            self.fields["owning_program"].queryset = Program.objects.filter(
                pk__in=pm_program_ids, status="active",
            )
            self.fields["owning_program"].empty_label = None
            self.fields["owning_program"].required = True

        # Populate CIDS dropdowns from CidsCodeList (if imported)
        self._populate_cids_choices()

    def _populate_cids_choices(self):
        """Populate CIDS dropdown fields from CidsCodeList entries.

        Gracefully handles missing table (e.g. during early migrations)
        by falling back to static choices.
        """
        from django.db.utils import OperationalError, ProgrammingError
        from apps.admin_settings.models import CidsCodeList

        try:
            # iris_metric_code → Select from IrisMetric53
            iris_choices = [("", _("— None —"))]
            iris_entries = CidsCodeList.objects.filter(
                list_name="IrisMetric53",
            ).order_by("code")
            iris_choices += [(e.code, f"{e.code} — {e.label}") for e in iris_entries]
            self.fields["iris_metric_code"].widget = forms.Select(choices=iris_choices)

            # sdg_goals → Replace JSONField form field with MultipleChoiceField
            # so CheckboxSelectMultiple works correctly (JSONField expects a JSON
            # string but checkboxes submit a list of values).
            sdg_choices = []
            sdg_entries = CidsCodeList.objects.filter(
                list_name="SDGImpacts",
            ).order_by("code")
            if sdg_entries.exists():
                sdg_choices = [(e.code, f"SDG {e.code}: {e.label}") for e in sdg_entries]
            else:
                sdg_choices = [(str(i), f"SDG {i}") for i in range(1, 18)]
        except (OperationalError, ProgrammingError):
            # Table doesn't exist yet (early migration or fresh test DB)
            self.fields["iris_metric_code"].widget = forms.Select(
                choices=[("", _("— None —"))],
            )
            sdg_choices = [(str(i), f"SDG {i}") for i in range(1, 18)]

        self.fields["sdg_goals"] = forms.TypedMultipleChoiceField(
            choices=sdg_choices,
            widget=forms.CheckboxSelectMultiple,
            required=False,
            coerce=str,
            label=_("SDG Goals"),
        )
        # Set initial value: convert ints to strings for the widget
        if self.instance and self.instance.pk and self.instance.sdg_goals:
            self.initial["sdg_goals"] = [str(g) for g in self.instance.sdg_goals]

    def clean_sdg_goals(self):
        """Convert multi-select string values to a list of integers."""
        value = self.cleaned_data.get("sdg_goals")
        if not value:
            return []
        if isinstance(value, list):
            try:
                return [int(v) for v in value]
            except (ValueError, TypeError):
                raise forms.ValidationError(_("SDG goals must be numbers 1–17."))
        return value

    def _clean_json_list_field(self, field_name):
        """Validate that a field contains a JSON list (or is empty)."""
        value = self.cleaned_data.get(field_name)
        if not value:
            return []
        if isinstance(value, list):
            return value
        # If it's a string (from Textarea), try to parse it
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            try:
                parsed = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                raise forms.ValidationError(
                    _('Please enter a valid JSON list, e.g. ["Option 1", "Option 2"].')
                )
            if not isinstance(parsed, list):
                raise forms.ValidationError(
                    _("This field must be a list, e.g. [\"Option 1\", \"Option 2\"].")
                )
            return parsed
        return value

    def clean_achievement_options(self):
        return self._clean_json_list_field("achievement_options")

    def clean_achievement_success_values(self):
        return self._clean_json_list_field("achievement_success_values")


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
        error_messages={"required": _("Please give this goal a short name.")},
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

    field_order = ["client_goal", "name", "description", "metrics",
                   "section_choice", "new_section_name"]

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
        # R9: Order by most recently created so the default is the newest section
        if client_file:
            sections = PlanSection.objects.filter(
                client_file=client_file, status="default",
            ).order_by("-pk")
            choices = [(str(s.pk), s.name) for s in sections]
            choices.append(("new", _("+ Create new section")))
            self.fields["section_choice"].choices = choices

    def clean(self):
        cleaned = super().clean()
        section_choice = cleaned.get("section_choice", "")
        new_name = cleaned.get("new_section_name", "").strip()

        # R9: If "new" chosen but no name given, default to "General"
        if section_choice == "new" and not new_name:
            cleaned["new_section_name"] = str(_("General"))
        elif not section_choice:
            raise forms.ValidationError(
                _("Please choose which area of the plan this goal belongs to.")
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
