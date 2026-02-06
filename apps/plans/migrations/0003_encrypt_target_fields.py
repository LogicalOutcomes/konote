"""
Encrypt PlanTarget and PlanTargetRevision fields: name, description, status_reason.

Three-phase migration:
1. Add new _encrypted BinaryFields alongside existing plaintext columns
2. Copy plaintext data into encrypted fields (data migration)
3. Remove old plaintext columns

IMPORTANT: Back up the database before running this migration.
"""
from django.db import migrations, models


def encrypt_existing_data(apps, schema_editor):
    """Encrypt existing plaintext values into the new binary fields."""
    from konote.encryption import encrypt_field

    PlanTarget = apps.get_model("plans", "PlanTarget")
    PlanTargetRevision = apps.get_model("plans", "PlanTargetRevision")

    # Encrypt PlanTarget rows
    count = 0
    for target in PlanTarget.objects.all():
        target._name_encrypted = encrypt_field(target.name_plaintext or "")
        target._description_encrypted = encrypt_field(target.description_plaintext or "")
        target._status_reason_encrypted = encrypt_field(target.status_reason_plaintext or "")
        target.save(update_fields=[
            "_name_encrypted", "_description_encrypted", "_status_reason_encrypted",
        ])
        count += 1
    if count:
        print(f"  Encrypted {count} PlanTarget rows")

    # Encrypt PlanTargetRevision rows
    count = 0
    for rev in PlanTargetRevision.objects.all():
        rev._name_encrypted = encrypt_field(rev.name_plaintext or "")
        rev._description_encrypted = encrypt_field(rev.description_plaintext or "")
        rev._status_reason_encrypted = encrypt_field(rev.status_reason_plaintext or "")
        rev.save(update_fields=[
            "_name_encrypted", "_description_encrypted", "_status_reason_encrypted",
        ])
        count += 1
    if count:
        print(f"  Encrypted {count} PlanTargetRevision rows")


def decrypt_existing_data(apps, schema_editor):
    """Reverse: copy encrypted values back to plaintext fields."""
    from konote.encryption import decrypt_field

    PlanTarget = apps.get_model("plans", "PlanTarget")
    PlanTargetRevision = apps.get_model("plans", "PlanTargetRevision")

    for target in PlanTarget.objects.all():
        target.name_plaintext = decrypt_field(target._name_encrypted)
        target.description_plaintext = decrypt_field(target._description_encrypted)
        target.status_reason_plaintext = decrypt_field(target._status_reason_encrypted)
        target.save(update_fields=[
            "name_plaintext", "description_plaintext", "status_reason_plaintext",
        ])

    for rev in PlanTargetRevision.objects.all():
        rev.name_plaintext = decrypt_field(rev._name_encrypted)
        rev.description_plaintext = decrypt_field(rev._description_encrypted)
        rev.status_reason_plaintext = decrypt_field(rev._status_reason_encrypted)
        rev.save(update_fields=[
            "name_plaintext", "description_plaintext", "status_reason_plaintext",
        ])


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0002_add_client_goal"),
    ]

    operations = [
        # Phase 1: Add encrypted fields + rename old fields to _plaintext
        # Rename old plaintext columns so both can coexist
        migrations.RenameField(
            model_name="plantarget",
            old_name="name",
            new_name="name_plaintext",
        ),
        migrations.RenameField(
            model_name="plantarget",
            old_name="description",
            new_name="description_plaintext",
        ),
        migrations.RenameField(
            model_name="plantarget",
            old_name="status_reason",
            new_name="status_reason_plaintext",
        ),
        migrations.RenameField(
            model_name="plantargetrevision",
            old_name="name",
            new_name="name_plaintext",
        ),
        migrations.RenameField(
            model_name="plantargetrevision",
            old_name="description",
            new_name="description_plaintext",
        ),
        migrations.RenameField(
            model_name="plantargetrevision",
            old_name="status_reason",
            new_name="status_reason_plaintext",
        ),
        # Add new encrypted binary fields
        migrations.AddField(
            model_name="plantarget",
            name="_name_encrypted",
            field=models.BinaryField(blank=True, default=b""),
        ),
        migrations.AddField(
            model_name="plantarget",
            name="_description_encrypted",
            field=models.BinaryField(blank=True, default=b""),
        ),
        migrations.AddField(
            model_name="plantarget",
            name="_status_reason_encrypted",
            field=models.BinaryField(blank=True, default=b""),
        ),
        migrations.AddField(
            model_name="plantargetrevision",
            name="_name_encrypted",
            field=models.BinaryField(blank=True, default=b""),
        ),
        migrations.AddField(
            model_name="plantargetrevision",
            name="_description_encrypted",
            field=models.BinaryField(blank=True, default=b""),
        ),
        migrations.AddField(
            model_name="plantargetrevision",
            name="_status_reason_encrypted",
            field=models.BinaryField(blank=True, default=b""),
        ),
        # Phase 2: Encrypt existing data
        migrations.RunPython(encrypt_existing_data, decrypt_existing_data),
        # Phase 3: Remove old plaintext columns
        migrations.RemoveField(
            model_name="plantarget",
            name="name_plaintext",
        ),
        migrations.RemoveField(
            model_name="plantarget",
            name="description_plaintext",
        ),
        migrations.RemoveField(
            model_name="plantarget",
            name="status_reason_plaintext",
        ),
        migrations.RemoveField(
            model_name="plantargetrevision",
            name="name_plaintext",
        ),
        migrations.RemoveField(
            model_name="plantargetrevision",
            name="description_plaintext",
        ),
        migrations.RemoveField(
            model_name="plantargetrevision",
            name="status_reason_plaintext",
        ),
    ]
