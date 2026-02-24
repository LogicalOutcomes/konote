"""Add DataAccessRequest model for PIPEDA Section 8 data access tracking."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0024_erasure_scheduled_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DataAccessRequest",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requested_at", models.DateField(help_text="Date the access request was received.")),
                ("request_method", models.CharField(choices=[("verbal", "Verbal"), ("written", "Written"), ("email", "Email")], max_length=20)),
                ("deadline", models.DateField(help_text="Auto-set to requested_at + 30 days.")),
                ("completed_at", models.DateField(blank=True, null=True)),
                ("delivery_method", models.CharField(blank=True, choices=[("in_person", "In person"), ("mail", "Mail"), ("email", "Email")], max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("client_file", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="data_access_requests", to="clients.clientfile")),
                ("completed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="data_access_completions", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="data_access_requests_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "data_access_requests",
                "ordering": ["-created_at"],
            },
        ),
    ]
