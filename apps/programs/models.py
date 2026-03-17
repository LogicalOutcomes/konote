"""Program and user-program role models."""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.auth_app.constants import CLIENT_ACCESS_ROLES, ROLE_EXECUTIVE


class Program(models.Model):
    """An organisational unit (e.g., housing, employment, youth services)."""

    SERVICE_MODEL_CHOICES = [
        ("individual", _("One-on-one")),
        ("group", _("Group sessions")),
        ("both", _("Both")),
    ]

    name = models.CharField(max_length=255)
    name_fr = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_("French name (displayed when language is French)"),
    )
    portal_display_name = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_("Name shown in participant portal. Leave blank to use program name."),
    )
    description = models.TextField(default="", blank=True)
    colour_hex = models.CharField(max_length=7, default="#3B82F6")
    service_model = models.CharField(
        max_length=20,
        choices=SERVICE_MODEL_CHOICES,
        default="both",
        help_text=_(
            "How staff record their work in this program. "
            "One-on-one: individual notes and plans. "
            "Group sessions: attendance and session notes. "
            "Both: all of the above."
        ),
    )
    status = models.CharField(
        max_length=20, default="active",
        choices=[("active", "Active"), ("archived", "Archived")],
    )
    is_confidential = models.BooleanField(
        default=False,
        help_text=_(
            "Confidential programs are invisible to staff in other programs. "
            "Cannot be changed back to Standard without a formal Privacy Impact Assessment."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── CIDS metadata fields (Phase 1) ────────────────────────────────
    cids_sector_code = models.CharField(
        max_length=100, blank=True, default="",
        help_text=_("CIDS sector code from ICNPOsector or ESDCSector code list."),
    )
    population_served_codes = models.JSONField(
        default=list, blank=True,
        help_text=_("Population served codes from PopulationServed code list."),
    )
    description_fr = models.TextField(
        blank=True, default="",
        help_text=_("French description for bilingual CIDS exports."),
    )
    funder_program_code = models.CharField(
        max_length=100, blank=True, default="",
        help_text=_("Funder-assigned program identifier."),
    )
    # ── FHIR-informed defaults ───────────────────────────────────────
    default_goal_review_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_("Default target date offset (days) for goals created in this program."),
    )

    class Meta:
        app_label = "programs"
        db_table = "programs"
        ordering = ["name"]

    @property
    def translated_name(self):
        """Return French name when active language is French, else English."""
        from django.utils.translation import get_language

        if get_language() == "fr" and self.name_fr:
            return self.name_fr
        return self.name

    def __str__(self):
        return self.name


class UserProgramRole(models.Model):
    """Links a user to a program with a specific role."""

    ROLE_CHOICES = [
        ("receptionist", _("Front Desk")),
        ("staff", _("Direct Service")),
        ("program_manager", _("Program Manager")),
        ("executive", _("Executive")),
    ]
    STATUS_CHOICES = [
        ("active", _("Active")),
        ("removed", _("Removed")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="program_roles"
    )
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="user_roles")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, default="active", choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "programs"
        db_table = "user_program_roles"
        unique_together = ["user", "program"]

    # Roles that grant access to individual client records
    CLIENT_ACCESS_ROLES = CLIENT_ACCESS_ROLES  # alias for apps.auth_app.constants.CLIENT_ACCESS_ROLES

    def __str__(self):
        return f"{self.user} → {self.program} ({self.role})"

    @classmethod
    def is_executive_only(cls, user, roles=None):
        """Check if user only has executive role (no client access roles).

        Returns True if the user has an active executive role but no roles
        that grant access to individual client records.

        Pass pre-fetched ``roles`` set to avoid an extra query when the
        caller has already loaded the user's roles.
        """
        if roles is None:
            roles = set(
                cls.objects.filter(user=user, status="active")
                .values_list("role", flat=True)
            )
        if not roles:
            return False
        if ROLE_EXECUTIVE in roles:
            return not bool(roles & cls.CLIENT_ACCESS_ROLES)
        return False


# ── Evaluation Planning models (CIDS Full Tier) ──────────────────────


class EvaluationFramework(models.Model):
    """Program-level evaluation framework that maps to cids:ImpactModel."""

    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("active", _("Active")),
        ("archived", _("Archived")),
    ]
    QUALITY_CHOICES = [
        ("ai_generated", _("AI-generated")),
        ("checks_passed", _("Checks passed")),
        ("human_confirmed", _("Human-confirmed")),
        ("manual", _("Manually entered")),
    ]

    name = models.CharField(max_length=255)
    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, related_name="evaluation_frameworks",
    )
    report_template = models.ForeignKey(
        "reports.ReportTemplate", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="evaluation_frameworks",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    planning_quality_state = models.CharField(
        max_length=20, choices=QUALITY_CHOICES, default="manual",
    )

    summary = models.TextField(blank=True, default="")
    output_summary = models.TextField(blank=True, default="")
    outcome_chain_summary = models.TextField(blank=True, default="")
    risk_summary = models.TextField(blank=True, default="")
    counterfactual_summary = models.TextField(blank=True, default="")
    partner_requirements_summary = models.TextField(blank=True, default="")
    source_documents_json = models.JSONField(default=list, blank=True)

    evaluator_attestation_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="attested_frameworks",
    )
    evaluator_attestation_at = models.DateTimeField(null=True, blank=True)
    evaluator_attestation_scope = models.JSONField(null=True, blank=True)
    evaluator_attestation_text = models.TextField(blank=True, default="")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_frameworks",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="updated_frameworks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "programs"
        db_table = "evaluation_frameworks"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.program.name})"

    @property
    def cids_class_coverage(self):
        """Return set of distinct CIDS classes mapped by components."""
        return set(
            self.components.filter(is_active=True)
            .exclude(cids_class="")
            .values_list("cids_class", flat=True)
        )

    @property
    def is_attested(self):
        return self.evaluator_attestation_by_id is not None


class EvaluationComponent(models.Model):
    """Structured child record mapping to a CIDS Full Tier class."""

    COMPONENT_TYPES = [
        ("participant_group", _("Participant group")),
        ("service", _("Service")),
        ("activity", _("Activity")),
        ("output", _("Output")),
        ("outcome", _("Outcome")),
        ("risk", _("Risk")),
        ("mitigation", _("Mitigation")),
        ("counterfactual", _("Counterfactual")),
        ("assumption", _("Assumption")),
        ("input", _("Input")),
        ("impact_dimension", _("Impact dimension")),
    ]
    CIDS_CLASS_MAP = {
        "participant_group": "cids:Stakeholder",
        "service": "cids:Service",
        "activity": "cids:Activity",
        "output": "cids:Output",
        "outcome": "cids:StakeholderOutcome",
        "risk": "cids:ImpactRisk",
        "mitigation": "cids:ImpactRisk",
        "counterfactual": "cids:Counterfactual",
        "assumption": "",
        "input": "cids:Input",
        "impact_dimension": "cids:ImpactDimension",
    }
    QUALITY_CHOICES = [
        ("ai_generated", _("AI-generated")),
        ("checks_passed", _("Checks passed")),
        ("human_confirmed", _("Human-confirmed")),
        ("manual", _("Manually entered")),
    ]
    PROVENANCE_CHOICES = [
        ("manual", _("Manual")),
        ("ai_local", _("AI (local)")),
        ("ai_external", _("AI (external)")),
        ("imported", _("Imported")),
    ]

    framework = models.ForeignKey(
        EvaluationFramework, on_delete=models.CASCADE, related_name="components",
    )
    component_type = models.CharField(max_length=30, choices=COMPONENT_TYPES)
    cids_class = models.CharField(max_length=100, blank=True, default="")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    sequence_order = models.IntegerField(default=0)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children",
    )
    structured_payload = models.JSONField(default=dict, blank=True)
    quality_state = models.CharField(
        max_length=20, choices=QUALITY_CHOICES, default="manual",
    )
    provenance_source = models.CharField(
        max_length=20, choices=PROVENANCE_CHOICES, default="manual",
    )
    provenance_model = models.CharField(max_length=200, blank=True, default="")
    confidence_score = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "programs"
        db_table = "evaluation_components"
        ordering = ["framework", "sequence_order", "pk"]

    def __str__(self):
        return f"{self.get_component_type_display()}: {self.name}"

    def save(self, *args, **kwargs):
        if not self.cids_class:
            self.cids_class = self.CIDS_CLASS_MAP.get(self.component_type, "")
        super().save(*args, **kwargs)


class EvaluationEvidenceLink(models.Model):
    """Source material that supported an evaluation framework."""

    SOURCE_TYPE_CHOICES = [
        ("proposal", _("Proposal")),
        ("logic_model", _("Logic model")),
        ("funder_requirement", _("Funder requirement")),
        ("website", _("Website")),
        ("manual_note", _("Manual note")),
        ("report_template", _("Report template")),
    ]

    framework = models.ForeignKey(
        EvaluationFramework, on_delete=models.CASCADE, related_name="evidence_links",
    )
    title = models.CharField(max_length=255)
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPE_CHOICES)
    storage_path = models.CharField(max_length=500, blank=True, default="")
    external_reference = models.URLField(max_length=500, blank=True, default="")
    excerpt_text = models.TextField(blank=True, default="")
    contains_pii = models.BooleanField(default=False)
    used_for_ai = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "programs"
        db_table = "evaluation_evidence_links"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
