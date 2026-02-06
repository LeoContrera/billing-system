"""
Vistas para gestión de inventario.
"""

from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from products.services import ProductService

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


@login_required
@require_POST
def adjust_stock_quick(request):
    """
    Modal de ajuste rápido de stock (HTMX).

    POST /inventory/adjust-quick/
    """
    try:
        sku = request.POST.get('sku')
        adjustment = Decimal(request.POST.get('adjustment'))
        notes = request.POST.get('notes', '')

        # Obtener stock actual
        current_qty = InventoryService.get_stock_level(sku)
        if current_qty is None:
            current_qty = Decimal('0')

        new_qty = current_qty + adjustment

        if new_qty < 0:
            return JsonResponse({
                'success': False,
                'error': 'El stock no puede ser negativo'
            }, status=400)

        result = InventoryService.adjust_stock(
            sku=sku,
            new_quantity=new_qty,
            user=request.user,
            notes=f"Ajuste rápido: {adjustment:+}. {notes}".strip()
        )

        return JsonResponse({
            'success': True,
            'new_qty': float(result.new_qty),
            'message': result.message
        })

    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error inesperado: {str(e)}'
        }, status=500)


@login_required
def inventory_summary(request):
    """
    Resumen de inventario con valor total y alertas de stock bajo.

    GET /inventory/summary/
    """
    from django.shortcuts import render

    total_value = ProductService.calculate_total_inventory_value()
    low_stock = InventoryService.get_products_below_minimum()
    low_stock_count = len(low_stock)

    # Si es HTMX, retornar fragmento HTML
    if request.headers.get('HX-Request'):
        return render(request, 'products/_inventory_summary_widget.html', {
            'total_value': total_value,
            'low_stock_count': low_stock_count,
            'low_stock_items': low_stock[:5]  # Mostrar solo los primeros 5
        })

    # Si es JSON API
    return JsonResponse({
        'total_value': float(total_value),
        'low_stock_count': low_stock_count,
        'low_stock_items': [
            {
                'sku': stock.product.sku,
                'name': stock.product.name,
                'current': float(stock.current_qty),
                'minimum': float(stock.min_qty)
            }
            for stock in low_stock
        ]
    })
