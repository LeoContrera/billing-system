"""
URLs para la app inventory.
"""

from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("check/<str:sku>/", views.check_availability, name="check"),
    path("stock/<str:sku>/", views.stock_level, name="stock_level"),
    path("low-stock/", views.low_stock_list, name="low_stock"),
    path("adjust-quick/", views.adjust_stock_quick, name="adjust_quick"),
    path("summary/", views.inventory_summary, name="summary"),
]
