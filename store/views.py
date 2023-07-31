from django.db.models import Count
from django.shortcuts import render, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    UpdateModelMixin
)
from rest_framework import status

from .filters import ProductFilter
from .models import Product, Collection, OrderItem, Review, Cart, CartItem, Customer
from .serializers import (
    ProductSerializer,
    CollectionSerializer,
    ReviewSerializer,
    CartSerizalizer,
    CartItemSerializer,
    AddCartItemSerializer,
    CustomerSerializer,
    UpdateCartItemSerializer,
)
from .pagination import DefaultPagination


# PUT and PATCH are used to update data
# PUT is used to update all fields
# PATCH is used to update some fields


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()

    # For Generic Filtering
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    # filterset_fields = ['collection_id']

    # For custom Filtering
    filterset_class = ProductFilter

    # Searching
    search_fields = ["title", "description"]

    # Ordering
    ordering_fields = ["unit_price", "last_update"]

    # Pagination
    pagination_class = DefaultPagination

    def get_serializer_context(self):
        return {"request": self.request}

    def destroy(self, request, *args, **kwargs):
        if OrderItem.objects.filter(product_id=kwargs["pk"]).count() > 0:
            return Response(
                {"error": "Product can't be deleted, associated with an order"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        return super().destroy(request, *args, **kwargs)


# The class below is a generic implementation of the collection_list api_view commented out below.
class CollectionList(ListCreateAPIView):
    queryset = Collection.objects.annotate(products_count=Count("products")).all()
    serializer_class = CollectionSerializer

    def get_serializer_context(self):
        return {"request": self.request}


class CollectionDetail(RetrieveUpdateDestroyAPIView):
    queryset = Collection.objects.annotate(products_count=Count("products"))
    serializer_class = CollectionSerializer

    def delete(self, request, pk):
        collection = get_object_or_404(Collection, pk=pk)
        if collection.products.count() > 0:  # type: ignore
            return Response(
                {
                    "error": "Deletion not allowed, collection is associated with products"
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Note that you can set ModelViewSet to ReadOnlyModelViewSet to allow read-only functions
class CollectionViewSet(ModelViewSet):
    queryset = Collection.objects.annotate(products_count=Count("products"))
    serializer_class = CollectionSerializer

    def get_serializer_context(self):
        return {"request": self.request}

    def delete(self, request, pk):
        collection = get_object_or_404(Collection, pk=pk)
        if collection.products.count() > 0:  # type: ignore
            return Response(
                {
                    "error": "Deletion not allowed, collection is associated with products"
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReviewViewSet(ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.filter(product_id=self.kwargs["product_pk"])

    def get_serializer_context(self):
        return {"product_id": self.kwargs["product_pk"]}


# class CartViewSet(ModelViewSet):
class CartViewSet(
    RetrieveModelMixin,
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    GenericViewSet,
):
    queryset = Cart.objects.prefetch_related("items__product").all()
    serializer_class = CartSerizalizer

    def get_serializer_context(self):
        return {"request": self.request}


class CartItemViewSet(ModelViewSet):
    http_method_names = ["get", "post", "patch", "delete"]

    def get_serializer_context(self):
        return {"cart_id": self.kwargs["cart_pk"]}

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AddCartItemSerializer
        elif self.request.method == "PATCH":
            return UpdateCartItemSerializer
        return CartItemSerializer

    def get_queryset(self):
        return CartItem.objects.filter(cart_id=self.kwargs["cart_pk"]).select_related(
            "product"
        )


class CustomerViewSet(CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer