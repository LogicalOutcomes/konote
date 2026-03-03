"""Consortia app — tenant-scoped models for cross-agency data sharing."""
from django.apps import AppConfig


class ConsortiaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.consortia"
    label = "consortia"
    verbose_name = "Consortia"
