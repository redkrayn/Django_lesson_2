from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from geopy.distance import geodesic

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from foodcartapp.models import Product, Restaurant, Order, RestaurantMenuItem
from geocoordapp.models import Place


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {item.restaurant_id: item.availability for item in product.menu_items.all()}
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    orders = Order.objects.total_price().filter(status='accepted').prefetch_related(
        'items__product'
    )

    orders_in_progress = Order.objects.total_price().filter(status='in_progress')
    orders_in_delivery = Order.objects.total_price().filter(status='in_delivery')

    restaurants_items = RestaurantMenuItem.objects.filter(
        availability=True
    ).select_related('restaurant', 'product')

    restaurants = Restaurant.objects.all().select_related()

    order_addresses = [order.address for order in orders]
    restaurant_addresses = [restaurant.address for restaurant in restaurants]

    all_addresses = set(order_addresses + restaurant_addresses)
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

                if (not order_place or not order_place.lat or not order_place.lon or
                    not restaurant_place or not restaurant_place.lat or not restaurant_place.lon):
                    distance = 'ошибка в оценке расстояния, '
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

    return render(
        request,
        template_name='order_items.html',
        context={
            'order_items': orders,
            'order_in_progress': orders_in_progress,
            'order_in_delivery': orders_in_delivery
        }
    )
