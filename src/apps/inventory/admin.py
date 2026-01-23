"""
Configuración del admin para la app inventory.
"""

from django.contrib import admin

from .models import Movement, Stock


class MovementInline(admin.TabularInline):
    """Inline para mostrar movimientos recientes."""

    model = Movement
    extra = 0
    readonly_fields = [
        "movement_type",
        "delta_qty",
        "previous_qty",
        "reference",
        "created_at",
        "created_by",
    ]
    ordering = ["-created_at"]
    max_num = 10

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    """Admin para el modelo Stock."""

    list_display = [
        "product",
        "current_qty",
        "min_qty",
        "location",
        "is_below_minimum",
        "updated_at",
    ]
    list_filter = ["location", "updated_at"]
    search_fields = ["product__sku", "product__name"]
    readonly_fields = ["updated_at"]
    inlines = [MovementInline]
    list_select_related = ["product"]

    @admin.display(boolean=True, description="Bajo Mínimo")
    def is_below_minimum(self, obj):
        return obj.is_below_minimum


@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    """Admin para el modelo Movement."""

    list_display = [
        "id",
        "stock",
        "movement_type",
        "delta_qty",
        "previous_qty",
        "reference",
        "created_at",
        "created_by",
    ]
    list_filter = ["movement_type", "created_at"]
    search_fields = ["stock__product__sku", "reference"]
    readonly_fields = [
        "stock",
        "movement_type",
        "delta_qty",
        "previous_qty",
        "reference",
        "created_at",
        "created_by",
    ]
    date_hierarchy = "created_at"
    list_select_related = ["stock", "stock__product", "created_by"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
