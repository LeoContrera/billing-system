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

    # Actualización masiva de precios
    path("actualizar-precios/", views.bulk_price_update_view, name="bulk_price_update"),
    path("actualizar-precios/filtrar/", views.bulk_price_update_filter, name="bulk_price_filter"),
    path("actualizar-precios/aplicar/", views.bulk_price_update_submit, name="bulk_price_submit"),

    # Historial de precios
    path("historial-precios/", views.price_history_view, name="price_history"),
    path("historial-precios/filtrar/", views.price_history_filter, name="price_history_filter"),

    # Operaciones masivas
    path("operaciones-masivas/", views.bulk_operations_view, name="bulk_operations"),
    path("operaciones-masivas/<str:bulk_id>/", views.bulk_operation_detail, name="bulk_operation_detail"),
]
