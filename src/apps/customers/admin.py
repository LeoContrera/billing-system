"""
Configuración del admin para la app customers.
"""

from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Admin para el modelo Customer."""
    list_display = ['last_name', 'first_name', 'tax_id', 'phone']
    search_fields = ['last_name', 'first_name', 'tax_id']
    list_filter = ['created_at']
