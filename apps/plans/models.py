"""Plan sections, targets, metrics — the core outcomes tracking models."""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field


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

    name = models.CharField(max_length=255)
    definition = models.TextField(help_text="What this metric measures and how to score it.")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="custom")
    is_library = models.BooleanField(default=False, help_text="Part of the built-in metric library.")
    is_enabled = models.BooleanField(default=True, help_text="Available for use in this instance.")
    min_value = models.FloatField(null=True, blank=True, help_text="Minimum valid value.")
    max_value = models.FloatField(null=True, blank=True, help_text="Maximum valid value.")
    unit = models.CharField(max_length=50, default="", blank=True, help_text="e.g., 'score', 'days', '%'")
    portal_visibility = models.CharField(
        max_length=20, default="no",
        choices=[
            ("yes", _("Visible in participant portal")),
            ("no", _("Hidden from participant portal")),
            ("self_reported", _("Only when self-reported")),
        ],
        help_text=_("Visibility in participant portal. Default: hidden until explicitly enabled."),
    )
    status = models.CharField(
        max_length=20, default="active",
        choices=[("active", _("Active")), ("deactivated", _("Deactivated"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)

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
    description = models.TextField(default="", blank=True)
    status = models.CharField(
        max_length=20, default="active",
        choices=[("active", _("Active")), ("archived", _("Archived"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "plans"
        db_table = "plan_templates"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PlanTemplateSection(models.Model):
    plan_template = models.ForeignKey(PlanTemplate, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=255)
    program = models.ForeignKey("programs.Program", on_delete=models.SET_NULL, null=True, blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        app_label = "plans"
        db_table = "plan_template_sections"
        ordering = ["sort_order"]


class PlanTemplateTarget(models.Model):
    template_section = models.ForeignKey(PlanTemplateSection, on_delete=models.CASCADE, related_name="targets")
    name = models.CharField(max_length=255)
    description = models.TextField(default="", blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        app_label = "plans"
        db_table = "plan_template_targets"
        ordering = ["sort_order"]
