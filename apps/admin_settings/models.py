"""Instance customisation: terminology, features, and settings."""
from django.db import models
from django.utils.translation import gettext_lazy as _lazy


# Default terminology — keys must match template usage
# Format: { key: (English, French) }
DEFAULT_TERMS = {
    # People & files
    "client": ("Participant", "Participant(e)"),
    "client_plural": ("Participants", "Participant(e)s"),
    "worker": ("Worker", "Intervenant(e)"),
    "worker_plural": ("Workers", "Intervenant(e)s"),
    "file": ("File", "Dossier"),
    "file_plural": ("Files", "Dossiers"),
    # Plans & structure
    "plan": ("Plan", "Plan"),
    "plan_plural": ("Plans", "Plans"),
    "section": ("Section", "Section"),
    "section_plural": ("Sections", "Sections"),
    "target": ("Target", "Objectif"),
    "target_plural": ("Targets", "Objectifs"),
    # Measurement
    "metric": ("Metric", "Indicateur"),
    "metric_plural": ("Metrics", "Indicateurs"),
    # Notes
    "progress_note": ("Note", "Note de suivi"),
    "progress_note_plural": ("Notes", "Notes de suivi"),
    "quick_note": ("Quick Note", "Note rapide"),
    "quick_note_plural": ("Quick Notes", "Notes rapides"),
    # Events & alerts
    "event": ("Event", "Événement"),
    "event_plural": ("Events", "Événements"),
    "alert": ("Alert", "Alerte"),
    "alert_plural": ("Alerts", "Alertes"),
    # Programs & enrolment
    "program": ("Program", "Programme"),
    "program_plural": ("Programs", "Programmes"),
    "enrolment": ("Enrolment", "Inscription"),
    "enrolment_plural": ("Enrolments", "Inscriptions"),
    # Groups & sessions
    "group": ("Group", "Groupe"),
    "group_plural": ("Groups", "Groupes"),
    "member": ("Member", "Membre"),
    "member_plural": ("Members", "Membres"),
    "session": ("Session", "Séance"),
    "session_plural": ("Sessions", "Séances"),
    # Circles
    "circle": ("Circle", "Cercle"),
    "circle_plural": ("Circles", "Cercles"),
    # Portal resources
    "resource": ("Resource", "Ressource"),
    "resource_plural": ("Resources", "Ressources"),
}

# Help text showing where each term appears in the interface.
# Separate dict to avoid changing the (EN, FR) tuple structure above.
TERM_HELP_TEXT = {
    "client": _lazy("Used in: search bar, navigation, file headers, plan labels, notes, exports, registration forms"),
    "client_plural": _lazy("Used in: navigation menu, dashboard counts, search results, reports"),
    "worker": _lazy("Used in: staff assignment dropdowns, file headers, message labels"),
    "worker_plural": _lazy("Used in: admin user list, program role assignments, reports"),
    "file": _lazy("Used in: participant detail page header, breadcrumbs, note headers"),
    "file_plural": _lazy("Used in: navigation menu, search results heading"),
    "plan": _lazy("Used in: participant file tabs, plan page header, goal builder"),
    "plan_plural": _lazy("Used in: navigation menu, dashboard summaries"),
    "section": _lazy("Used in: plan structure, template builder, report grouping"),
    "section_plural": _lazy("Used in: plan editor sidebar, template management"),
    "target": _lazy("Used in: plan goals, progress note forms, analysis charts"),
    "target_plural": _lazy("Used in: plan summary, dashboard counts, reports"),
    "metric": _lazy("Used in: progress note value entry, analysis charts, alert thresholds"),
    "metric_plural": _lazy("Used in: plan template builder, metric library, reports"),
    "progress_note": _lazy("Used in: participant timeline, note detail page, exports"),
    "progress_note_plural": _lazy("Used in: navigation menu, dashboard counts, search results"),
    "quick_note": _lazy("Used in: quick note buttons on participant file, timeline"),
    "quick_note_plural": _lazy("Used in: dashboard counts, communication logs"),
    "event": _lazy("Used in: participant timeline, event recording form, calendar feed"),
    "event_plural": _lazy("Used in: navigation menu, dashboard counts, reports"),
    "alert": _lazy("Used in: dashboard badges, participant file warnings"),
    "alert_plural": _lazy("Used in: dashboard summary, notification counts"),
    "program": _lazy("Used in: program selector, enrolment forms, reports, file headers"),
    "program_plural": _lazy("Used in: navigation menu, dashboard cards, admin management"),
    "enrolment": _lazy("Used in: participant file program tab, intake forms"),
    "enrolment_plural": _lazy("Used in: program reports, dashboard counts"),
    "group": _lazy("Used in: group detail page, session recording, attendance"),
    "group_plural": _lazy("Used in: navigation menu, dashboard counts"),
    "member": _lazy("Used in: group roster, attendance marking, session records"),
    "member_plural": _lazy("Used in: group detail page, attendance summary"),
    "session": _lazy("Used in: group session recording form, attendance page"),
    "session_plural": _lazy("Used in: group detail page, session history"),
    "circle": _lazy("Used in: navigation, circle list, circle detail, participant file sidebar, note form"),
    "circle_plural": _lazy("Used in: navigation menu, dashboard counts, reports"),
    "resource": _lazy("Used in: portal resources page heading, staff resource management"),
    "resource_plural": _lazy("Used in: portal navigation menu, portal resources page"),
}


def get_default_terms_for_language(lang="en"):
    """Return default terms for a specific language.

    Args:
        lang: Language code ('en' or 'fr'). Defaults to 'en'.

    Returns:
        Dict of term_key -> display_value for the specified language.
    """
    index = 1 if lang.startswith("fr") else 0
    return {key: values[index] for key, values in DEFAULT_TERMS.items()}


class TerminologyOverride(models.Model):
    """Stores custom terminology for this instance.

    Supports both English and French overrides. If a French override is not
    provided, the English override (or default) is used as a fallback.
    """

    term_key = models.CharField(max_length=100, unique=True)
    display_value = models.CharField(max_length=255)  # English
    display_value_fr = models.CharField(
        max_length=255, blank=True, default="",
        help_text="French translation. Leave blank to use English value.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "admin_settings"
        db_table = "terminology_overrides"

    def __str__(self):
        return f"{self.term_key} → {self.display_value}"

    @classmethod
    def get_all_terms(cls, lang="en"):
        """Return merged dict of defaults + overrides for a language.

        Args:
            lang: Language code ('en' or 'fr'). Defaults to 'en'.

        Returns:
            Dict of term_key -> display_value for the specified language.
            Falls back to English if French translation is empty.
        """
        # Start with defaults for the requested language
        terms = get_default_terms_for_language(lang)

        # Get all overrides
        overrides = cls.objects.all()

        for override in overrides:
            if lang.startswith("fr") and override.display_value_fr:
                # Use French override if available
                terms[override.term_key] = override.display_value_fr
            elif override.display_value:
                # Use English override (or as fallback for French)
                terms[override.term_key] = override.display_value

        return terms


class FeatureToggle(models.Model):
    """Feature flags for this instance."""

    feature_key = models.CharField(max_length=100, unique=True)
    is_enabled = models.BooleanField(default=False)
    config_json = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "admin_settings"
        db_table = "feature_toggles"

    def __str__(self):
        state = "ON" if self.is_enabled else "OFF"
        return f"{self.feature_key}: {state}"

    @classmethod
    def get_all_flags(cls):
        """Return dict of feature_key → is_enabled."""
        return dict(cls.objects.values_list("feature_key", "is_enabled"))


class InstanceSetting(models.Model):
    """Key-value settings for branding, formats, timeouts, etc."""

    setting_key = models.CharField(max_length=100, unique=True)
    setting_value = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "admin_settings"
        db_table = "instance_settings"

    def __str__(self):
        return f"{self.setting_key}: {self.setting_value[:50]}"

    @classmethod
    def get_all(cls):
        """Return dict of all settings."""
        return dict(cls.objects.values_list("setting_key", "setting_value"))

    @classmethod
    def get(cls, key, default=""):
        """Get a single setting value."""
        try:
            return cls.objects.get(setting_key=key).setting_value
        except cls.DoesNotExist:
            return default


class CidsCodeList(models.Model):
    """CIDS code list entries from Common Approach code lists.

    Stores codes from the 17 official code lists published at
    codelist.commonapproach.org. Populated via the import_cids_codelists
    management command.
    """

    list_name = models.CharField(
        max_length=100,
        help_text=_lazy('Code list name, e.g., "ICNPOsector", "IrisMetric53".'),
    )
    code = models.CharField(
        max_length=100,
        help_text=_lazy("The code value within the list."),
    )
    label = models.CharField(
        max_length=255,
        help_text=_lazy("Display label (English)."),
    )
    label_fr = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_lazy("French label."),
    )
    description = models.TextField(
        blank=True, default="",
        help_text=_lazy("Longer description of the code."),
    )
    specification_uri = models.CharField(
        max_length=500, blank=True, default="",
        help_text=_lazy("URI of code list spec (for SHACL cids:hasSpecification)."),
    )
    defined_by_name = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_lazy('Defining organisation name (e.g., "GIIN", "United Nations").'),
    )
    defined_by_uri = models.CharField(
        max_length=500, blank=True, default="",
        help_text=_lazy("URI of defining organisation (for SHACL cids:definedBy)."),
    )
    source_url = models.URLField(
        blank=True, default="",
        help_text=_lazy("Common Approach code list page URL."),
    )
    version_date = models.DateField(
        blank=True, null=True,
        help_text=_lazy("For staleness warnings."),
    )

    class Meta:
        app_label = "admin_settings"
        db_table = "cids_code_lists"
        unique_together = [("list_name", "code")]
        ordering = ["list_name", "code"]
        verbose_name = "CIDS Code List Entry"
        verbose_name_plural = "CIDS Code List Entries"

    def __str__(self):
        return f"{self.list_name}: {self.code} — {self.label}"


class TaxonomyMapping(models.Model):
    """Maps metrics, programs, or plan targets to external taxonomy codes.

    Supports multi-funder taxonomy: a single metric can have mappings
    to CIDS/IRIS, United Way, PHAC, provincial taxonomies, etc.
    Each mapping optionally scopes to a specific funder context.

    Design: explicit nullable FKs (not GenericFK) — simpler queries,
    standard Django patterns, and the set of mappable models is small.
    Exactly one of the three FKs must be set per row.
    """

    TAXONOMY_SYSTEMS = [
        ("cids_iris", _lazy("CIDS / IRIS+")),
        ("united_way", _lazy("United Way")),
        ("phac", _lazy("Public Health Agency of Canada")),
        ("provincial", _lazy("Provincial")),
        ("esdc", _lazy("ESDC")),
        ("custom", _lazy("Custom")),
    ]

    metric_definition = models.ForeignKey(
        "plans.MetricDefinition",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="taxonomy_mappings",
    )
    program = models.ForeignKey(
        "programs.Program",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="taxonomy_mappings",
    )
    plan_target = models.ForeignKey(
        "plans.PlanTarget",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="taxonomy_mappings",
    )
    taxonomy_system = models.CharField(
        max_length=50,
        choices=TAXONOMY_SYSTEMS,
        help_text=_lazy('e.g., "cids_iris", "united_way", "phac".'),
    )
    taxonomy_code = models.CharField(
        max_length=100,
        help_text=_lazy("Code within the taxonomy system."),
    )
    taxonomy_label = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_lazy("Display label for the taxonomy code."),
    )
    funder_context = models.CharField(
        max_length=100, blank=True, default="",
        help_text=_lazy("Which funder this mapping serves (blank = universal)."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "admin_settings"
        db_table = "taxonomy_mappings"
        ordering = ["taxonomy_system", "taxonomy_code"]
        verbose_name = "Taxonomy Mapping"

    def __str__(self):
        target = (
            f"Metric:{self.metric_definition_id}"
            if self.metric_definition_id
            else f"Program:{self.program_id}"
            if self.program_id
            else f"Target:{self.plan_target_id}"
        )
        return f"{target} → {self.taxonomy_system}:{self.taxonomy_code}"

    def clean(self):
        """Validate that exactly one of the three FKs is set."""
        from django.core.exceptions import ValidationError

        fk_count = sum([
            self.metric_definition_id is not None,
            self.program_id is not None,
            self.plan_target_id is not None,
        ])
        if fk_count != 1:
            raise ValidationError(
                _lazy("Exactly one of metric_definition, program, or plan_target must be set.")
            )


class OrganizationProfile(models.Model):
    """Singleton model storing organisation identity for CIDS exports.

    Only one row should exist per instance. Use get_solo() to retrieve.
    """

    PROVINCE_CHOICES = [
        ("AB", "Alberta"),
        ("BC", "British Columbia"),
        ("MB", "Manitoba"),
        ("NB", "New Brunswick"),
        ("NL", "Newfoundland and Labrador"),
        ("NS", "Nova Scotia"),
        ("NT", "Northwest Territories"),
        ("NU", "Nunavut"),
        ("ON", "Ontario"),
        ("PE", "Prince Edward Island"),
        ("QC", "Quebec"),
        ("SK", "Saskatchewan"),
        ("YT", "Yukon"),
    ]

    legal_name = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_lazy("Required for CIDS BasicTier (org:hasLegalName)."),
    )
    operating_name = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_lazy("Display name used in the application."),
    )
    description = models.TextField(
        blank=True, default="",
        help_text=_lazy("Mission statement or organisation description."),
    )
    description_fr = models.TextField(
        blank=True, default="",
        help_text=_lazy("French mission statement for bilingual CIDS exports."),
    )
    legal_status = models.CharField(
        max_length=100, blank=True, default="",
        help_text=_lazy("e.g., Registered charity, Nonprofit corporation."),
    )
    sector_codes = models.JSONField(
        default=list, blank=True,
        help_text=_lazy("ICNPOsector codes for the organisation."),
    )
    street_address = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    province = models.CharField(
        max_length=2, blank=True, default="",
        choices=PROVINCE_CHOICES,
    )
    postal_code = models.CharField(
        max_length=10, blank=True, default="",
        help_text=_lazy("Canadian format: A1A 1A1."),
    )
    country = models.CharField(max_length=2, default="CA")
    website = models.URLField(blank=True, default="")

    # Backup reminder settings
    backup_reminder_enabled = models.BooleanField(
        default=False,
        help_text=_lazy("Send periodic reminders when a backup export is due."),
    )
    backup_reminder_frequency_days = models.IntegerField(
        default=90,
        help_text=_lazy("How often to send backup reminders (in days)."),
    )
    backup_reminder_contact_email = models.EmailField(
        blank=True,
        default="",
        help_text=_lazy("Email address to send backup reminders to."),
    )
    backup_reminder_last_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_lazy("When the last backup reminder was sent."),
    )
    backup_last_exported_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_lazy("When the last backup export was completed."),
    )

    class Meta:
        app_label = "admin_settings"
        db_table = "organization_profiles"
        verbose_name = "Organisation Profile"

    def __str__(self):
        return self.operating_name or self.legal_name or "Organisation Profile"

    @classmethod
    def get_solo(cls):
        """Get or create the singleton instance."""
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        """Enforce singleton — always use pk=1."""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of the singleton."""
        pass


# --- Access tier helper ---

# Tier descriptions for admin UI and documentation
ACCESS_TIER_CHOICES = [
    ("1", "Open Access"),
    ("2", "Role-Based"),
    ("3", "Clinical Safeguards"),
]

ACCESS_TIER_DESCRIPTIONS = {
    "1": (
        "Everyone on the team sees what they need for their role. "
        "Good for programs where data is non-sensitive and the team is small. "
        "Front desk still cannot see clinical notes. Executives see aggregate data only."
    ),
    "2": (
        "Different roles see different things, and you can configure exactly which "
        "fields front desk can see or edit. Good for agencies with distinct front desk, "
        "worker, and manager functions. DV-safe mode is available."
    ),
    "3": (
        "Additional protections for clinical and safety-sensitive data. Program managers "
        "must document why they need to view clinical notes, with time-limited access. "
        "DV-safe mode is prompted during setup."
    ),
}


def get_access_tier():
    """Return the agency's access tier (1, 2, or 3). Default is 1.

    Used by the permission decorator to determine whether GATED
    permissions are enforced (Tier 3) or relaxed to ALLOW (Tiers 1–2).
    Also used by templates to show/hide tier-specific admin UI.
    """
    return int(InstanceSetting.get("access_tier", "1"))
