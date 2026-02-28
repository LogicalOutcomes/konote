from django.apps import AppConfig


class NotesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notes"
    label = "notes"
    verbose_name = "Progress Notes"

    def ready(self):
        import apps.notes.signals  # noqa: F401
