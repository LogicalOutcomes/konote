"""Create ConsentEvent model for PIPEDA consent withdrawal audit trail."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("clients", "0033_serviceepisode_consent_to_aggregate_reporting_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConsentEvent",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("granted", "Consent Granted"),
                            ("withdrawn", "Consent Withdrawn"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "event_date",
                    models.DateField(
                        help_text="Date the consent event occurred.",
                    ),
                ),
                ("recorded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "recorded_by_display",
                    models.CharField(default="", max_length=255),
                ),
                (
                    "consent_type",
                    models.CharField(blank=True, default="", max_length=50),
                ),
                (
                    "withdrawal_reason",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", "— Not specified —"),
                            ("participant_requested", "Participant requested"),
                            (
                                "guardian_requested",
                                "Guardian/substitute decision-maker requested",
                            ),
                            ("service_ended", "Service relationship ended"),
                            ("transferred", "Transferred to another agency"),
                            ("other", "Other"),
                        ],
                        default="",
                        max_length=30,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                (
                    "client_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consent_events",
                        to="clients.clientfile",
                    ),
                ),
                (
                    "recorded_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "consent_events",
                "ordering": ["-recorded_at"],
            },
        ),
    ]
