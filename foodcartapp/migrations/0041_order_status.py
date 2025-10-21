from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0040_alter_orderitem_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('accepted', 'Принят'), ('in_progress', 'Собирается'), ('in_delivery', 'Доставляется'), ('completed', 'Завершён')], db_index=True, default='accepted', max_length=50, verbose_name='Статус'),
        ),
    ]
