"""Data migration: convert messaging_profile to two independent boolean settings.

Old setting (messaging_profile):
    "record_keeping" → both new settings stay "false"
    "staff_sent"     → staff_messaging_enabled = "true"
    "full_automation" → automated_reminders_enabled = "true"

The old messaging_profile key is deleted after migration.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    InstanceSetting = apps.get_model("admin_settings", "InstanceSetting")

    try:
        old = InstanceSetting.objects.get(setting_key="messaging_profile")
    except InstanceSetting.DoesNotExist:
        return  # No existing setting — defaults will apply

    if old.setting_value == "staff_sent":
        InstanceSetting.objects.update_or_create(
            setting_key="staff_messaging_enabled",
            defaults={"setting_value": "true"},
        )
    elif old.setting_value == "full_automation":
        InstanceSetting.objects.update_or_create(
            setting_key="automated_reminders_enabled",
            defaults={"setting_value": "true"},
        )
    # record_keeping: both stay false (default), nothing to create

    old.delete()


def backwards(apps, schema_editor):
    InstanceSetting = apps.get_model("admin_settings", "InstanceSetting")

    staff = False
    auto = False
    try:
        s = InstanceSetting.objects.get(setting_key="staff_messaging_enabled")
        staff = s.setting_value == "true"
    except InstanceSetting.DoesNotExist:
        pass
    try:
        a = InstanceSetting.objects.get(setting_key="automated_reminders_enabled")
        auto = a.setting_value == "true"
    except InstanceSetting.DoesNotExist:
        pass

    if auto:
        profile = "full_automation"
    elif staff:
        profile = "staff_sent"
    else:
        profile = "record_keeping"

    InstanceSetting.objects.update_or_create(
        setting_key="messaging_profile",
        defaults={"setting_value": profile},
    )

    # Clean up new keys
    InstanceSetting.objects.filter(
        setting_key__in=["staff_messaging_enabled", "automated_reminders_enabled"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("admin_settings", "0006_split_ai_toggle"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
