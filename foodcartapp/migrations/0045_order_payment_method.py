from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0044_alter_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(choices=[('cash', 'Наличностью'), ('web_cash', 'Электронно')], db_index=True, default='cash', max_length=30, verbose_name='Способ оплаты'),
        ),
    ]
