"""Add participant_suggestion and suggestion_priority fields to ProgressNote.

Captures participant feedback on programme improvement, shown on every note form.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notes", "0007_add_qualitative_tracking"),
    ]

    operations = [
        migrations.AddField(
            model_name="progressnote",
            name="_participant_suggestion_encrypted",
            field=models.BinaryField(blank=True, default=b""),
        ),
        migrations.AddField(
            model_name="progressnote",
            name="suggestion_priority",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "---------"),
                    ("noted", "Noted"),
                    ("worth_exploring", "Worth exploring"),
                    ("important", "Important"),
                    ("urgent", "Urgent"),
                ],
                default="",
                max_length=20,
            ),
        ),
    ]
