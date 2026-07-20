from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0012_productvideo'),
    ]

    operations = [
        migrations.CreateModel(
            name='StyleReel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, default='', max_length=200)),
                ('video', models.FileField(upload_to='reels/')),
                ('poster', models.ImageField(blank=True, null=True, upload_to='reels/posters/')),
                ('active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0, help_text='Lower numbers appear first in the homepage carousel')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(
                    blank=True,
                    help_text='Optional product to open when shoppers tap Shop look',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='style_reels',
                    to='shop.product',
                )),
            ],
            options={
                'verbose_name': 'style reel',
                'verbose_name_plural': 'style reels',
                'ordering': ['sort_order', '-created_at'],
            },
        ),
    ]
