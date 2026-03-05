from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0015_add_suppression_threshold_to_report_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="reporttemplate",
            name="html_template_name",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Optional custom Django template path for HTML export "
                    "(e.g., 'reports/html_united_way.html'). "
                    "When blank, the default HTML report template is used."
                ),
                max_length=255,
            ),
        ),
    ]
