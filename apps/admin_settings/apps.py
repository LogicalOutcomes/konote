from django.apps import AppConfig


class AdminSettingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admin_settings"
    label = "admin_settings"
    verbose_name = "Settings & Customisation"

    def ready(self):
        import apps.admin_settings.checks  # noqa: F401
        import apps.admin_settings.signals  # noqa: F401
