import django.db.models.deletion
import phonenumber_field.modelfields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0037_auto_20210125_1833'),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('firstname', models.CharField(blank=True, max_length=20, null=True, verbose_name='Имя')),
                ('lastname', models.CharField(blank=True, max_length=20, null=True, verbose_name='Фамилия')),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(blank=True, db_index=True, max_length=128, null=True, region=None, verbose_name='Номер телефона')),
                ('address', models.CharField(blank=True, max_length=50, null=True, verbose_name='Адрес')),
            ],
            options={
                'verbose_name': 'Заказ',
                'verbose_name_plural': 'Заказы',
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='количество')),
                ('price', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='цена на момент заказа')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='foodcartapp.order', verbose_name='заказ')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='foodcartapp.product', verbose_name='товар')),
            ],
            options={
                'verbose_name': 'элемент заказа',
                'verbose_name_plural': 'элементы заказа',
            },
        ),
    ]
