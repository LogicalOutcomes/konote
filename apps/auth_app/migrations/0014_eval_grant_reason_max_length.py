"""EVAL-GOV1 follow-up — Add max_length=2000 to EvaluationExportGrant.reason.

Defense-in-depth against admins (or bots) posting arbitrarily long
narrative reasons. Also matters for privacy-officer review ergonomics:
scrolling through kilobytes of free-text per grant is a burden. 2000
characters is enough for several sentences of authorising context.

PostgreSQL stores TextField as `text` regardless of max_length — this
migration only changes Django-level validation, not the column type.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0013_backfill_eval_export_grants"),
    ]

    operations = [
        migrations.AlterField(
            model_name="evaluationexportgrant",
            name="reason",
            field=models.TextField(
                max_length=2000,
                help_text=(
                    "Why this grant was issued — typically references the ED's "
                    "authorisation and the evaluation engagement. Max 2000 chars "
                    "so privacy officers can review the audit log without wading "
                    "through page-length narratives."
                ),
            ),
        ),
    ]
