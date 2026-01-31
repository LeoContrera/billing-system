"""
Vistas para gestión de ventas (POS).

Este módulo implementa vistas delgadas que solo manejan request/response,
delegando la lógica de negocio a SaleService.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from decimal import Decimal
from .services import SaleService
from .models import Sale, SaleLineItem
from payments.services import PaymentService


@login_required
@require_http_methods(["GET"])
def pos_index(request):
    """
    Interfaz principal del POS (standalone).

    GET /sale/pos/

    Crea nueva venta al cargar la página y muestra la interfaz POS completa.
    Esta vista renderiza pos_index.html con todos los datos necesarios.
    """
    # Crear nueva venta al cargar la página
    sale = SaleService.create_sale(request.user)

    # Pre-fetch de relaciones para evitar N+1 queries
    sale = (Sale.objects
            .select_related('customer', 'created_by')
            .prefetch_related('line_items', 'transactions__payment_method')
            .get(pk=sale.id))

    payment_methods = PaymentService.get_active_payment_methods()

    context = {
        'sale': sale,
        'payment_methods': payment_methods,
    }
    return render(request, 'sale/pos_index.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def create_sale(request):
    """
    Interfaz principal del POS (versión HTMX).

    GET /sale/create/

    Crea nueva venta al cargar la página y muestra la interfaz completa.
    """
    # Crear nueva venta al cargar la página
    sale = SaleService.create_sale(request.user)
    payment_methods = PaymentService.get_active_payment_methods()

    context = {
        'sale': sale,
        'payment_methods': payment_methods,
    }
    return render(request, 'sale/pos_index.html', context)


@login_required
@require_POST
def set_customer(request):
    """
    Asignar cliente a venta.

    POST /sale/set-customer/
    JSON: Retorna estado de éxito para Alpine.js
    """
    from django.http import JsonResponse

    try:
        sale_id = request.POST.get('sale_id')
        customer_id = request.POST.get('customer_id')

        sale = SaleService.set_customer(int(sale_id), int(customer_id))

        return JsonResponse({
            'success': True,
            'message': 'Cliente asignado'
        })

    except ValidationError as e:
        error_message = e.message if hasattr(e, 'message') else str(e)
        return JsonResponse({
            'success': False,
            'error': error_message
        }, status=400)


@login_required
@require_POST
def add_item(request):
    """
    Agregar producto a venta con validación de producto e inventario.

    POST /sale/add-item/
    HTMX: Renderiza solo la nueva fila de producto
    JSON: Retorna datos del item para Alpine.js

    Parámetros POST:
        - sale_id: ID de la venta
        - sku: SKU del producto (requerido)
        - quantity: Cantidad (default: 1)

    Nota: product_name y unit_price se obtienen automáticamente del ProductService
    """
    try:
        sale_id = int(request.POST.get('sale_id'))
        sku = request.POST.get('sku', '').strip()
        quantity = Decimal(request.POST.get('quantity', '1'))

        # El servicio ahora valida producto y stock automáticamente
        item = SaleService.add_line_item(sale_id, sku, quantity)

        # Si es request HTMX, renderizar HTML
        if request.headers.get('HX-Request'):
            return render(request, 'sale/_product_row.html', {'item': item})

        # Si es request JSON (Alpine.js/Fetch), retornar JSON
        from django.http import JsonResponse
        return JsonResponse({
            'success': True,
            'item': {
                'id': item.id,
                'sku': item.sku,
                'description': item.product_name,
                'quantity': float(item.quantity),
                'unitPrice': float(item.unit_price),
                'discountAmount': float(item.discount_amount),
            }
        })

    except ValidationError as e:
        error_message = e.message if hasattr(e, 'message') else str(e)

        # Si es request HTMX
        if request.headers.get('HX-Request'):
            return HttpResponse(
                f'<div class="text-red-600 p-2 rounded bg-red-50">{error_message}</div>',
                status=400
            )

        # Si es request JSON
        from django.http import JsonResponse
        return JsonResponse({
            'success': False,
            'error': error_message
        }, status=400)


@login_required
@require_POST
def discount_global(request):
    """
    Aplicar descuento global.

    POST /sale/discount-global/
    JSON: Retorna estado de éxito para Alpine.js
    """
    from django.http import JsonResponse

    try:
        sale_id = int(request.POST.get('sale_id'))
        discount_amount = Decimal(request.POST.get('discount_amount'))

        sale = SaleService.apply_global_discount(sale_id, discount_amount)

        return JsonResponse({
            'success': True,
            'discount_amount': float(discount_amount),
            'message': 'Descuento aplicado'
        })

    except ValidationError as e:
        error_message = e.message if hasattr(e, 'message') else str(e)
        return JsonResponse({
            'success': False,
            'error': error_message
        }, status=400)


@login_required
@require_POST
def discount_item(request):
    """
    Aplicar descuento a línea específica.

    POST /sale/discount-item/
    JSON: Retorna datos actualizados del item para Alpine.js
    """
    from django.http import JsonResponse

    try:
        line_item_id = int(request.POST.get('line_item_id'))
        discount_amount = Decimal(request.POST.get('discount_amount'))

        line_item = SaleService.apply_line_discount(line_item_id, discount_amount)

        return JsonResponse({
            'success': True,
            'item': {
                'id': line_item.id,
                'discount_amount': float(line_item.discount_amount)
            }
        })

    except ValidationError as e:
        error_message = e.message if hasattr(e, 'message') else str(e)
        return JsonResponse({
            'success': False,
            'error': error_message
        }, status=400)


@login_required
@require_POST
def add_payment(request):
    """
    Agregar pago a venta.

    POST /sale/add-payment/
    JSON: Retorna datos del pago para Alpine.js
    """
    from django.http import JsonResponse

    try:
        sale_id = int(request.POST.get('sale_id'))
        payment_method_id = int(request.POST.get('payment_method_id'))
        amount = Decimal(request.POST.get('amount'))

        transaction = PaymentService.add_payment(
            sale_id=sale_id,
            payment_method_id=payment_method_id,
            amount=amount,
            user=request.user
        )

        return JsonResponse({
            'success': True,
            'transaction': {
                'id': transaction.id,
                'amount': float(transaction.amount),
                'method_name': transaction.payment_method.name,
                'method_type': transaction.payment_method.method_type
            }
        })

    except ValidationError as e:
        error_message = e.message if hasattr(e, 'message') else str(e)
        return JsonResponse({
            'success': False,
            'error': error_message
        }, status=400)


@login_required
@require_POST
def finalize_sale(request):
    """
    Finalizar venta con descuento de inventario.

    POST /sale/finalize/
    JSON: Retorna estado de éxito para Alpine.js

    Nota: Al finalizar, se registran movimientos de inventario para todos
    los items con SKU. Si algún item no tiene stock suficiente, se hace
    rollback de toda la operación.
    """
    from django.http import JsonResponse

    try:
        sale_id = int(request.POST.get('sale_id'))
        # Pasar usuario para registro de movimientos de inventario
        sale = SaleService.finalize_sale(sale_id, request.user)

        return JsonResponse({
            'success': True,
            'sale_id': sale.id,
            'message': 'Venta finalizada con éxito'
        })

    except ValidationError as e:
        error_message = e.message if hasattr(e, 'message') else str(e)
        return JsonResponse({
            'success': False,
            'error': error_message
        }, status=400)


@login_required
@require_http_methods(["GET"])
def preview_receipt_type(request):
    """
    Obtener tipo de comprobante según cliente.

    GET /sale/preview-receipt-type/?customer_tax_category=RI&customer_identified=true
    JSON: Retorna tipo de comprobante determinado por backend

    Parámetros GET:
        - customer_tax_category: Categoría fiscal del cliente (CF, RI, MT, EX) o None
        - customer_identified: 'true' o 'false' (default: 'false')

    Este endpoint mueve la lógica de negocio de determineReceiptType()
    del frontend al backend, donde corresponde.
    """
    from django.http import JsonResponse
    from invoices.services import InvoiceService
    from invoices.models import ReceiptType

    customer_tax_category = request.GET.get('customer_tax_category', '').strip()
    customer_identified = request.GET.get('customer_identified', 'false').lower() == 'true'

    # Si no hay categoría fiscal, asumimos que no hay cliente identificado
    if not customer_tax_category:
        customer_identified = False
        customer_tax_category = None

    # Llamar al servicio de backend (única fuente de verdad)
    receipt_type = InvoiceService.determine_receipt_type(
        issuer_tax_category=InvoiceService.ISSUER_TAX_CATEGORY,
        customer_tax_category=customer_tax_category or '',
        customer_identified=customer_identified
    )

    # Mapear el código a nombre amigable
    receipt_type_display = {
        ReceiptType.FACTURA_A: 'Factura A',
        ReceiptType.FACTURA_B: 'Factura B',
        ReceiptType.FACTURA_C: 'Factura C' if customer_identified else 'Ticket',
    }.get(receipt_type, 'Ticket')

    return JsonResponse({
        'receipt_type': receipt_type,
        'receipt_type_display': receipt_type_display
    })
