"""Merge service_group and activity_group into a single 'group' type.

The expert panel found that Service Group and Activity Group are functionally
identical (both track attendance and session notes). Only Project has extra
features (milestones, outcomes). Collapsing to two types removes confusion.
"""

from django.db import migrations, models


def merge_group_types(apps, schema_editor):
    """Convert service_group and activity_group rows to 'group'."""
    Group = apps.get_model("groups", "Group")
    Group.objects.filter(group_type="service_group").update(group_type="group")
    Group.objects.filter(group_type="activity_group").update(group_type="group")


def reverse_merge(apps, schema_editor):
    """Best-effort reverse: default all 'group' back to 'service_group'."""
    Group = apps.get_model("groups", "Group")
    Group.objects.filter(group_type="group").update(group_type="service_group")


class Migration(migrations.Migration):

    dependencies = [
        ("groups", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(merge_group_types, reverse_merge),
        migrations.AlterField(
            model_name="group",
            name="group_type",
            field=models.CharField(
                choices=[("group", "Group"), ("project", "Project")],
                max_length=20,
            ),
        ),
    ]
