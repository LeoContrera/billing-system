"""
URLs para la app products.
"""

from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("search/", views.search_products, name="search"),
    path("<str:sku>/", views.product_detail, name="detail"),
]
