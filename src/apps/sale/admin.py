"""
Configuración del admin para la app sale.
"""

from django.contrib import admin
from .models import Sale, SaleLineItem


class SaleLineItemInline(admin.TabularInline):
    """Inline para mostrar items de venta."""
    model = SaleLineItem
    extra = 0
    readonly_fields = ['product_name', 'sku', 'quantity', 'unit_price', 'discount_amount']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    """Admin para el modelo Sale."""
    list_display = ['id', 'customer', 'status', 'created_by', 'created_at', 'completed_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['created_at', 'completed_at']
    inlines = [SaleLineItemInline]
