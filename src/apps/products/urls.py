"""
URLs para la app products.
"""

from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    # Vista principal
    path("", views.product_list, name="list"),

    # CRUD operations
    path("create/", views.product_create, name="create"),
    path("<str:sku>/update/", views.product_update, name="update"),
    path("<str:sku>/toggle-active/", views.product_toggle_active, name="toggle_active"),

    # API endpoints
    path("search/", views.search_products, name="search"),
    path("<str:sku>/", views.product_detail, name="detail"),
]
