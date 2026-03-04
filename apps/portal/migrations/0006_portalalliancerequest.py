import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0001_initial"),
        ("notes", "0027_progressnote_alliance_prompt_index"),
        ("portal", "0005_add_portal_resource_links"),
    ]

    operations = [
        migrations.CreateModel(
            name="PortalAllianceRequest",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "prompt_index",
                    models.PositiveSmallIntegerField(
                        help_text="Which alliance prompt set to show (index into ALLIANCE_PROMPT_SETS).",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("completed", "Completed"),
                            ("expired", "Expired"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "rating",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        help_text="Participant's self-rated alliance score (1-5).",
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "expires_at",
                    models.DateTimeField(
                        help_text="Request expires 7 days after creation.",
                    ),
                ),
                (
                    "client_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="portal_alliance_requests",
                        to="clients.clientfile",
                    ),
                ),
                (
                    "progress_note",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="portal_alliance_request",
                        to="notes.progressnote",
                    ),
                ),
            ],
            options={
                "verbose_name": "portal alliance request",
                "verbose_name_plural": "portal alliance requests",
                "db_table": "portal_alliance_requests",
                "ordering": ["-created_at"],
            },
        ),
    ]
