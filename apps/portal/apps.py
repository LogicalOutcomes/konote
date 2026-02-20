from django.apps import AppConfig


class PortalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.portal"
    label = "portal"
    verbose_name = "Participant Portal"

    def ready(self):
        import apps.portal.signals  # noqa: F401 -- registers signal handlers
