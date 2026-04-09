"""EVAL-GOV1 — Add EvaluationExportGrant model.

Grant records carry who granted, when, and the reason (governance
requirement from tasks/eval-export-governance.md). Revocation preserves
the granting row for audit by setting active=False; a partial unique
constraint keeps at most one active grant per user at a time.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0011_user_evaluation_export_granted"),
    ]

    operations = [
        migrations.CreateModel(
            name="EvaluationExportGrant",
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
                ("granted_at", models.DateTimeField(auto_now_add=True)),
                (
                    "reason",
                    models.TextField(
                        help_text=(
                            "Why this grant was issued — typically references "
                            "the ED's authorisation and the evaluation engagement."
                        ),
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "granted_by",
                    models.ForeignKey(
                        blank=True,
                        help_text=(
                            "Admin who issued the grant. Null only for backfilled "
                            "legacy rows."
                        ),
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="evaluation_export_grants_issued",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "revoked_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="evaluation_export_grants_revoked",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evaluation_export_grants",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "evaluation_export_grants",
                "ordering": ["-granted_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="evaluationexportgrant",
            constraint=models.UniqueConstraint(
                condition=models.Q(("active", True)),
                fields=("user",),
                name="one_active_eval_export_grant_per_user",
            ),
        ),
    ]
