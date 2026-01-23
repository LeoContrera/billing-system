"""
Vistas para gestión de inventario.
"""

from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .services import InventoryService


@login_required
@require_GET
def check_availability(request, sku):
    """
    Verificar disponibilidad de stock.

    GET /inventory/check/<sku>/?qty=<cantidad>
    """
    try:
        quantity = Decimal(request.GET.get("qty", "1"))
    except (ValueError, TypeError):
        quantity = Decimal("1")

    available = InventoryService.check_availability(sku, quantity)

    return JsonResponse(
        {"sku": sku, "quantity_requested": str(quantity), "available": available}
    )


@login_required
@require_GET
def stock_level(request, sku):
    """
    Obtener nivel de stock actual.

    GET /inventory/stock/<sku>/
    """
    level = InventoryService.get_stock_level(sku)

    if level is None:
        return JsonResponse(
            {"sku": sku, "error": "No hay registro de stock para este producto"},
            status=404,
        )

    return JsonResponse({"sku": sku, "current_qty": str(level)})


@login_required
@require_GET
def low_stock_list(request):
    """
    Lista de productos con stock bajo el mínimo.

    GET /inventory/low-stock/
    """
    stocks = InventoryService.get_products_below_minimum()

    return JsonResponse(
        {
            "count": len(stocks),
            "products": [
                {
                    "sku": s.product.sku,
                    "name": s.product.name,
                    "current_qty": str(s.current_qty),
                    "min_qty": str(s.min_qty),
                }
                for s in stocks
            ],
        }
    )
