"""
Configuración del admin para la app products.
"""

from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin para el modelo Product."""

    list_display = ["sku", "name", "price", "cost", "is_active", "updated_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["sku", "name"]
    readonly_fields = ["created_at", "updated_at"]
    list_editable = ["price", "is_active"]
    ordering = ["name"]
