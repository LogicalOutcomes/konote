from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_settings", "0009_taxonomymapping_list_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="taxonomymapping",
            name="mapping_source",
            field=models.CharField(choices=[("manual", "Manual"), ("imported", "Imported"), ("system_suggested", "System suggested"), ("ai_suggested", "AI suggested")], default="manual", help_text="How this mapping was created: manual review, import, or AI suggestion.", max_length=20),
        ),
        migrations.AlterField(
            model_name="taxonomymapping",
            name="taxonomy_system",
            field=models.CharField(choices=[("common_approach", "Common Approach"), ("iris_plus", "IRIS+"), ("sdg", "SDG"), ("cids_iris", "CIDS / IRIS+"), ("united_way", "United Way"), ("phac", "Public Health Agency of Canada"), ("provincial", "Provincial"), ("esdc", "ESDC"), ("custom", "Custom")], help_text='e.g., "cids_iris", "united_way", "phac".', max_length=50),
        ),
    ]