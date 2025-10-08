from rest_framework import serializers
from foodcartapp.models import Product, OrderItem, Order
from phonenumbers import parse, is_valid_number, NumberParseException


class OrderItemSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class OrderSerializer(serializers.Serializer):
    firstname = serializers.CharField(allow_blank=True, required=False, default="")
    lastname = serializers.CharField()
    phonenumber = serializers.CharField()
    address = serializers.CharField()
    products = OrderItemSerializer(many=True)

    def validate_phonenumber(self, value):
        try:
            phone_number = parse(value, "RU")

            if not is_valid_number(phone_number):
                raise serializers.ValidationError("Введен некорректный номер телефона")

        except NumberParseException:
            raise serializers.ValidationError("Введен некорректный номер телефона")

        return value

    def validate_products(self, value):
        if not value:
            raise serializers.ValidationError("Заказ должен содержать хотя бы один товар")

        product_ids = [item['product'] for item in value]
        existing_products = Product.objects.filter(id__in=product_ids)
        existing_product_ids = set(existing_products.values_list('id', flat=True))
        non_existing_products = set(product_ids) - existing_product_ids

        if non_existing_products:
            raise serializers.ValidationError(
                f"Продукты с ID {list(non_existing_products)} не существуют"
            )

        return value

    def create(self, validated_data):
        products_data = validated_data.pop('products')

        order = Order.objects.create(
            firstname=validated_data.get('firstname', ''),
            lastname=validated_data['lastname'],
            phone_number=validated_data['phonenumber'],
            address=validated_data['address']
        )

        for item in products_data:
            product = Product.objects.get(id=item['product'])
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item['quantity'],
                price=product.price
            )

        return order
