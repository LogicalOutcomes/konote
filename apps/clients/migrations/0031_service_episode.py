# Hand-written migration: rename ClientProgramEnrolment → ServiceEpisode
# and add new FHIR-informed fields. Uses RenameModel to preserve data.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0030_seed_dv_sensitive_defaults'),
        ('programs', '0009_program_cids_sector_code_program_description_fr_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Rename the model (db_table is explicit, so table stays the same)
        migrations.RenameModel(
            old_name='ClientProgramEnrolment',
            new_name='ServiceEpisode',
        ),

        # Step 2: Update status field choices (no schema change needed —
        # CharField max_length=20 is sufficient for all new values)
        migrations.AlterField(
            model_name='serviceepisode',
            name='status',
            field=models.CharField(
                choices=[
                    ('planned', 'Planned'),
                    ('waitlist', 'Waitlisted'),
                    ('active', 'Active'),
                    ('on_hold', 'On Hold'),
                    ('finished', 'Finished'),
                    ('cancelled', 'Cancelled'),
                ],
                default='active',
                max_length=20,
            ),
        ),

        # Step 3: Add new fields
        migrations.AddField(
            model_name='serviceepisode',
            name='status_reason',
            field=models.TextField(
                blank=True, default='',
                help_text='Why the status changed.',
            ),
        ),
        migrations.AddField(
            model_name='serviceepisode',
            name='episode_type',
            field=models.CharField(
                blank=True, default='',
                choices=[
                    ('new_intake', 'New Intake'),
                    ('re_enrolment', 'Re-enrolment'),
                    ('transfer_in', 'Transfer In'),
                    ('crisis', 'Crisis'),
                    ('short_term', 'Short-term'),
                ],
                help_text='Auto-derived from enrolment history. Do not set manually.',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='serviceepisode',
            name='primary_worker',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Assigned case worker.',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='primary_episodes',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='serviceepisode',
            name='referral_source',
            field=models.CharField(
                blank=True, default='',
                choices=[
                    ('', '— Not specified —'),
                    ('self', 'Self'),
                    ('family', 'Family'),
                    ('agency_internal', 'Agency (internal)'),
                    ('agency_external', 'Agency (external)'),
                    ('healthcare', 'Healthcare'),
                    ('school', 'School'),
                    ('court', 'Court'),
                    ('shelter', 'Shelter'),
                    ('community', 'Community'),
                    ('other', 'Other'),
                ],
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='serviceepisode',
            name='started_at',
            field=models.DateTimeField(
                blank=True, null=True,
                help_text='When active service began.',
            ),
        ),
        migrations.AddField(
            model_name='serviceepisode',
            name='ended_at',
            field=models.DateTimeField(
                blank=True, null=True,
                help_text='When service ended.',
            ),
        ),
        migrations.AddField(
            model_name='serviceepisode',
            name='end_reason',
            field=models.CharField(
                blank=True, default='',
                choices=[
                    ('', '— Not specified —'),
                    ('completed', 'Completed'),
                    ('goals_met', 'Goals Met'),
                    ('withdrew', 'Withdrew'),
                    ('transferred', 'Transferred'),
                    ('referred_out', 'Referred Out'),
                    ('lost_contact', 'Lost Contact'),
                    ('moved', 'Moved'),
                    ('ineligible', 'Ineligible'),
                    ('deceased', 'Deceased'),
                    ('other', 'Other'),
                ],
                max_length=30,
            ),
        ),

        # Step 4: Create the status change history table
        migrations.CreateModel(
            name='ServiceEpisodeStatusChange',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID',
                )),
                ('status', models.CharField(
                    help_text='The new status value.', max_length=20,
                )),
                ('reason', models.TextField(
                    blank=True, default='',
                    help_text='Why the status changed.',
                )),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('changed_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
                ('episode', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='status_changes',
                    to='clients.serviceepisode',
                )),
            ],
            options={
                'db_table': 'service_episode_status_changes',
                'ordering': ['changed_at'],
            },
        ),
        migrations.AddIndex(
            model_name='serviceepisodestatuschange',
            index=models.Index(
                fields=['episode', 'changed_at'],
                name='service_epi_episode_c2eb31_idx',
            ),
        ),
    ]
