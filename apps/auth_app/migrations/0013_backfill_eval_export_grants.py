"""EVAL-GOV1 — Backfill EvaluationExportGrant rows for pre-existing grants.

Any user who already has `evaluation_export_granted=True` predates the
grant model and has no recorded reason. Create a placeholder grant row
so the audit trail is complete. `granted_by` is left null — we cannot
retroactively know who issued the grant.

Idempotent: re-running the migration is a no-op because the existence
check skips users who already have an active grant.
"""
from django.db import migrations


PLACEHOLDER_REASON = (
    "Pre-EVAL-GOV1 grant — reason not recorded. This user held "
    "evaluation_export_granted=True before the grant audit model existed. "
    "Review the grant and revoke/re-issue with a current reason if needed."
)


def backfill_grants(apps, schema_editor):
    User = apps.get_model("auth_app", "User")
    EvaluationExportGrant = apps.get_model("auth_app", "EvaluationExportGrant")

    for user in User.objects.filter(evaluation_export_granted=True):
        if EvaluationExportGrant.objects.filter(user=user, active=True).exists():
            continue
        EvaluationExportGrant.objects.create(
            user=user,
            granted_by=None,
            reason=PLACEHOLDER_REASON,
            active=True,
        )


def reverse_backfill(apps, schema_editor):
    """Remove only the placeholder rows we created."""
    EvaluationExportGrant = apps.get_model("auth_app", "EvaluationExportGrant")
    EvaluationExportGrant.objects.filter(reason=PLACEHOLDER_REASON).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0012_evaluation_export_grant"),
    ]

    operations = [
        migrations.RunPython(backfill_grants, reverse_backfill),
    ]
