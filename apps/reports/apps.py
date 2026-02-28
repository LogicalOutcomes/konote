from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"
    label = "reports"
    verbose_name = "Reports & Charts"

    def ready(self):
        import apps.reports.checks  # noqa: F401
