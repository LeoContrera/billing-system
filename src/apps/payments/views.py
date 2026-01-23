"""
Vistas para procesamiento de pagos.

Este módulo implementa vistas delgadas para registrar pagos,
delegando la lógica de negocio a PaymentService.
"""

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from decimal import Decimal
from .services import PaymentService
from sale.models import Sale


@login_required
@require_POST
def add_payment(request):
    """
    Registrar pago.

    POST /payments/add/
    HTMX: Renderiza solo la nueva fila de pago
    """
    try:
        sale_id = int(request.POST.get('sale_id'))
        payment_method_id = int(request.POST.get('payment_method_id'))
        amount = Decimal(request.POST.get('amount'))

        transaction = PaymentService.add_payment(sale_id, payment_method_id, amount, request.user)

        # Renderizar solo la nueva fila
        return render(request, 'sale/_payment_row.html', {'transaction': transaction})

    except ValidationError as e:
        return HttpResponse(f'<div class="text-red-600">{e.message}</div>', status=400)
