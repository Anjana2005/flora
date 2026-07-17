from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0007_alter_offersale_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaBlob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(db_index=True, max_length=500, unique=True)),
                ('data', models.BinaryField()),
                ('content_type', models.CharField(default='image/jpeg', max_length=100)),
                ('size', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['path'],
            },
        ),
    ]
