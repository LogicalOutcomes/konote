"""Add demo_group field to User model.

Groups demo users by instance type so instance-specific seeds can suppress
the default demo users on the login page automatically.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0009_seed_default_grant_reasons"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="demo_group",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Groups demo users by instance type (e.g. 'default', 'prosper-canada'). "
                    "When instance-specific demo users exist, the login page suppresses "
                    "the 'default' group automatically."
                ),
                max_length=50,
                null=True,
            ),
        ),
    ]
