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
    return render(request, 'sale/sale_create.html', context)


@login_required
@require_POST
def set_customer(request):
    """
    Asignar cliente a venta.

    POST /sale/set-customer/
    HTMX: Renderiza partial HTML con info del cliente
    """
    try:
        sale_id = request.POST.get('sale_id')
        customer_id = request.POST.get('customer_id')

        sale = SaleService.set_customer(int(sale_id), int(customer_id))

        # Renderizar partial HTML con info del cliente
        return render(request, 'sale/_customer_info.html', {'sale': sale})

    except ValidationError as e:
        return HttpResponse(f'<div class="text-red-600">{e.message}</div>', status=400)


@login_required
@require_POST
def add_item(request):
    """
    Agregar producto a venta.

    POST /sale/add-item/
    HTMX: Renderiza solo la nueva fila de producto
    """
    try:
        sale_id = int(request.POST.get('sale_id'))
        product_name = request.POST.get('product_name')
        sku = request.POST.get('sku', '')
        quantity = Decimal(request.POST.get('quantity'))
        unit_price = Decimal(request.POST.get('unit_price'))

        item = SaleService.add_line_item(sale_id, product_name, quantity, unit_price, sku)

        # Renderizar solo la nueva fila
        return render(request, 'sale/_product_row.html', {'item': item})

    except ValidationError as e:
        return HttpResponse(f'<div class="text-red-600">{e.message}</div>', status=400)


@login_required
@require_POST
def discount_global(request):
    """
    Aplicar descuento global.

    POST /sale/discount-global/
    HTMX: Renderiza sección de totales actualizada
    """
    try:
        sale_id = int(request.POST.get('sale_id'))
        discount_amount = Decimal(request.POST.get('discount_amount'))

        sale = SaleService.apply_global_discount(sale_id, discount_amount)

        # Re-fetch con relaciones para cálculos
        sale = Sale.objects.prefetch_related('line_items', 'transactions').get(pk=sale_id)

        # Renderizar sección de totales
        return render(request, 'sale/_totals_section.html', {'sale': sale})

    except ValidationError as e:
        return HttpResponse(f'<div class="text-red-600">{e.message}</div>', status=400)


@login_required
@require_POST
def discount_item(request):
    """
    Aplicar descuento a línea específica.

    POST /sale/discount-item/
    HTMX: Renderiza solo la fila actualizada
    """
    try:
        line_item_id = int(request.POST.get('line_item_id'))
        discount_amount = Decimal(request.POST.get('discount_amount'))

        line_item = SaleService.apply_line_discount(line_item_id, discount_amount)

        # Renderizar solo la fila actualizada
        return render(request, 'sale/_line_item_row.html', {'item': line_item})

    except ValidationError as e:
        return HttpResponse(f'<div class="text-red-600">{e.message}</div>', status=400)


@login_required
@require_POST
def add_payment(request):
    """
    Agregar pago a venta.

    POST /sale/add-payment/
    HTMX: Renderiza fila de pago actualizada
    """
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

        # Renderizar fila de pago
        return render(request, 'sale/_payment_row.html', {'transaction': transaction})

    except ValidationError as e:
        return HttpResponse(f'<div class="text-red-600">{e.message}</div>', status=400)


@login_required
@require_POST
def finalize_sale(request):
    """
    Finalizar venta.

    POST /sale/finalize/
    HTMX: Renderiza mensaje de éxito + botón para nueva venta
    """
    try:
        sale_id = int(request.POST.get('sale_id'))
        sale = SaleService.finalize_sale(sale_id)

        # Renderizar mensaje de éxito + botón para nueva venta
        return render(request, 'sale/_sale_completed.html', {'sale': sale})

    except ValidationError as e:
        return HttpResponse(f'<div class="text-red-600">{e.message}</div>', status=400)
