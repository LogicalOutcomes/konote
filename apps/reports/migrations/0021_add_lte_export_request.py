"""LTE — Add LTEExportRequest and LTELifecycleEvent models.

The Longitudinal Trajectory Export is a structurally separate export
tier from the Evaluation Microdata Export. See
tasks/design-rationale/evaluation-microdata-export.md for the full
specification.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0015_lte_export_grant"),
        ("programs", "0013_program_community_governance_framework"),
        ("reports", "0020_reporttemplate_taxonomy_system"),
    ]

    operations = [
        migrations.AlterField(
            model_name="secureexportlink",
            name="export_type",
            field=models.CharField(
                choices=[
                    ("client_data", "Participant Data"),
                    ("metrics", "Metric Report"),
                    ("standard_report", "Standard Report"),
                    ("individual_client", "Individual Client Export"),
                    ("session_report", "Session Report"),
                    ("evaluation_microdata", "Evaluation Microdata"),
                    (
                        "longitudinal_trajectory_export",
                        "Longitudinal Trajectory Export (Small Population)",
                    ),
                ],
                max_length=50,
            ),
        ),
        migrations.CreateModel(
            name="LTEExportRequest",
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
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("period_start", models.DateField()),
                ("period_end", models.DateField()),
                ("reb_name", models.CharField(max_length=200)),
                ("reb_approval_number", models.CharField(max_length=100)),
                ("reb_approval_date", models.DateField()),
                ("data_sharing_agreement_expiry", models.DateField()),
                ("evaluator_name", models.CharField(max_length=200)),
                ("evaluator_email", models.EmailField(max_length=254)),
                ("evaluator_organisation", models.CharField(max_length=200)),
                ("evaluator_degree", models.CharField(max_length=300)),
                ("evaluator_years_experience", models.PositiveSmallIntegerField()),
                (
                    "evaluator_prior_programs",
                    models.TextField(
                        help_text=(
                            "Auditable narrative of prior evaluation work. "
                            "Minimum 50 characters."
                        ),
                    ),
                ),
                (
                    "destruction_window_days",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (30, "30 days"),
                            (60, "60 days"),
                            (90, "90 days"),
                        ],
                    ),
                ),
                ("purpose_statement", models.TextField()),
                (
                    "community_reviewer_name",
                    models.CharField(blank=True, default="", max_length=200),
                ),
                (
                    "community_reviewer_affiliation",
                    models.CharField(blank=True, default="", max_length=300),
                ),
                (
                    "community_framework_description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text=(
                            "Description of community review framework — "
                            "required for 'other' flag."
                        ),
                    ),
                ),
                ("community_signoff_date", models.DateField(blank=True, null=True)),
                ("acknowledgement_confirmed", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("submitted", "Submitted — review and cancel window"),
                            ("flagged", "Flagged — privacy officer action required"),
                            ("cancelled", "Cancelled"),
                            (
                                "auto_cancelled",
                                "Auto-cancelled — population dropped below floor",
                            ),
                            (
                                "invalidated_by_withdrawal",
                                "Invalidated — participant withdrew consent",
                            ),
                            ("active", "Download link active"),
                            ("downloaded", "Downloaded"),
                            ("expired", "Expired without download"),
                        ],
                        default="submitted",
                        max_length=30,
                    ),
                ),
                ("window_activates_at", models.DateTimeField()),
                ("flag_hold_seconds", models.PositiveIntegerField(default=0)),
                ("flag_hold_started_at", models.DateTimeField(blank=True, null=True)),
                ("population_snapshot", models.PositiveIntegerField()),
                (
                    "population_client_ids",
                    models.JSONField(blank=True, default=list),
                ),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                (
                    "cancellation_reason",
                    models.CharField(blank=True, default="", max_length=500),
                ),
                ("destruction_confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("post_hoc_review_resolved_at", models.DateTimeField(blank=True, null=True)),
                ("post_hoc_review_notes", models.TextField(blank=True, default="")),
                ("linkage_blob_encrypted", models.BinaryField(blank=True, default=b"")),
                (
                    "cancelled_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lte_requests_cancelled",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "destruction_confirmed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lte_destruction_confirmations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "post_hoc_review_resolved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lte_reviews_resolved",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "program",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lte_requests",
                        to="programs.program",
                    ),
                ),
                (
                    "secure_export_link",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="lte_request",
                        to="reports.secureexportlink",
                    ),
                ),
                (
                    "submitted_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lte_requests_submitted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "lte_export_requests",
                "ordering": ["-submitted_at"],
            },
        ),
        migrations.AddIndex(
            model_name="lteexportrequest",
            index=models.Index(
                fields=["status", "window_activates_at"],
                name="lte_req_status_window_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="lteexportrequest",
            index=models.Index(
                fields=["program", "-submitted_at"],
                name="lte_req_program_submitted_idx",
            ),
        ),
        migrations.CreateModel(
            name="LTELifecycleEvent",
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
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("submitted", "Submitted"),
                            ("flagged", "Flagged"),
                            ("flag_resolved", "Flag resolved"),
                            ("cancelled", "Cancelled"),
                            (
                                "auto_cancelled",
                                "Auto-cancelled (population floor)",
                            ),
                            (
                                "withdrawal_invalidation",
                                "Invalidated by withdrawal",
                            ),
                            ("window_activated", "Download link activated"),
                            ("downloaded", "Downloaded"),
                            ("expired", "Expired without download"),
                            (
                                "post_hoc_review_resolved",
                                "Post-hoc review resolved",
                            ),
                            ("destruction_confirmed", "Destruction confirmed"),
                        ],
                        max_length=50,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lte_lifecycle_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lifecycle_events",
                        to="reports.lteexportrequest",
                    ),
                ),
            ],
            options={
                "db_table": "lte_lifecycle_events",
                "ordering": ["timestamp"],
            },
        ),
    ]
