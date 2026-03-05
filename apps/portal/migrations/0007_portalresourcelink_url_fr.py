from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0006_portalalliancerequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="portalresourcelink",
            name="url_fr",
            field=models.URLField(blank=True, default=""),
        ),
    ]
