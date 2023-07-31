from decimal import Decimal
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

    # price = serializers.DecimalField(
    #     max_digits=6, decimal_places=2, source="unit_price"
    # )
    price_with_tax = serializers.SerializerMethodField(method_name="calculate_tax")
    # collection = serializers.HyperlinkedRelatedField(
    #     queryset=Collection.objects.all(), view_name="collection-detail"
    # )

    def calculate_tax(self, product: Product):
        return product.unit_price * Decimal(1.1)

    # These functions are for if you want to create custom functionality for creating and updating
    # when using the serializer
    # def create(self, validated_data):
    #     product = Product(**validated_data)
    #     product.other = 1
    #     product.save()
    #     return product

    # def update(self, instance, validated_data):
    #     instance.unit_price = validated_data.get("unit_price")
    #     instance.save()
    #     return instance


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
