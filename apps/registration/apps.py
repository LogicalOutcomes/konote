from django.apps import AppConfig


class RegistrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.registration"
    label = "registration"
    verbose_name = "Registration"

    def ready(self):
        """Connect signals when app is ready."""
        from . import signals  # noqa: F401
