# Generated manually for SCALE-ROLLUP1

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConsortiumRollup",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("period_start", models.DateField()),
                ("period_end", models.DateField()),
                (
                    "agency_count",
                    models.PositiveIntegerField(
                        help_text="Number of agencies included in this rollup.",
                    ),
                ),
                (
                    "participant_count",
                    models.PositiveIntegerField(
                        help_text="Total participants across all agencies.",
                    ),
                ),
                (
                    "data_json",
                    models.JSONField(
                        help_text=(
                            "Aggregated report data. Structure: "
                            "{demographics: {...}, outcomes: {...}, service_stats: {...}}"
                        ),
                    ),
                ),
                ("generated_at", models.DateTimeField(auto_now=True)),
                (
                    "generated_by",
                    models.CharField(
                        default="aggregate_consortium",
                        help_text="Management command or process that generated this rollup.",
                        max_length=100,
                    ),
                ),
                (
                    "consortium",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rollups",
                        to="tenants.consortium",
                    ),
                ),
            ],
            options={
                "db_table": "consortium_rollups",
                "ordering": ["-period_start"],
                "unique_together": {("consortium", "period_start", "period_end")},
            },
        ),
    ]
