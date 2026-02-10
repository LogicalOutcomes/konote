from django.apps import AppConfig


class AuthAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auth_app"
    label = "auth_app"
    verbose_name = "Authentication"

    def ready(self):
        import apps.auth_app.checks  # noqa: F401
