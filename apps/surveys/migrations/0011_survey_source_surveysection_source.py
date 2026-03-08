from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("surveys", "0010_encrypt_respondent_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="survey",
            name="source",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Source or citation for the whole survey, e.g. 'PHQ-9 (Kroenke et al., 2001)'.",
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="surveysection",
            name="source",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Source or citation for this section's questions, e.g. 'WHO-5 (WHO, 1998)'.",
                max_length=500,
            ),
        ),
    ]
