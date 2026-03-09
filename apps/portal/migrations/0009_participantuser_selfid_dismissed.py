"""Add selfid_dismissed field to ParticipantUser.

Allows participants to hide the About Me card from the dashboard.
Reversible via the Settings page.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0008_participantuser_selfid_consent_shown"),
    ]

    operations = [
        migrations.AddField(
            model_name="participantuser",
            name="selfid_dismissed",
            field=models.BooleanField(
                default=False,
                help_text="True if the participant chose to hide the About Me card from the dashboard.",
            ),
        ),
    ]
