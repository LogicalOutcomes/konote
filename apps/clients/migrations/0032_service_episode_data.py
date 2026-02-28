# Data migration: convert existing enrolment rows to ServiceEpisode format.
#
# For each existing row:
#   1. Set started_at = enrolled_at
#   2. Set status: "enrolled" → "active", "unenrolled" → "finished"
#   3. Set ended_at = unenrolled_at (if unenrolled)
#   4. Leave episode_type, end_reason, referral_source blank (unknown for historical)
#   5. Create initial ServiceEpisodeStatusChange row

from django.db import migrations


def migrate_enrolments_forward(apps, schema_editor):
    """Convert existing enrolled/unenrolled rows to active/finished."""
    ServiceEpisode = apps.get_model('clients', 'ServiceEpisode')
    StatusChange = apps.get_model('clients', 'ServiceEpisodeStatusChange')

    for episode in ServiceEpisode.objects.all():
        # Map old status values to new
        if episode.status == "enrolled":
            episode.status = "active"
        elif episode.status == "unenrolled":
            episode.status = "finished"
            episode.ended_at = episode.unenrolled_at
        # else: leave as-is (shouldn't happen, but be safe)

        # Set started_at from enrolled_at
        episode.started_at = episode.enrolled_at

        episode.save(update_fields=[
            "status", "started_at", "ended_at",
        ])

        # Create initial status change record
        StatusChange.objects.create(
            episode=episode,
            status=episode.status,
            reason="Migrated from ClientProgramEnrolment",
            changed_at=episode.enrolled_at,
        )


def migrate_enrolments_reverse(apps, schema_editor):
    """Convert back to enrolled/unenrolled for rollback."""
    ServiceEpisode = apps.get_model('clients', 'ServiceEpisode')
    StatusChange = apps.get_model('clients', 'ServiceEpisodeStatusChange')

    for episode in ServiceEpisode.objects.all():
        if episode.status == "active":
            episode.status = "enrolled"
        elif episode.status in ("finished", "cancelled"):
            episode.status = "unenrolled"
        elif episode.status in ("planned", "waitlist", "on_hold"):
            episode.status = "enrolled"  # best approximation
        episode.save(update_fields=["status"])

    # Remove migration-created status changes
    StatusChange.objects.filter(
        reason="Migrated from ClientProgramEnrolment",
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0031_service_episode'),
    ]

    operations = [
        migrations.RunPython(
            migrate_enrolments_forward,
            migrate_enrolments_reverse,
        ),
    ]
