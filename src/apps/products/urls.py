"""
URLs para la app products.
"""

from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    # Lista y gestión de productos
    path("", views.product_list, name="list"),
    path("create/", views.product_create, name="create"),
    path("<str:sku>/update/", views.product_update, name="update"),
    path("<str:sku>/toggle-active/", views.toggle_active, name="toggle_active"),

    # Búsqueda y detalles (para API/HTMX)
    path("search/", views.search_products, name="search"),
    path("<str:sku>/detail/", views.product_detail, name="detail"),
]
