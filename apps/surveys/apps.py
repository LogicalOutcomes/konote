from django.apps import AppConfig


class SurveysConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.surveys"
    verbose_name = "Surveys"

    def ready(self):
        import apps.surveys.signals  # noqa: F401
