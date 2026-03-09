"""Add selfid_consent_shown field to ParticipantUser.

Tracks whether the participant has seen the self-identification
consent disclosure before filling in their demographic data (DEMO-VIS1).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0007_portalresourcelink_url_fr"),
    ]

    operations = [
        migrations.AddField(
            model_name="participantuser",
            name="selfid_consent_shown",
            field=models.BooleanField(
                default=False,
                help_text="True after the participant has seen the self-identification consent notice.",
            ),
        ),
    ]
