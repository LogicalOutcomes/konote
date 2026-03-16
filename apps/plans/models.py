"""Plan sections, targets, metrics — the core outcomes tracking models."""
import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field, DecryptionError


SELF_EFFICACY_METRIC_NAME = "Self-Efficacy"


class MetricDefinition(models.Model):
    """
    A reusable metric type (e.g., 'PHQ-9 Score', 'Housing Stability').
    Agencies pick from a pre-built library and can add their own.
    """

    METRIC_TYPE_CHOICES = [
        ("scale", _("Numeric scale")),
        ("achievement", _("Achievement")),
        ("open_text", _("Open text")),
    ]

    CATEGORY_CHOICES = [
        ("mental_health", _("Mental Health")),
        ("housing", _("Housing")),
        ("employment", _("Employment")),
        ("substance_use", _("Substance Use")),
        ("youth", _("Youth")),
        ("general", _("General")),
        ("client_experience", _("Client Experience")),
        ("custom", _("Custom")),
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
    is_library = models.BooleanField(default=False, help_text="Part of the built-in metric library.")
    is_universal = models.BooleanField(default=False, help_text="Universal scale (Goal Progress, Self-Efficacy, Satisfaction) shown prominently during goal creation.")
    is_enabled = models.BooleanField(default=True, help_text="Available for use in this instance.")
    min_value = models.FloatField(null=True, blank=True, help_text="Minimum valid value.")
    max_value = models.FloatField(null=True, blank=True, help_text="Maximum valid value.")
    warn_min = models.FloatField(
        null=True, blank=True,
        help_text=_("Soft warning minimum — values below this trigger a plausibility warning but are still accepted."),
    )
    warn_max = models.FloatField(
        null=True, blank=True,
        help_text=_("Soft warning maximum — values above this trigger a plausibility warning but are still accepted."),
    )
    very_unlikely_min = models.FloatField(
        null=True, blank=True,
        help_text=_("Hard floor — values below this are almost certainly data-entry errors. Requires two confirmations."),
    )
    very_unlikely_max = models.FloatField(
        null=True, blank=True,
        help_text=_("Hard ceiling — values above this are almost certainly data-entry errors. Requires two confirmations."),
    )
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
    cadence_sessions = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text=_("How often to prompt for this metric (in sessions). Blank = every session."),
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
    metric_type = models.CharField(
        max_length=20, choices=METRIC_TYPE_CHOICES, default="scale",
        help_text=_("Scale = numeric value recorded repeatedly. Achievement = categorical, typically recorded once."),
    )
    higher_is_better = models.BooleanField(
        default=True,
        help_text=_("False for metrics like PHQ-9 where lower is better."),
    )
    threshold_low = models.FloatField(
        null=True, blank=True,
        help_text=_("Low band boundary (scale metrics)."),
    )
    threshold_high = models.FloatField(
        null=True, blank=True,
        help_text=_("High band boundary (scale metrics)."),
    )
    achievement_options = models.JSONField(
        default=list, blank=True,
        help_text=_('Options for achievement metrics, e.g. ["Employed", "In training", "Unemployed"].'),
    )
    achievement_success_values = models.JSONField(
        default=list, blank=True,
        help_text=_('Which options count as achieved, e.g. ["Employed"].'),
    )
    target_rate = models.FloatField(
        null=True, blank=True,
        help_text=_("Optional target % for achievement metrics (e.g. 70 for 70%)."),
    )
    target_band_high_pct = models.FloatField(
        null=True, blank=True,
        help_text=_("Optional target for % in high band (scale metrics)."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # ── CIDS metadata fields (Phase 1) ────────────────────────────────
    cids_indicator_uri = models.CharField(
        max_length=500, blank=True, default="",
        help_text=_("CIDS indicator @id — CharField not URLField (URIs may use urn: schemes)."),
    )
    iris_metric_code = models.CharField(
        max_length=100, blank=True, default="",
        help_text=_("IRIS+ metric code from IrisMetric53 code list (e.g., 'PI2061')."),
    )
    sdg_goals = models.JSONField(
        default=list, blank=True,
        help_text=_("List of SDG goal numbers [1–17]."),
    )
    cids_unit_description = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_("Human-readable unit label for CIDS export (maps to cids:unitDescription)."),
    )
    cids_defined_by = models.CharField(
        max_length=500, blank=True, default="",
        help_text=_("URI of the organisation that defined this indicator (e.g., GIIN for IRIS+)."),
    )
    cids_has_baseline = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_("Human-readable baseline description (e.g., 'Average score 3.2 at intake'). NOT a boolean."),
    )
    cids_theme_override = models.CharField(
        max_length=50, blank=True, default="",
        help_text=_("Admin override for CIDS theme derivation when auto-derivation is wrong."),
    )

    # ── Rationale log ─────────────────────────────────────────────────
    rationale_log = models.JSONField(
        default=list, blank=True,
        help_text=_("Append-only changelog: [{date, note, note_fr, author}]. Most recent entry is the current rationale."),
    )

    # ── Instrument grouping ──────────────────────────────────────────
    instrument_name = models.CharField(
        max_length=100, blank=True, default="",
        help_text=_("Group name for multi-item instruments (e.g. 'PHQ-9'). "
                    "Metrics sharing an instrument_name are reported together."),
    )

    # ── Standardized instrument / assessment fields ───────────────────
    is_standardized_instrument = models.BooleanField(
        default=False,
        help_text=_("True for published validated instruments (PHQ-9, GAD-7, K10, etc.)."),
    )

    # ── Data quality descriptors (for CIDS DQV export) ────────────────
    EVIDENCE_TYPE_CHOICES = [
        ("self_report", _("Self-report (participant completes)")),
        ("staff_observed", _("Staff-observed (recorded by worker)")),
        ("administrative_record", _("Administrative record (system data)")),
        ("third_party_assessed", _("Third-party assessed (external evaluator)")),
        ("coded_qualitative", _("Coded qualitative (open responses coded to scale)")),
    ]
    evidence_type = models.CharField(
        max_length=30, blank=True, default="",
        choices=EVIDENCE_TYPE_CHOICES,
        help_text=_("How the data is generated. Describes the source, not quality."),
    )

    MEASURE_BASIS_CHOICES = [
        ("published_validated", _("Published, validated for this population")),
        ("published_adapted", _("Published, adapted for local context")),
        ("custom_participatory", _("Custom, developed with participant input")),
        ("custom_staff_designed", _("Custom, designed by staff")),
        ("administrative", _("Administrative or system-generated")),
    ]
    measure_basis = models.CharField(
        max_length=30, blank=True, default="",
        choices=MEASURE_BASIS_CHOICES,
        help_text=_("How the measure was developed. Not a quality ranking."),
    )

    DERIVATION_METHOD_CHOICES = [
        ("direct_response", _("Direct participant response")),
        ("coded_from_qualitative", _("Coded from qualitative responses")),
        ("calculated_composite", _("Calculated composite score")),
        ("staff_rating", _("Staff rating or judgment")),
    ]
    derivation_method = models.CharField(
        max_length=30, blank=True, default="",
        choices=DERIVATION_METHOD_CHOICES,
        help_text=_("How the recorded value was produced. Only needed when "
                    "the value isn't a direct participant response."),
    )
    scoring_bands = models.JSONField(
        null=True, blank=True,
        help_text=_('Published severity cutoffs, e.g. [{"label": "Minimal", "min": 0, "max": 4}]. Display-only.'),
    )
    assessment_interval_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_("Days between scheduled administrations (e.g. 90 for quarterly). Global per-metric."),
    )
    assessment_at_intake = models.BooleanField(
        default=False,
        help_text=_("Administer this assessment at intake (first session)."),
    )
    assessment_at_discharge = models.BooleanField(
        default=False,
        help_text=_("Administer this assessment at discharge."),
    )

    def clean(self):
        super().clean()
        if self.threshold_low is not None and self.threshold_high is not None:
            if self.threshold_low >= self.threshold_high:
                raise ValidationError(
                    _("Low band threshold must be less than high band threshold.")
                )
        if self.warn_min is not None and self.warn_max is not None:
            if self.warn_min >= self.warn_max:
                raise ValidationError(
                    _("Warning minimum must be less than warning maximum.")
                )
        if self.warn_min is not None and self.min_value is not None:
            if self.warn_min < self.min_value:
                raise ValidationError(
                    _("Warning minimum cannot be below the hard minimum.")
                )
        if self.warn_max is not None and self.max_value is not None:
            if self.warn_max > self.max_value:
                raise ValidationError(
                    _("Warning maximum cannot exceed the hard maximum.")
                )
        if self.very_unlikely_min is not None and self.very_unlikely_max is not None:
            if self.very_unlikely_min >= self.very_unlikely_max:
                raise ValidationError(
                    _("Very unlikely minimum must be less than very unlikely maximum.")
                )
        if self.very_unlikely_min is not None and self.warn_min is not None:
            if self.very_unlikely_min > self.warn_min:
                raise ValidationError(
                    _("Very unlikely minimum must be at or below the warning minimum.")
                )
        if self.very_unlikely_max is not None and self.warn_max is not None:
            if self.very_unlikely_max < self.warn_max:
                raise ValidationError(
                    _("Very unlikely maximum must be at or above the warning maximum.")
                )
        if self.very_unlikely_min is not None and self.min_value is not None:
            if self.very_unlikely_min < self.min_value:
                raise ValidationError(
                    _("Very unlikely minimum cannot be below the hard minimum.")
                )
        if self.very_unlikely_max is not None and self.max_value is not None:
            if self.very_unlikely_max > self.max_value:
                raise ValidationError(
                    _("Very unlikely maximum cannot exceed the hard maximum.")
                )

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

    # ── Rationale helpers ────────────────────────────────────────────
    @property
    def current_rationale(self):
        """Return the most recent rationale entry's note text, or empty string."""
        if self.rationale_log:
            entry = self.rationale_log[-1]
            from django.utils.translation import get_language
            if get_language() == "fr" and entry.get("note_fr"):
                return entry["note_fr"]
            return entry.get("note", "")
        return ""

    def append_rationale(self, note, note_fr="", author="System"):
        """Append a new entry to the rationale log."""
        import datetime as _dt
        if self.rationale_log is None:
            self.rationale_log = []
        self.rationale_log.append({
            "date": _dt.date.today().isoformat(),
            "note": note,
            "note_fr": note_fr,
            "author": author,
        })

    # ── Scoring band lookup ───────────────────────────────────────────
    def get_severity_band(self, score):
        """Return the severity band label for a given score, or None."""
        if not self.scoring_bands:
            return None
        try:
            score_val = float(score)
        except (ValueError, TypeError):
            return None
        for band in self.scoring_bands:
            if band.get("min") is not None and band.get("max") is not None:
                if band["min"] <= score_val <= band["max"]:
                    return band.get("label")
        return None

    @property
    def translated_portal_description(self):
        """Return French portal description when active language is French, else English."""
        from django.utils.translation import get_language

        if get_language() == "fr" and self.portal_description_fr:
            return self.portal_description_fr
        return self.portal_description

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

    # ── CIDS metadata (Phase 1) ───────────────────────────────────────
    cids_outcome_uri = models.CharField(
        max_length=500, blank=True, default="",
        help_text=_("CIDS outcome @id."),
    )

    # ── Achievement status (Phase F2) ──────────────────────────────────
    ACHIEVEMENT_STATUS_CHOICES = [
        ("in_progress", _("In progress")),
        ("improving", _("Improving")),
        ("worsening", _("Worsening")),
        ("no_change", _("No change")),
        ("achieved", _("Achieved")),
        ("sustaining", _("Sustaining")),
        ("not_achieved", _("Not achieved")),
        ("not_attainable", _("Not attainable")),
    ]
    ACHIEVEMENT_SOURCE_CHOICES = [
        ("auto_computed", _("Auto-computed")),
        ("worker_assessed", _("Worker assessed")),
    ]

    achievement_status = models.CharField(
        max_length=20, blank=True, default="",
        choices=ACHIEVEMENT_STATUS_CHOICES,
    )
    achievement_status_source = models.CharField(
        max_length=20, blank=True, default="",
        choices=ACHIEVEMENT_SOURCE_CHOICES,
    )
    achievement_status_updated_at = models.DateTimeField(null=True, blank=True)
    first_achieved_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("When first achieved. Never cleared once set."),
    )

    # ── FHIR Goal metadata (auto-populated) ──────────────────────────
    GOAL_SOURCE_CHOICES = [
        ("participant", _("Participant-initiated")),
        ("worker", _("Worker-initiated")),
        ("joint", _("Jointly developed")),
        ("funder_required", _("Funder-required")),
    ]

    goal_source = models.CharField(
        max_length=20, blank=True, default="",
        choices=GOAL_SOURCE_CHOICES,
        help_text=_("Who established this goal. Auto-classified from content."),
    )
    target_date = models.DateField(
        null=True, blank=True,
        help_text=_("Target completion date. Auto-set from program default or AI extraction."),
    )
    goal_source_method = models.CharField(
        max_length=20, blank=True, default="",
        help_text=_("How goal_source was derived: heuristic, worker_set, or ai_inferred."),
    )

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        # Auto-classify goal source from field population patterns
        if is_new and not self.goal_source:
            has_description = bool(self._description_encrypted and self._description_encrypted != b"")
            has_client_goal = bool(self._client_goal_encrypted and self._client_goal_encrypted != b"")
            if has_client_goal and has_description:
                self.goal_source = "joint"
            elif has_client_goal:
                self.goal_source = "participant"
            elif has_description:
                self.goal_source = "worker"
            if self.goal_source:
                self.goal_source_method = "heuristic"

        # Auto-set target_date from program default
        if is_new and not self.target_date and self.plan_section_id:
            try:
                program = self.plan_section.program
                if program and program.default_goal_review_days:
                    from datetime import timedelta
                    from django.utils import timezone
                    self.target_date = (timezone.now() + timedelta(days=program.default_goal_review_days)).date()
            except (AttributeError, TypeError):
                pass  # Plan section may not have a program

        super().save(*args, **kwargs)

    @property
    def name(self):
        try:
            return decrypt_field(self._name_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @name.setter
    def name(self, value):
        self._name_encrypted = encrypt_field(value)

    @property
    def description(self):
        try:
            return decrypt_field(self._description_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @description.setter
    def description(self, value):
        self._description_encrypted = encrypt_field(value)

    @property
    def status_reason(self):
        try:
            return decrypt_field(self._status_reason_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @status_reason.setter
    def status_reason(self, value):
        self._status_reason_encrypted = encrypt_field(value)

    @property
    def client_goal(self):
        try:
            return decrypt_field(self._client_goal_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

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
        try:
            return decrypt_field(self._name_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @name.setter
    def name(self, value):
        self._name_encrypted = encrypt_field(value)

    @property
    def description(self):
        try:
            return decrypt_field(self._description_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @description.setter
    def description(self, value):
        self._description_encrypted = encrypt_field(value)

    @property
    def status_reason(self):
        try:
            return decrypt_field(self._status_reason_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @status_reason.setter
    def status_reason(self, value):
        self._status_reason_encrypted = encrypt_field(value)

    @property
    def client_goal(self):
        try:
            return decrypt_field(self._client_goal_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

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
    assigned_date = models.DateField(default=datetime.date.today)
    last_reviewed_date = models.DateField(
        null=True, blank=True,
        help_text=_("When the worker last confirmed this metric is still relevant."),
    )

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
