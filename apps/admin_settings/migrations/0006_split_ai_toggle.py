"""Data migration: split ai_assist toggle into ai_assist_tools_only + ai_assist_participant_data."""
from django.db import migrations


def split_ai_toggle(apps, schema_editor):
    FeatureToggle = apps.get_model("admin_settings", "FeatureToggle")

    try:
        old_toggle = FeatureToggle.objects.get(feature_key="ai_assist")
        was_enabled = old_toggle.is_enabled

        # Tools-only always enabled (new default)
        FeatureToggle.objects.update_or_create(
            feature_key="ai_assist_tools_only",
            defaults={"is_enabled": True},
        )
        # Participant data preserves the old toggle state
        FeatureToggle.objects.update_or_create(
            feature_key="ai_assist_participant_data",
            defaults={"is_enabled": was_enabled},
        )
        old_toggle.delete()
    except FeatureToggle.DoesNotExist:
        # No existing toggle — new defaults via FEATURES_DEFAULT_ENABLED apply
        pass


def reverse_split(apps, schema_editor):
    FeatureToggle = apps.get_model("admin_settings", "FeatureToggle")

    participant_toggle = FeatureToggle.objects.filter(
        feature_key="ai_assist_participant_data"
    ).first()
    was_enabled = participant_toggle.is_enabled if participant_toggle else False

    FeatureToggle.objects.update_or_create(
        feature_key="ai_assist",
        defaults={"is_enabled": was_enabled},
    )
    FeatureToggle.objects.filter(
        feature_key__in=["ai_assist_tools_only", "ai_assist_participant_data"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("admin_settings", "0005_backup_reminder_fields"),
    ]
    operations = [
        migrations.RunPython(split_ai_toggle, reverse_split),
    ]
