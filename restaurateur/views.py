from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from foodcartapp.models import Product, Restaurant, Order
from geocoordapp.models import Place
from geocoordapp.views import fetch_coordinates
from geopy.distance import geodesic

from star_burger import settings


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
    orders = Order.objects.total_price().filter(
        status='accepted'
    ).prefetch_related(
        'items__product'
    ).select_related(
        'restaurant'
    ).with_available_restaurants()

    restaurants = Restaurant.objects.all()

    all_addresses = set()
    for order in orders:
        all_addresses.add(order.address)
        for restaurant_id in getattr(order, 'available_restaurant_ids', []):
            restaurant = next((r for r in restaurants if r.id == restaurant_id), None)
            if restaurant:
                all_addresses.add(restaurant.address)

    places = Place.objects.filter(address__in=all_addresses)
    existing_places = {place.address: place for place in places}

    missing_addresses = [address for address in all_addresses
                         if address not in existing_places or
                         not existing_places[address].lat or
                         not existing_places[address].lon]

    for address in missing_addresses:
        coordinates = fetch_coordinates(settings.GEOAPP_TOKEN, address)
        if coordinates:
            lat, lon = coordinates
            place, created = Place.objects.get_or_create(address=address)
            place.lat = lat
            place.lon = lon
            place.save()
            existing_places[address] = place
        else:
            place, created = Place.objects.get_or_create(address=address)
            existing_places[address] = place

    places_dict = existing_places

    for order in orders:
        order.available_restaurants = []
        order.address_not_found = False

        order_place = places_dict.get(order.address)
        if not order_place or not order_place.lat or not order_place.lon:
            order.address_not_found = True
        else:
            for restaurant_id in getattr(order, 'available_restaurant_ids', []):
                restaurant = next((r for r in restaurants if r.id == restaurant_id), None)
                if not restaurant:
                    continue

                restaurant_place = places_dict.get(restaurant.address)

                if not restaurant_place or not restaurant_place.lat or not restaurant_place.lon:
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

    orders_in_progress = Order.objects.total_price().filter(status='in_progress').select_related(
        'restaurant'
    )
    orders_in_delivery = Order.objects.total_price().filter(status='in_delivery').select_related(
        'restaurant'
    )

    return render(
        request,
        template_name='order_items.html',
        context={
            'order_items': orders,
            'order_in_progress': orders_in_progress,
            'order_in_delivery': orders_in_delivery
        }
    )
