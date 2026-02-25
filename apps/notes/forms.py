"""Forms for progress notes."""
from django import forms
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from apps.plans.models import SELF_EFFICACY_METRIC_NAME
from apps.programs.models import Program, UserProgramRole

from .models import (
    ProgressNote, ProgressNoteTarget, ProgressNoteTemplate,
    ProgressNoteTemplateSection, SuggestionTheme,
)


# Subset for quick notes — group and collateral typically need full notes with target tracking
# Contact types (phone, sms, email) listed first since contact logging is the primary use case
QUICK_INTERACTION_CHOICES = [
    ("phone", _("Phone Call")),
    ("sms", _("Text Message")),
    ("email", _("Email")),
    ("session", _("Session")),
    ("home_visit", _("Home Visit")),
    ("admin", _("Admin")),
    ("other", _("Other")),
]

OUTCOME_CHOICES = [
    ("", _("— Select —")),
    ("reached", _("Reached")),
    ("left_message", _("Left Message")),
    ("no_answer", _("No Answer")),
]

# Interaction types that use the outcome field
CONTACT_TYPES = {"phone", "sms", "email"}


class QuickNoteForm(forms.Form):
    """Form for quick notes — supports both session notes and contact logging."""

    interaction_type = forms.ChoiceField(
        choices=QUICK_INTERACTION_CHOICES,
        widget=forms.RadioSelect,
        label=_("What kind of interaction?"),
    )
    outcome = forms.ChoiceField(
        choices=OUTCOME_CHOICES,
        required=False,
        label=_("Outcome"),
    )
    notes_text = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": _("Write your note here..."),
            # ID must match the error container in quick_note_form.html.
            # Explicit here because this form uses <div> not <small class="error">,
            # so the app.js auto-linker does not apply.
            "aria-describedby": "notes-text-errors",
        }),
        required=False,
    )
    follow_up_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "data-followup-picker": "true"}),
        required=False,
        label=_("Follow up by"),
        help_text=_("(optional — adds to your home page reminders)"),
    )

    def __init__(self, *args, circle_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if circle_choices:
            self.fields["circle"] = forms.ChoiceField(
                choices=[("", _("— None —"))] + list(circle_choices),
                required=False,
                label=_("Circle"),
                help_text=_("Circle notes should describe shared observations, not clinical details about specific individuals."),
            )
            # Auto-select when participant belongs to exactly one circle
            if len(circle_choices) == 1:
                self.fields["circle"].initial = circle_choices[0][0]

    def clean(self):
        cleaned = super().clean()
        interaction = cleaned.get("interaction_type", "")
        outcome = cleaned.get("outcome", "")
        notes = cleaned.get("notes_text", "").strip()

        if interaction in CONTACT_TYPES:
            # Outcome is required for contact types
            if not outcome:
                self.add_error("outcome", _("Please select an outcome."))
            # For unsuccessful contacts, auto-fill notes if blank
            if outcome in ("no_answer", "left_message") and not notes:
                cleaned["notes_text"] = dict(OUTCOME_CHOICES).get(outcome, outcome)
            # For reached contacts, notes are required
            elif outcome == "reached" and not notes:
                self.add_error("notes_text", _("Note text is required."))
        else:
            # Clear outcome for non-contact types
            cleaned["outcome"] = ""
            # Notes always required for non-contact types
            if not notes:
                self.add_error("notes_text", _("Note text is required."))

        return cleaned


class _TemplateChoiceField(forms.ModelChoiceField):
    """ModelChoiceField that shows section count next to template name."""

    def label_from_instance(self, obj):
        count = getattr(obj, "_section_count", None)
        if count is None:
            count = obj.sections.count()
        label = obj.translated_name
        if count:
            label += " (%d)" % count
        return label


class FullNoteForm(forms.Form):
    """Top-level form for a full structured progress note."""

    template = _TemplateChoiceField(
        queryset=ProgressNoteTemplate.objects.filter(status="active").annotate(
            _section_count=Count("sections"),
        ),
        required=False,
        label=_("This note is for..."),
        empty_label=_("Freeform"),
    )
    interaction_type = forms.ChoiceField(
        choices=ProgressNote.INTERACTION_TYPE_CHOICES,
        label=_("Interaction type"),
    )
    session_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        help_text=_("Change if this note is for a different day."),
    )
    duration_minutes = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=1440,
        label=_("Duration (minutes)"),
        help_text=_("Optional \u2014 for session reporting"),
        widget=forms.NumberInput(attrs={"placeholder": _("e.g. 60"), "min": "1", "max": "1440"}),
    )
    modality = forms.ChoiceField(
        choices=[("", _("\u2014 Select \u2014"))] + list(ProgressNote.MODALITY_CHOICES),
        required=False,
        label=_("Session modality"),
        help_text=_("Optional \u2014 for session reporting"),
    )
    summary = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": _("Optional summary...")}),
        required=False,
    )
    follow_up_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "data-followup-picker": "true"}),
        required=False,
        label=_("Follow up by"),
        help_text=_("(optional — adds to your home page reminders)"),
    )
    engagement_observation = forms.ChoiceField(
        choices=ProgressNote.ENGAGEMENT_CHOICES,
        required=False,
        label=_("Engagement"),
        widget=forms.RadioSelect,
        help_text=_("Your observation, not a score."),
    )
    alliance_rating = forms.TypedChoiceField(
        choices=[("", "")] + list(ProgressNote.ALLIANCE_RATING_CHOICES),
        required=False,
        coerce=int,
        empty_value=None,
        label=_("Working relationship check-in"),
        widget=forms.RadioSelect,
    )
    alliance_rater = forms.ChoiceField(
        choices=[("", "")] + list(ProgressNote.ALLIANCE_RATER_CHOICES),
        required=False,
        label=_("Who rated?"),
        widget=forms.RadioSelect,
        initial="client",
    )
    participant_reflection = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 2,
            "placeholder": _("Their words..."),
        }),
        required=False,
        label=_("How did they feel about today's session?"),
        help_text=_("Record their words, not your interpretation."),
    )
    participant_suggestion = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 2,
            "placeholder": _('e.g. "Tea is always cold" or "Loves the Friday group" or "Wishes sessions were longer"'),
        }),
        required=False,
        label=_("Anything they'd change about the program?"),
    )
    suggestion_priority = forms.ChoiceField(
        choices=ProgressNote.SUGGESTION_PRIORITY_CHOICES,
        required=False,
        label=_("Priority"),
    )

    def __init__(self, *args, circle_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if circle_choices:
            self.fields["circle"] = forms.ChoiceField(
                choices=[("", _("— None —"))] + list(circle_choices),
                required=False,
                label=_("Circle"),
                help_text=_("Circle notes should describe shared observations, not clinical details about specific individuals."),
            )
            # Auto-select when participant belongs to exactly one circle
            if len(circle_choices) == 1:
                self.fields["circle"].initial = circle_choices[0][0]


class TargetNoteForm(forms.Form):
    """Notes for a single plan target within a full note."""

    target_id = forms.IntegerField(widget=forms.HiddenInput())
    client_words = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": _("What did they say about this goal?")}),
        required=False,
        label=_("What did they say about this?"),
        help_text=_("What did they say about this goal?"),
    )
    progress_descriptor = forms.ChoiceField(
        choices=ProgressNoteTarget.PROGRESS_DESCRIPTOR_CHOICES,
        required=False,
        label=_("How are things going?"),
        widget=forms.RadioSelect,
        help_text=_("Harder isn't always backwards — progress often makes things harder first."),
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": _("Your notes for this target...")}),
        required=False,
    )


class MetricValueForm(forms.Form):
    """A single metric value input."""

    metric_def_id = forms.IntegerField(widget=forms.HiddenInput())
    value = forms.CharField(required=False, max_length=100)
    is_scale = False
    is_achievement = False
    auto_calc_value = None

    def __init__(self, *args, metric_def=None, target_name="", **kwargs):
        super().__init__(*args, **kwargs)
        self.target_name = target_name
        if metric_def:
            self.metric_def = metric_def
            label = metric_def.translated_name
            if metric_def.translated_unit:
                label += f" ({metric_def.translated_unit})"
            self.fields["value"].label = label
            # Domain-specific prompt for Self-Efficacy
            if metric_def.name == SELF_EFFICACY_METRIC_NAME and target_name:
                from django.utils.translation import gettext
                self.fields["value"].label = gettext(
                    "How sure do you feel about being able to %(target)s?"
                ) % {"target": target_name.lower()}
            # Set help text from definition
            help_parts = []
            if metric_def.translated_definition:
                help_parts.append(metric_def.translated_definition)
            if metric_def.min_value is not None or metric_def.max_value is not None:
                range_str = _("Range: ")
                if metric_def.min_value is not None:
                    range_str += str(metric_def.min_value)
                range_str += " – "
                if metric_def.max_value is not None:
                    range_str += str(metric_def.max_value)
                help_parts.append(range_str)
            self.fields["value"].help_text = " | ".join(help_parts)

            # Achievement metrics: render as radio pills with option labels
            if metric_def.metric_type == "achievement" and metric_def.achievement_options:
                choices = [("", "---------")] + [
                    (opt, opt) for opt in metric_def.achievement_options
                ]
                self.fields["value"].widget = forms.RadioSelect(
                    choices=choices,
                    attrs={
                        "class": "achievement-pills-input",
                        "aria-label": f"{metric_def.translated_name}: {metric_def.translated_definition}",
                    },
                )
                self.is_achievement = True
                # Override help text — don't show range for achievements
                self.fields["value"].help_text = metric_def.translated_definition or ""
            else:
                # Detect scale metrics: both min/max set, both integers, small range
                is_scale = (
                    metric_def.min_value is not None
                    and metric_def.max_value is not None
                    and metric_def.min_value == int(metric_def.min_value)
                    and metric_def.max_value == int(metric_def.max_value)
                    and (metric_def.max_value - metric_def.min_value) <= 10
                )

                if is_scale:
                    low = int(metric_def.min_value)
                    high = int(metric_def.max_value)
                    choices = [("", "---------")] + [
                        (str(i), str(i)) for i in range(low, high + 1)
                    ]
                    self.fields["value"].widget = forms.RadioSelect(
                        choices=choices,
                        attrs={
                            "class": "scale-pills-input",
                            "aria-label": f"{metric_def.translated_name}: {metric_def.translated_definition}",
                        },
                    )
                    self.is_scale = True
                else:
                    # Standard number input for wide-range metrics
                    attrs = {}
                    if metric_def.min_value is not None:
                        attrs["min"] = metric_def.min_value
                    if metric_def.max_value is not None:
                        attrs["max"] = metric_def.max_value
                    if attrs:
                        attrs["type"] = "number"
                        attrs["step"] = "any"
                        self.fields["value"].widget = forms.NumberInput(attrs=attrs)
                    self.is_scale = False

    def clean_value(self):
        val = self.cleaned_data.get("value", "").strip()
        if not val:
            return ""
        if hasattr(self, "metric_def"):
            # Achievement metrics: validate option is in the allowed list
            if self.metric_def.metric_type == "achievement":
                valid_options = self.metric_def.achievement_options or []
                if val not in valid_options:
                    raise forms.ValidationError(_("Invalid option selected."))
                return val
            # Scale/numeric metrics: validate against min/max
            try:
                numeric = float(val)
            except ValueError:
                raise forms.ValidationError(_("Enter a valid number."))
            if self.metric_def.min_value is not None and numeric < self.metric_def.min_value:
                raise forms.ValidationError(
                    _("Value must be at least %(min_value)s.") % {"min_value": self.metric_def.min_value}
                )
            if self.metric_def.max_value is not None and numeric > self.metric_def.max_value:
                raise forms.ValidationError(
                    _("Value must be at most %(max_value)s.") % {"max_value": self.metric_def.max_value}
                )
        return val


class NoteTemplateForm(forms.ModelForm):
    """Form for creating/editing progress note templates.

    Pass requesting_user to scope owning_program choices for PMs.
    """

    class Meta:
        model = ProgressNoteTemplate
        fields = ["name", "name_fr", "default_interaction_type", "owning_program", "status"]

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if requesting_user and not requesting_user.is_admin:
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


class NoteTemplateSectionForm(forms.ModelForm):
    """Form for a section within a note template."""

    class Meta:
        model = ProgressNoteTemplateSection
        fields = ["name", "name_fr", "section_type", "sort_order"]


class NoteCancelForm(forms.Form):
    """Form for cancelling a progress note."""

    status_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": _("Reason for cancellation...")}),
        label=_("Reason"),
    )


class SuggestionThemeForm(forms.ModelForm):
    """Create or edit a SuggestionTheme (kept for backward compat with tests).

    In the automated design, themes are created by AI — not by users.
    This form is only used for manual theme creation if needed.
    """

    class Meta:
        model = SuggestionTheme
        fields = ["name", "program", "description", "status", "addressed_note"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": _("Optional context about this theme...")}),
            "addressed_note": forms.Textarea(attrs={"rows": 3, "placeholder": _("What was done about it?")}),
        }
        labels = {
            "name": _("Theme name"),
            "program": _("Program"),
            "description": _("Description"),
            "status": _("Status"),
            "addressed_note": _("Resolution notes"),
        }

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if requesting_user and not getattr(requesting_user, "is_admin", False):
            from apps.programs.access import get_accessible_programs
            self.fields["program"].queryset = get_accessible_programs(requesting_user)
        self.fields["addressed_note"].required = False

    def clean_name(self):
        name = self.cleaned_data.get("name", "")
        # Normalise: strip and collapse internal whitespace
        name = " ".join(name.split())
        return name

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name", "")
        program = cleaned.get("program")
        if name and program:
            qs = SuggestionTheme.objects.filter(
                program=program, name__iexact=name,
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    _("A theme called \"%(name)s\" already exists in this program.")
                    % {"name": name}
                )
        return cleaned


class SuggestionThemeStatusForm(forms.ModelForm):
    """Inline status update for a suggestion theme.

    Used on the Insights page and theme detail page to let PMs
    mark themes as in-progress, addressed, or won't-do.
    """

    class Meta:
        model = SuggestionTheme
        fields = ["status", "addressed_note"]
        widgets = {
            "addressed_note": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": _("What was done about it?"),
            }),
        }
        labels = {
            "status": _("Status"),
            "addressed_note": _("Resolution notes"),
        }
