"""Seed the five default AccessGrantReason rows."""
from django.db import migrations


def seed_reasons(apps, schema_editor):
    AccessGrantReason = apps.get_model("auth_app", "AccessGrantReason")
    defaults = [
        {"label": "Clinical supervision", "label_fr": "Supervision clinique", "sort_order": 1},
        {"label": "Complaint investigation", "label_fr": "Enquête sur une plainte", "sort_order": 2},
        {"label": "Safety concern", "label_fr": "Préoccupation liée à la sécurité", "sort_order": 3},
        {"label": "Quality assurance", "label_fr": "Assurance qualité", "sort_order": 4},
        {"label": "Intake / case assignment", "label_fr": "Accueil / attribution de dossier", "sort_order": 5},
    ]
    for d in defaults:
        AccessGrantReason.objects.get_or_create(label=d["label"], defaults=d)


def unseed_reasons(apps, schema_editor):
    AccessGrantReason = apps.get_model("auth_app", "AccessGrantReason")
    AccessGrantReason.objects.filter(
        label__in=[
            "Clinical supervision",
            "Complaint investigation",
            "Safety concern",
            "Quality assurance",
            "Intake / case assignment",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0008_add_access_grant_reason_and_access_grant"),
    ]

    operations = [
        migrations.RunPython(seed_reasons, unseed_reasons),
    ]
