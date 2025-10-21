from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from django.db.models import F, Prefetch, Sum


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):
    def total_price(self):
        return (
            self.prefetch_related(
                Prefetch(
                    'items',
                    queryset=OrderItem.objects.select_related('product')
                )
            )
            .annotate(
                total_price=Sum(
                    F('items__quantity') * F('items__price')
                )
            )
        )


class Order(models.Model):
    PAYMENT_METHOD = [
        ('cash', 'Наличностью'),
        ('web_cash', 'Электронно'),
    ]
    ORDER_STATUS = [
        ('accepted', 'Не обработан'),
        ('in_progress', 'В сборке'),
        ('in_delivery', 'В доставке'),
        ('completed', 'Завершён'),
    ]
    firstname = models.CharField(
        verbose_name='Имя',
        max_length=20,
        blank=True,
        null=True
    )
    lastname = models.CharField(
        verbose_name='Фамилия',
        max_length=20,
        blank=True,
        null=True
    )
    phonenumber = PhoneNumberField(
        verbose_name='Номер телефона',
        blank=True,
        null=True,
        db_index=True
    )
    address = models.CharField(
        verbose_name='Адрес',
        max_length=50,
        blank=True,
        null=True
    )
    status = models.CharField(
        choices=ORDER_STATUS,
        max_length=50,
        default='accepted',
        verbose_name='Статус',
        db_index=True,
    )
    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий'
    )
    registered_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата оформления заказа',
        db_index=True
    )
    called_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Дата звонка',
        db_index=True
    )
    delivered_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Дата доставки',
        db_index=True
    )
    payment_method = models.CharField(
        choices=PAYMENT_METHOD,
        default='cash',
        max_length=30,
        verbose_name='Способ оплаты',
        db_index=True
    )

    def __str__(self):
        return f"{self.firstname} {self.lastname} {self.address}"

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name='заказ',
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='товар'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='количество'
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='цена на момент заказа',
        validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = 'элемент заказа'
        verbose_name_plural = 'элементы заказа'

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
