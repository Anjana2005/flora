from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0005_add_offersale_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productsize',
            name='size',
            field=models.CharField(
                choices=[
                    ('M', 'Medium'),
                    ('L', 'Large'),
                    ('XL', 'XL'),
                    ('2XL', '2XL'),
                    ('3XL', '3XL'),
                    ('16', '16 (1 Year)'),
                    ('18', '18 (2 Years)'),
                    ('20', '20 (3 Years)'),
                    ('22', '22 (4 Years)'),
                    ('24', '24 (5-6 Years)'),
                    ('26', '26 (7-8 Years)'),
                    ('28', '28 (9-10 Years)'),
                    ('30', '30 (11-12 Years)'),
                ],
                max_length=10,
            ),
        ),
    ]
