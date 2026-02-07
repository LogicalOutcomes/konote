"""Instance customisation: terminology, features, and settings."""
from django.db import models


# Default terminology — keys must match template usage
# Format: { key: (English, French) }
DEFAULT_TERMS = {
    # People & files
    "client": ("Participant", "Participant(e)"),
    "client_plural": ("Participants", "Participant(e)s"),
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
    "progress_note": ("Progress Note", "Note de suivi"),
    "progress_note_plural": ("Progress Notes", "Notes de suivi"),
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
