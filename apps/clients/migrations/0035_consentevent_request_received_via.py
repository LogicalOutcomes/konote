"""Add request_received_via field to ConsentEvent."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0034_consentevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="consentevent",
            name="request_received_via",
            field=models.CharField(
                blank=True,
                default="",
                help_text="How the withdrawal request was received (written, verbal, representative).",
                max_length=20,
            ),
        ),
    ]
