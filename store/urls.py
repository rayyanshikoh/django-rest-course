from django.urls import path, include
from . import views

# from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

# Viewsets require router
router = routers.DefaultRouter()
router.register("products", views.ProductViewSet, basename="products")
router.register("collections", views.CollectionViewSet)
router.register("customers", views.CustomerViewSet)

router.register("carts", views.CartViewSet, basename="cart")

products_router = routers.NestedDefaultRouter(router, "products", lookup="product")
products_router.register("reviews", views.ReviewViewSet, basename="product-reviews")

carts_router = routers.NestedDefaultRouter(router, "carts", lookup="cart")
carts_router.register("items", views.CartItemViewSet, basename="cart-items")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(products_router.urls)),
    path("", include(carts_router.urls))
    # Commented out below urls because we no longer need them
    # path("products/", views.ProductList.as_view(), name="product_list"),
    # path("products/<int:pk>/", views.ProductDetail.as_view(), name="product_detail"),
    # path("collections/", views.CollectionList.as_view(), name="collection_list"),
    # path(
    #     "collections/<int:pk>/",
    #     views.CollectionDetail.as_view(),
    #     name="collection-detail",
    # ),
]
