"""
Configuración del Django Admin para el módulo de facturación electrónica.
"""

from django.contrib import admin
from .models import Invoice, VATAliquot


class VATAliquotInline(admin.TabularInline):
    """Inline para mostrar alícuotas de IVA en Facturas A."""
    model = VATAliquot
    extra = 0
    readonly_fields = ['vat_rate', 'base_amount', 'vat_amount']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin para gestión de facturas electrónicas."""

    list_display = [
        'id',
        'receipt_type',
        'status',
        'customer_name',
        'total_amount',
        'cae',
        'display_number',
        'created_at'
    ]

    list_filter = [
        'status',
        'receipt_type',
        'created_at',
        'customer_tax_category'
    ]

    search_fields = [
        'cae',
        'customer_name',
        'customer_tax_id',
        'notes'
    ]

    readonly_fields = [
        'sale',
        # 'afip_receipt',  # Temporarily commented out
        'receipt_type',
        'customer_name',
        'customer_tax_id',
        'customer_tax_category',
        'net_taxed',
        'vat_amount',
        'net_untaxed',
        'total_amount',
        'cae',
        'cae_expiration',
        'display_number',
        'created_at',
        'authorized_at',
        'created_by'
    ]

    fieldsets = (
        ('Información General', {
            'fields': (
                'sale',
                'receipt_type',
                'status',
                'display_number'
            )
        }),
        ('Datos del Cliente', {
            'fields': (
                'customer_name',
                'customer_tax_id',
                'customer_tax_category'
            )
        }),
        ('Montos', {
            'fields': (
                'net_taxed',
                'vat_amount',
                'net_untaxed',
                'total_amount'
            )
        }),
        ('Autorización AFIP', {
            'fields': (
                'cae',
                'cae_expiration',
                # 'afip_receipt'  # Temporarily commented out
            )
        }),
        ('Metadatos', {
            'fields': (
                'created_by',
                'created_at',
                'authorized_at',
                'notes'
            )
        })
    )

    inlines = [VATAliquotInline]

    def has_add_permission(self, request):
        """No permitir creación manual desde admin."""
        return False

    def has_delete_permission(self, request, obj=None):
        """No permitir eliminación desde admin."""
        return False


@admin.register(VATAliquot)
class VATAliquotAdmin(admin.ModelAdmin):
    """Admin para alícuotas de IVA (solo lectura)."""

    list_display = [
        'invoice',
        'vat_rate',
        'base_amount',
        'vat_amount'
    ]

    readonly_fields = [
        'invoice',
        'vat_rate',
        'base_amount',
        'vat_amount'
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
