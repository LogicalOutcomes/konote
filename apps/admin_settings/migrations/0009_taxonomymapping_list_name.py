from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_settings", "0008_taxonomymapping_review_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="taxonomymapping",
            name="taxonomy_list_name",
            field=models.CharField(blank=True, default="", help_text="Specific code list used for this mapping, e.g. SDGImpacts or IrisMetric53.", max_length=100),
        ),
    ]