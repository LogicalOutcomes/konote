# Generated manually — adds contains_pii field to SecureExportLink for
# defense-in-depth PII access control on report downloads.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0002_add_insight_summary"),
    ]

    operations = [
        migrations.AddField(
            model_name="secureexportlink",
            name="contains_pii",
            field=models.BooleanField(default=True),
        ),
    ]
