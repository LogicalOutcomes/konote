from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0016_reporttemplate_html_template_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="reporttemplate",
            name="include_all_metrics",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "When checked, the report includes every metric with recorded "
                    "data in the selected period. Use for org-wide or board reports. "
                    "Leave unchecked for funder reports that require specific metrics."
                ),
            ),
        ),
    ]
