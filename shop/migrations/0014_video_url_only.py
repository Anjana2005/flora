from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0013_stylereel'),
    ]

    operations = [
        # ProductVideo: file → external URL only
        migrations.AddField(
            model_name='productvideo',
            name='video_url',
            field=models.URLField(
                default='',
                help_text='Direct video link (mp4/webm) or hosted URL — not uploaded to this server',
                max_length=500,
            ),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name='productvideo',
            name='video',
        ),
        # StyleReel: file → external URL only
        migrations.AddField(
            model_name='stylereel',
            name='video_url',
            field=models.URLField(
                default='',
                help_text='Direct video link (mp4/webm). Files are not uploaded to this server.',
                max_length=500,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='stylereel',
            name='poster_url',
            field=models.URLField(
                blank=True,
                default='',
                help_text='Optional thumbnail image URL',
                max_length=500,
            ),
        ),
        migrations.RemoveField(
            model_name='stylereel',
            name='video',
        ),
        migrations.RemoveField(
            model_name='stylereel',
            name='poster',
        ),
    ]
