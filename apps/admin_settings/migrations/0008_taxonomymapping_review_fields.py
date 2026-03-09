from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("admin_settings", "0007_migrate_messaging_profile"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="taxonomymapping",
            name="confidence_score",
            field=models.FloatField(blank=True, help_text="Optional confidence score for imported or AI-suggested mappings, from 0.0 to 1.0.", null=True, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)]),
        ),
        migrations.AddField(
            model_name="taxonomymapping",
            name="mapping_source",
            field=models.CharField(choices=[("manual", "Manual"), ("imported", "Imported"), ("ai_suggested", "AI suggested")], default="manual", help_text="How this mapping was created: manual review, import, or AI suggestion.", max_length=20),
        ),
        migrations.AddField(
            model_name="taxonomymapping",
            name="mapping_status",
            field=models.CharField(choices=[("draft", "Draft"), ("approved", "Approved"), ("rejected", "Rejected"), ("superseded", "Superseded")], default="approved", help_text="Review state for this mapping: draft suggestions remain separate from approved report mappings.", max_length=20),
        ),
        migrations.AddField(
            model_name="taxonomymapping",
            name="rationale",
            field=models.TextField(blank=True, default="", help_text="Why this mapping was suggested or approved."),
        ),
        migrations.AddField(
            model_name="taxonomymapping",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, help_text="When this mapping was last reviewed.", null=True),
        ),
        migrations.AddField(
            model_name="taxonomymapping",
            name="reviewed_by",
            field=models.ForeignKey(blank=True, help_text="User who last reviewed this mapping.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_taxonomy_mappings", to=settings.AUTH_USER_MODEL),
        ),
    ]