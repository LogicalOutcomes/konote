from django.db import migrations, models


def migrate_boolean_to_tristate(apps, schema_editor):
    """Convert old Boolean (True/False) to new tri-state (consent/default)."""
    ClientFile = apps.get_model("clients", "ClientFile")
    # True → "consent" (explicit opt-in), False → "default" (follow agency)
    ClientFile.objects.filter(cross_program_sharing_consent=True).update(
        cross_program_sharing_consent="consent"
    )
    ClientFile.objects.filter(cross_program_sharing_consent=False).update(
        cross_program_sharing_consent="default"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("clients", "0022_fix_contact_field_ordering"),
    ]

    operations = [
        # Step 1: Change field type from BooleanField to CharField (keeps old name)
        migrations.AlterField(
            model_name="clientfile",
            name="cross_program_sharing_consent",
            field=models.CharField(
                max_length=20,
                default="default",
                help_text="Controls whether clinical notes are visible across programs for this participant. Most participants use the agency default.",
            ),
        ),
        # Step 2: Migrate data (True→"consent", False→"default")
        migrations.RunPython(migrate_boolean_to_tristate, migrations.RunPython.noop),
        # Step 3: Rename field
        migrations.RenameField(
            model_name="clientfile",
            old_name="cross_program_sharing_consent",
            new_name="cross_program_sharing",
        ),
    ]
