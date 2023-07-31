from decimal import Decimal

from django.db import transaction

from rest_framework import serializers

from .models import *


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ["id", "title", "products_count"]

    # Marked as read only because product count is not used for updating or creating a collection
    products_count = serializers.IntegerField(read_only=True)


class ProductSerializer(serializers.Serializer):  # type: ignore
    id = serializers.IntegerField()
    title = serializers.CharField(max_length=255)
    price = serializers.DecimalField(
        max_digits=6, decimal_places=2, source="unit_price"
    )

    # For a custom field like this one that doesnt exist in the model we define the method name and give the function below
    price_with_tax = serializers.SerializerMethodField(method_name="calculate_tax")

    # There are 4 ways of serializing a relationship: one way is to use primary key, another is string, nested objects and hyperlinks
    collection = serializers.PrimaryKeyRelatedField(queryset=Collection.objects.all())

    collection = serializers.StringRelatedField()

    collection = CollectionSerializer()

    collection = serializers.HyperlinkedRelatedField(
        queryset=Collection.objects.all(), view_name="collection-detail"
    )

    def calculate_tax(self, product: Product):
        return product.unit_price * Decimal(1.1)


# As you can see above we had to redefine fields already in the models.py file. Thats bad programming so instead
# we can use model serializers
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "slug",
            "inventory",
            "description",
            "unit_price",
            "price_with_tax",
            "collection",
        ]

    price_with_tax = serializers.SerializerMethodField(method_name="calculate_tax")

    def calculate_tax(self, product: Product):
        return product.unit_price * Decimal(1.1)


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "date", "name", "description"]

    def create(self, validated_data):
        product_id = self.context["product_id"]
        return Review.objects.create(product_id=product_id, **validated_data)


class SimpleProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "title", "unit_price"]


class CartItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer()
    total_price = serializers.SerializerMethodField(method_name="get_total_price")

    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "total_price"]

    def get_total_price(self, cart_item: CartItem):
        return cart_item.quantity * cart_item.product.unit_price


class CartSerizalizer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField(method_name="get_total_price")

    def get_total_price(self, cart):
        return sum(
            [item.quantity * item.product.unit_price for item in cart.items.all()]
        )

    class Meta:
        model = Cart
        fields = ["id", "items", "total_price"]


class AddCartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()

    # Prevent getting a hard error from django if the product_id from the post request doesnt exist
    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value).exists():
            raise serializers.ValidationError("No product with the given id was found")
        return value

    # We specify a custom save formula because if the item is already in the cart then we are updating
    # just the quantity, else we are just adding the item.

    # we return self.instance to comply with the default save function of the ModelSerializer

    def save(self, **kwargs):
        # The cart_id is present in the URL, not accessible in validated data. Thhere
        cart_id = self.context["cart_id"]
        product_id = self.validated_data["product_id"]
        quantity = self.validated_data["quantity"]
        try:
            # Update existing item
            cart_item = CartItem.objects.get(cart_id=cart_id, product_id=product_id)
            cart_item.quantity += quantity
            cart_item.save()
            self.instance = cart_item
        except CartItem.DoesNotExist:
            # Create a new item
            self.instance = CartItem.objects.create(
                cart_id=cart_id, **self.validated_data
            )
        return self.instance

    class Meta:
        model = CartItem
        fields = ["id", "product_id", "quantity"]


class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["quantity"]


class CustomerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "user_id", "phone", "birth_date", "membership"]


class OrderItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "unit_price", "quantity"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ["id", "customer", "placed_at", "payment_status", "items"]


class CreateOrderSerializer(
    serializers.Serializer
):  # Can't use model serializer cuz cart_id not part of the Order model
    cart_id = serializers.UUIDField()

    def save(self, **kwargs):
        with transaction.atomic():  # We use this because due to the multiple queries we wanna ensure that either all the queries
            # or none of them run, therefore we use a transaction
            cart_id = self.validated_data["cart_id"]

            # Create a customer if a customer profile not existing, and create an associated order
            (customer, created) = Customer.objects.get_or_create(
                user_id=self.context["user_id"]
            )
            order = Order.objects.create(customer=customer)

            # Add all the cart items as order items
            cart_items = CartItem.objects.select_related("product").filter(
                cart_id=cart_id
            )

            order_items = [
                OrderItem(
                    order=order,
                    product=item.product,
                    unit_price=item.product.unit_price,
                    quantity=item.quantity,
                )
                for item in cart_items
            ]

            OrderItem.objects.bulk_create(order_items)

            # Delete the cart once we are done
            Cart.objects.filter(pk=cart_id).delete()
