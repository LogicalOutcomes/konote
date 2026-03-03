from django.apps import AppConfig


class PlansConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.plans"
    label = "plans"
    verbose_name = "Plans & Outcomes"

    def ready(self):
        import apps.plans.signals  # noqa: F401
