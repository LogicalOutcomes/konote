"""LTE — Add LTEExportGrant model + User.lte_export_granted cache flag.

Mirrors the EvaluationExportGrant pattern but is a strictly separate
permission. The DRR treats LTE as a structurally separate path that
must not be bundled with EME access (see
tasks/design-rationale/evaluation-microdata-export.md, "Anti-Patterns
— Do Not Build").
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0014_eval_grant_reason_max_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="lte_export_granted",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Cached flag — set by LTEExportGrant signal. "
                    "Do not edit directly; use the LTE Privacy Officer admin UI."
                ),
            ),
        ),
        migrations.CreateModel(
            name="LTEExportGrant",
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
                        max_length=2000,
                        help_text=(
                            "Why this grant was issued — typically references "
                            "the board or ED decision to designate this user as "
                            "the agency's LTE privacy officer. Max 2000 chars "
                            "so reviewers can scan the audit log without "
                            "wading through page-length narratives."
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
                            "Admin who issued the grant. Null only for "
                            "backfilled legacy rows."
                        ),
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lte_export_grants_issued",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "revoked_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lte_export_grants_revoked",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lte_export_grants",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "lte_export_grants",
                "ordering": ["-granted_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="lteexportgrant",
            constraint=models.UniqueConstraint(
                condition=models.Q(("active", True)),
                fields=("user",),
                name="one_active_lte_export_grant_per_user",
            ),
        ),
    ]
