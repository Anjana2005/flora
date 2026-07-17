from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0008_mediablob'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payer_upi_id',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_ref',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Optional UTR / transaction reference',
                max_length=64,
            ),
        ),
    ]
