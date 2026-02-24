"""Add scheduled_execution_at field and 'scheduled' status to ErasureRequest."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0023_cross_program_sharing_tristate"),
    ]

    operations = [
        migrations.AddField(
            model_name="erasurerequest",
            name="scheduled_execution_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="Tier 3 only: when the deferred erasure will execute (24h after approval).",
            ),
        ),
        migrations.AlterField(
            model_name="erasurerequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending Approval"),
                    ("anonymised", "Approved — Data Anonymised"),
                    ("scheduled", "Scheduled — Awaiting Erasure"),
                    ("approved", "Approved — Data Erased"),
                    ("rejected", "Rejected"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
