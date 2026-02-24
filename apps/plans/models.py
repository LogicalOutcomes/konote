"""Plan sections, targets, metrics — the core outcomes tracking models."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field


SELF_EFFICACY_METRIC_NAME = "Self-Efficacy"


class MetricDefinition(models.Model):
    """
    A reusable metric type (e.g., 'PHQ-9 Score', 'Housing Stability').
    Agencies pick from a pre-built library and can add their own.
    """

    CATEGORY_CHOICES = [
        ("mental_health", _("Mental Health")),
        ("housing", _("Housing")),
        ("employment", _("Employment")),
        ("substance_use", _("Substance Use")),
        ("youth", _("Youth")),
        ("general", _("General")),
        ("custom", _("Custom")),
    ]

    METRIC_TYPE_CHOICES = [
        ("scale", _("Numeric scale")),
        ("achievement", _("Achievement")),
    ]

    name = models.CharField(max_length=255)
    name_fr = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_("French name (displayed when language is French)"),
    )
    definition = models.TextField(help_text="What this metric measures and how to score it.")
    definition_fr = models.TextField(
        blank=True, default="",
        help_text=_("French definition (displayed when language is French)"),
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="custom")
    metric_type = models.CharField(
        max_length=20, choices=METRIC_TYPE_CHOICES, default="scale",
        help_text="Scale metrics are recorded as numbers. Achievement metrics use categorical options.",
    )
    higher_is_better = models.BooleanField(
        default=True,
        help_text="False for metrics like PHQ-9 where lower scores indicate improvement.",
    )
    threshold_low = models.FloatField(
        null=True, blank=True,
        help_text="Low band boundary (scale metrics). Values at or below this are in the low band.",
    )
    threshold_high = models.FloatField(
        null=True, blank=True,
        help_text="High band boundary (scale metrics). Values at or above this are in the high band.",
    )
    achievement_options = models.JSONField(
        default=list, blank=True,
        help_text='Dropdown choices for achievement metrics, e.g. ["Employed", "In training", "Unemployed"].',
    )
    achievement_success_values = models.JSONField(
        default=list, blank=True,
        help_text='Which options count as "achieved", e.g. ["Employed"].',
    )
    target_rate = models.FloatField(
        null=True, blank=True,
        help_text="Target percentage for achievement metrics (e.g. 70 means aiming for 70% achieved).",
    )
    target_band_high_pct = models.FloatField(
        null=True, blank=True,
        help_text="Target percentage of participants in the high band (scale metrics).",
    )
    is_library = models.BooleanField(default=False, help_text="Part of the built-in metric library.")
    is_universal = models.BooleanField(default=False, help_text="Universal scale (Goal Progress, Self-Efficacy, Satisfaction) shown prominently during goal creation.")
    is_enabled = models.BooleanField(default=True, help_text="Available for use in this instance.")
    min_value = models.FloatField(null=True, blank=True, help_text="Minimum valid value.")
    max_value = models.FloatField(null=True, blank=True, help_text="Maximum valid value.")
    unit = models.CharField(max_length=50, default="", blank=True, help_text="e.g., 'score', 'days', '%'")
    unit_fr = models.CharField(
        max_length=50, blank=True, default="",
        help_text=_("French unit label (e.g., 'pointage', 'jours', '%')"),
    )
    COMPUTATION_TYPE_CHOICES = [
        ("", _("Manual entry")),
        ("session_count", _("Sessions attended this month")),
    ]
    computation_type = models.CharField(
        max_length=30, blank=True, default="",
        choices=COMPUTATION_TYPE_CHOICES,
        help_text="If set, value is computed automatically instead of manual entry.",
    )
    portal_description = models.TextField(
        blank=True, default="",
        help_text=_(
            "Plain-language explanation shown to participants in the portal. "
            "Describe what the metric measures and what the numbers mean."
        ),
    )
    portal_description_fr = models.TextField(
        blank=True, default="",
        help_text=_("French portal description (displayed when language is French)"),
    )
    portal_visibility = models.CharField(
        max_length=20, default="no",
        choices=[
            ("yes", _("Visible in participant portal")),
            ("no", _("Hidden from participant portal")),
            ("self_reported", _("Only when self-reported")),
        ],
        help_text=_("Visibility in participant portal. Default: hidden until explicitly enabled."),
    )
    owning_program = models.ForeignKey(
        "programs.Program", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="metric_definitions",
        help_text="Program that owns this metric. Null = global (admin-created or library).",
    )
    status = models.CharField(
        max_length=20, default="active",
        choices=[("active", _("Active")), ("deactivated", _("Deactivated"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def translated_name(self):
        """Return French name when active language is French, else English."""
        from django.utils.translation import get_language

        if get_language() == "fr" and self.name_fr:
            return self.name_fr
        return self.name

    @property
    def translated_definition(self):
        """Return French definition when active language is French, else English."""
        from django.utils.translation import get_language

        if get_language() == "fr" and self.definition_fr:
            return self.definition_fr
        return self.definition

    @property
    def translated_unit(self):
        """Return French unit label when active language is French, else English."""
        from django.utils.translation import get_language

        if get_language() == "fr" and self.unit_fr:
            return self.unit_fr
        return self.unit

    @property
    def translated_portal_description(self):
        """Return French portal description when active language is French, else English."""
        from django.utils.translation import get_language

        if get_language() == "fr" and self.portal_description_fr:
            return self.portal_description_fr
        return self.portal_description

    def clean(self):
        super().clean()
        if self.threshold_low is not None and self.threshold_high is not None:
            if self.threshold_low >= self.threshold_high:
                raise ValidationError(
                    {"threshold_high": _("High threshold must be greater than low threshold.")}
                )
        if self.metric_type == "achievement":
            if self.threshold_low is not None or self.threshold_high is not None:
                raise ValidationError(
                    _("Scale thresholds do not apply to achievement metrics.")
                )
        if self.metric_type == "scale":
            if self.achievement_options or self.achievement_success_values:
                raise ValidationError(
                    _("Achievement options do not apply to scale metrics.")
                )

    @property
    def effective_threshold_low(self):
        """Return threshold_low, or calculate from scale range (bottom third)."""
        if self.threshold_low is not None:
            return self.threshold_low
        if self.min_value is not None and self.max_value is not None:
            return self.min_value + (self.max_value - self.min_value) / 3
        return None

    @property
    def effective_threshold_high(self):
        """Return threshold_high, or calculate from scale range (top third)."""
        if self.threshold_high is not None:
            return self.threshold_high
        if self.min_value is not None and self.max_value is not None:
            return self.min_value + 2 * (self.max_value - self.min_value) / 3
        return None

    def classify_band(self, value):
        """Classify a numeric value into band_low, band_mid, or band_high.

        Respects higher_is_better: when False (e.g. PHQ-9), low values
        are "goals within reach" (band_high) and high values are
        "more support needed" (band_low).
        """
        low = self.effective_threshold_low
        high = self.effective_threshold_high
        if low is None or high is None:
            return None

        if self.higher_is_better:
            if value <= low:
                return "band_low"
            elif value >= high:
                return "band_high"
            return "band_mid"
        else:
            # Lower is better (e.g. PHQ-9): high values need more support
            if value >= high:
                return "band_low"
            elif value <= low:
                return "band_high"
            return "band_mid"

    class Meta:
        app_label = "plans"
        db_table = "metric_definitions"
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class PlanSection(models.Model):
    """A section within a client's plan (e.g., 'Social Skills', 'Employment Goals')."""

    STATUS_CHOICES = [
        ("default", _("Active")),
        ("completed", _("Completed")),
        ("deactivated", _("Deactivated")),
    ]

    client_file = models.ForeignKey("clients.ClientFile", on_delete=models.CASCADE, related_name="plan_sections")
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default="default", choices=STATUS_CHOICES)
    status_reason = models.TextField(default="", blank=True)
    program = models.ForeignKey(
        "programs.Program", on_delete=models.SET_NULL, null=True, blank=True, related_name="plan_sections"
    )
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "plans"
        db_table = "plan_sections"
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class PlanTarget(models.Model):
    """
    A specific goal/outcome within a plan section.
    This is the core of the outcomes tracking system.
    """

    STATUS_CHOICES = [
        ("default", _("Active")),
        ("completed", _("Completed")),
        ("deactivated", _("Deactivated")),
    ]

    plan_section = models.ForeignKey(PlanSection, on_delete=models.CASCADE, related_name="targets")
    client_file = models.ForeignKey("clients.ClientFile", on_delete=models.CASCADE, related_name="plan_targets")
    _name_encrypted = models.BinaryField(default=b"", blank=True)
    _description_encrypted = models.BinaryField(default=b"", blank=True)
    status = models.CharField(max_length=20, default="default", choices=STATUS_CHOICES)
    _status_reason_encrypted = models.BinaryField(default=b"", blank=True)
    metrics = models.ManyToManyField(MetricDefinition, through="PlanTargetMetric", blank=True)
    _client_goal_encrypted = models.BinaryField(default=b"", blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def name(self):
        return decrypt_field(self._name_encrypted)

    @name.setter
    def name(self, value):
        self._name_encrypted = encrypt_field(value)

    @property
    def description(self):
        return decrypt_field(self._description_encrypted)

    @description.setter
    def description(self, value):
        self._description_encrypted = encrypt_field(value)

    @property
    def status_reason(self):
        return decrypt_field(self._status_reason_encrypted)

    @status_reason.setter
    def status_reason(self, value):
        self._status_reason_encrypted = encrypt_field(value)

    @property
    def client_goal(self):
        return decrypt_field(self._client_goal_encrypted)

    @client_goal.setter
    def client_goal(self, value):
        self._client_goal_encrypted = encrypt_field(value)

    class Meta:
        app_label = "plans"
        db_table = "plan_targets"
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class PlanTargetRevision(models.Model):
    """Immutable revision history for plan targets."""

    plan_target = models.ForeignKey(PlanTarget, on_delete=models.CASCADE, related_name="revisions")
    _name_encrypted = models.BinaryField(default=b"", blank=True)
    _description_encrypted = models.BinaryField(default=b"", blank=True)
    _client_goal_encrypted = models.BinaryField(default=b"", blank=True)
    status = models.CharField(max_length=20, default="default")
    _status_reason_encrypted = models.BinaryField(default=b"", blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def name(self):
        return decrypt_field(self._name_encrypted)

    @name.setter
    def name(self, value):
        self._name_encrypted = encrypt_field(value)

    @property
    def description(self):
        return decrypt_field(self._description_encrypted)

    @description.setter
    def description(self, value):
        self._description_encrypted = encrypt_field(value)

    @property
    def status_reason(self):
        return decrypt_field(self._status_reason_encrypted)

    @status_reason.setter
    def status_reason(self, value):
        self._status_reason_encrypted = encrypt_field(value)

    @property
    def client_goal(self):
        return decrypt_field(self._client_goal_encrypted)

    @client_goal.setter
    def client_goal(self, value):
        self._client_goal_encrypted = encrypt_field(value)

    class Meta:
        app_label = "plans"
        db_table = "plan_target_revisions"
        ordering = ["-created_at"]

    def __str__(self):
        date_str = self.created_at.strftime("%Y-%m-%d") if self.created_at else "draft"
        return f"{self.name} (rev {date_str})"


class PlanTargetMetric(models.Model):
    """Links a metric definition to a plan target."""

    plan_target = models.ForeignKey(PlanTarget, on_delete=models.CASCADE)
    metric_def = models.ForeignKey(MetricDefinition, on_delete=models.CASCADE)
    sort_order = models.IntegerField(default=0)

    class Meta:
        app_label = "plans"
        db_table = "plan_target_metrics"
        ordering = ["sort_order"]
        unique_together = ["plan_target", "metric_def"]


# Plan templates — reusable plan structures
class PlanTemplate(models.Model):
    """A reusable plan structure that can be applied to new clients."""

    name = models.CharField(max_length=255)
    name_fr = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_("French name (displayed when language is French)"),
    )
    description = models.TextField(default="", blank=True)
    description_fr = models.TextField(
        blank=True, default="",
        help_text=_("French description (displayed when language is French)"),
    )
    owning_program = models.ForeignKey(
        "programs.Program", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="plan_templates",
        help_text="Program that owns this template. Null = global (admin-created).",
    )
    status = models.CharField(
        max_length=20, default="active",
        choices=[("active", _("Active")), ("archived", _("Archived"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def translated_name(self):
        """Return French name when active language is French, else English."""
        from django.utils.translation import get_language

        if get_language() == "fr" and self.name_fr:
            return self.name_fr
        return self.name

    @property
    def translated_description(self):
        """Return French description when active language is French, else English."""
        from django.utils.translation import get_language

        if get_language() == "fr" and self.description_fr:
            return self.description_fr
        return self.description

    class Meta:
        app_label = "plans"
        db_table = "plan_templates"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PlanTemplateSection(models.Model):
    plan_template = models.ForeignKey(PlanTemplate, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=255)
    name_fr = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_("French name (displayed when language is French)"),
    )
    program = models.ForeignKey("programs.Program", on_delete=models.SET_NULL, null=True, blank=True)
    sort_order = models.IntegerField(default=0)

    @property
    def translated_name(self):
        """Return French name when active language is French, else English."""
        from django.utils.translation import get_language

        if get_language() == "fr" and self.name_fr:
            return self.name_fr
        return self.name

    class Meta:
        app_label = "plans"
        db_table = "plan_template_sections"
        ordering = ["sort_order"]


class PlanTemplateTarget(models.Model):
    template_section = models.ForeignKey(PlanTemplateSection, on_delete=models.CASCADE, related_name="targets")
    name = models.CharField(max_length=255)
    name_fr = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_("French name (displayed when language is French)"),
    )
    description = models.TextField(default="", blank=True)
    description_fr = models.TextField(
        blank=True, default="",
        help_text=_("French description (displayed when language is French)"),
    )
    sort_order = models.IntegerField(default=0)

    @property
    def translated_name(self):
        """Return French name when active language is French, else English."""
        from django.utils.translation import get_language

        if get_language() == "fr" and self.name_fr:
            return self.name_fr
        return self.name

    @property
    def translated_description(self):
        """Return French description when active language is French, else English."""
        from django.utils.translation import get_language

        if get_language() == "fr" and self.description_fr:
            return self.description_fr
        return self.description

    class Meta:
        app_label = "plans"
        db_table = "plan_template_targets"
        ordering = ["sort_order"]
