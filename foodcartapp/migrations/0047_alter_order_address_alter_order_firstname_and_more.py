import phonenumber_field.modelfields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0046_order_restaurant_alter_orderitem_quantity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='address',
            field=models.CharField(default='Unknown', max_length=50, verbose_name='Адрес'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='order',
            name='firstname',
            field=models.CharField(default='Unknown', max_length=20, verbose_name='Имя'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='order',
            name='lastname',
            field=models.CharField(default='Unknown', max_length=20, verbose_name='Фамилия'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='order',
            name='phonenumber',
            field=phonenumber_field.modelfields.PhoneNumberField(db_index=True, default='Unknown', max_length=128, region=None, verbose_name='Номер телефона'),
            preserve_default=False,
        ),
    ]
