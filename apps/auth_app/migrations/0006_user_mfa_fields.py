"""Add MFA fields to User model for TOTP authentication."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0005_user_preferred_language"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="mfa_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="mfa_secret",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="user",
            name="mfa_backup_codes",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
