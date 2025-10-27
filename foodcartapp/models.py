from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from django.db.models import F, Prefetch, Sum
from geocoordapp.models import Place
from geocoordapp.views import fetch_coordinates
from geopy.distance import geodesic


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

    def with_available_restaurants(self):
        orders = self
        if not orders:
            return orders

        restaurants_items = RestaurantMenuItem.objects.filter(
            availability=True
        ).select_related('restaurant', 'product')

        restaurants = Restaurant.objects.all()

        order_addresses = [order.address for order in orders]
        restaurant_addresses = [restaurant.address for restaurant in restaurants]
        all_addresses = set(order_addresses + restaurant_addresses)

        places = Place.objects.filter(address__in=all_addresses)
        places_dict = {place.address: place for place in places}

        missing_addresses = [address for address in all_addresses
                             if address not in places_dict or
                             not places_dict[address].lat or
                             not places_dict[address].lon]

        for address in missing_addresses:
            from django.conf import settings
            coordinates = fetch_coordinates(settings.GEOAPP_TOKEN, address)

            if coordinates:
                lat, lon = coordinates
                place, created = Place.objects.get_or_create(address=address)
                place.lat = lat
                place.lon = lon
                place.save()
                places_dict[address] = place
            else:
                place, created = Place.objects.get_or_create(address=address)
                place.lat = None
                place.lon = None
                place.save()
                places_dict[address] = place

        places = Place.objects.filter(address__in=all_addresses)
        places_dict = {place.address: place for place in places}

        product_restaurants = {}
        for item in restaurants_items:
            if item.product_id not in product_restaurants:
                product_restaurants[item.product_id] = []
            product_restaurants[item.product_id].append(item.restaurant)

        for order in orders:
            order.available_restaurants = []
            available_restaurants = []

            for item in order.items.all():
                item_restaurants = product_restaurants.get(item.product_id, [])
                item.available_restaurants = [r.id for r in item_restaurants]
                available_restaurants.append(item.available_restaurants)

            if available_restaurants:
                common_restaurants = list(set.intersection(*[set(arr) for arr in available_restaurants]))

                for common_restaurant in common_restaurants:
                    restaurant = next((r for r in restaurants if r.id == common_restaurant), None)
                    if not restaurant:
                        continue

                    order_place = places_dict.get(order.address)
                    restaurant_place = places_dict.get(restaurant.address)

                    if not order_place or not order_place.lat or not order_place.lon:
                        distance = 'адрес не найден'
                        order.available_restaurants.append({restaurant.name: distance})
                    elif not restaurant_place or not restaurant_place.lat or not restaurant_place.lon:
                        distance = 'адрес ресторана не найден'
                        order.available_restaurants.append({restaurant.name: distance})
                    else:
                        distance = round(geodesic(
                            (order_place.lat, order_place.lon),
                            (restaurant_place.lat, restaurant_place.lon)
                        ).km, 2)
                        order.available_restaurants.append({restaurant.name: distance})

            order.available_restaurants = sorted(order.available_restaurants, key=lambda x: (
                0, list(x.values())[0]) if isinstance(list(x.values())[0], (int, float)) else (
                1, str(list(x.values())[0])))

        return orders


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
        max_length=20
    )
    lastname = models.CharField(
        verbose_name='Фамилия',
        max_length=20
    )
    phonenumber = PhoneNumberField(
        verbose_name='Номер телефона',
        db_index=True
    )
    address = models.CharField(
        verbose_name='Адрес',
        max_length=50
    )
    status = models.CharField(
        choices=ORDER_STATUS,
        max_length=50,
        default='accepted',
        verbose_name='Статус',
        db_index=True,
    )
    payment_method = models.CharField(
        choices=PAYMENT_METHOD,
        max_length=30,
        verbose_name='Способ оплаты',
        db_index=True
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
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Ресторан',
        blank=True,
        null=True
    )

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f"{self.firstname} {self.lastname} {self.address}"


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
        verbose_name='товар',
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='количество',
        validators=[MinValueValidator(1)]
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
