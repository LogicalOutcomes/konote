"""Add evaluation_export_granted field to User model.

Per-user permission grant for de-identified evaluation exports.
Default False — must be explicitly granted by admin.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0010_user_demo_group"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="evaluation_export_granted",
            field=models.BooleanField(
                default=False,
                help_text="Explicitly granted permission to generate de-identified evaluation exports.",
            ),
        ),
    ]
