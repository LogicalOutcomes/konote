"""Backfill author_role from current UserProgramRole for existing notes.

Note: This uses CURRENT roles, which may not match the role the author
had when the note was originally created.  This is acceptable for
historical data — the field is most accurate going forward.
"""

from django.db import migrations


def backfill_author_role(apps, schema_editor):
    ProgressNote = apps.get_model("notes", "ProgressNote")
    UserProgramRole = apps.get_model("programs", "UserProgramRole")

    # Only fill notes that have both author and author_program set
    notes = ProgressNote.objects.filter(
        author_role="",
        author__isnull=False,
        author_program__isnull=False,
    ).select_related()

    updated = 0
    for note in notes.iterator(chunk_size=500):
        role_obj = UserProgramRole.objects.filter(
            user_id=note.author_id,
            program_id=note.author_program_id,
            status="active",
        ).first()
        if role_obj:
            note.author_role = role_obj.role
            note.save(update_fields=["author_role"])
            updated += 1

    if updated:
        print(f"  Backfilled author_role on {updated} notes (using current roles)")


def reverse_backfill(apps, schema_editor):
    ProgressNote = apps.get_model("notes", "ProgressNote")
    ProgressNote.objects.exclude(author_role="").update(author_role="")


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "0023_session4_achievement_role"),
        ("programs", "0009_program_cids_sector_code_program_description_fr_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_author_role, reverse_backfill),
    ]
