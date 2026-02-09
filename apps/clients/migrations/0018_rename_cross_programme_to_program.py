from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0017_add_cross_programme_sharing_consent'),
    ]

    operations = [
        migrations.RenameField(
            model_name='clientfile',
            old_name='cross_programme_sharing_consent',
            new_name='cross_program_sharing_consent',
        ),
    ]
