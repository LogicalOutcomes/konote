# Generated manually for SCALE-ROLLUP1

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("consortia", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="consortiummembership",
            name="is_consortium_lead",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Consortium leads see aggregated data across all partner agencies. "
                    "Regular members see only their own published data."
                ),
            ),
        ),
    ]
