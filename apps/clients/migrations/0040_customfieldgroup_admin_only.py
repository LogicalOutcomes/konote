"""Add admin_only field to CustomFieldGroup.

Groups marked admin_only are only visible to administrators. Used for
demographic data collected for funder reporting that frontline workers
do not need to see (DEMO-VIS1).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0039_set_demographics_collapsed"),
    ]

    operations = [
        migrations.AddField(
            model_name="customfieldgroup",
            name="admin_only",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "When checked, this group is only visible to administrators. "
                    "Use for demographic data collected for funder reporting that "
                    "frontline workers do not need to see."
                ),
            ),
        ),
    ]
