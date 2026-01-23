"""
Configuración del admin para la app payments.
"""

from django.contrib import admin
from .models import PaymentMethod, Transaction


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Admin para el modelo PaymentMethod."""
    list_display = ['name', 'method_type', 'is_active']
    list_filter = ['method_type', 'is_active']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin para el modelo Transaction."""
    list_display = ['sale', 'payment_method', 'amount', 'created_at', 'created_by']
    list_filter = ['payment_method', 'created_at']
    readonly_fields = ['created_at']
