"""
Vistas para procesamiento de pagos.

Este módulo implementa vistas delgadas para registrar pagos,
delegando la lógica de negocio a PaymentService.
"""

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.shortcuts import render
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from decimal import Decimal, InvalidOperation
from .services import PaymentService
from .models import PaymentMethod
from sale.models import Sale


@login_required
@require_POST
def add_payment(request):
    """
    Registrar pago con cálculo automático de intereses.

    POST /payments/add/
    Retorna JSON con datos de la transacción o HTML fragment (si HTMX)

    Parámetros POST:
        - sale_id: ID de la venta
        - payment_method_id: ID del método de pago
        - amount: Monto base del pago
        - card_type: Tipo de tarjeta (opcional, requerido para tarjetas)
        - installments: Número de cuotas (default: 1)
        - interest_rate: Tasa de interés mensual % (default: 0.00)
    """
    try:
        # Parsear datos del request
        sale_id = int(request.POST.get('sale_id'))
        payment_method_id = int(request.POST.get('payment_method_id'))
        amount = Decimal(request.POST.get('amount', '0'))

        # Parámetros opcionales para tarjetas
        card_type = request.POST.get('card_type') or None
        installments = int(request.POST.get('installments', '1'))
        interest_rate = Decimal(request.POST.get('interest_rate', '0.00'))

        # Delegar lógica al servicio
        transaction = PaymentService.add_payment(
            sale_id=sale_id,
            payment_method_id=payment_method_id,
            amount=amount,
            user=request.user,
            card_type=card_type,
            installments=installments,
            interest_rate=interest_rate
        )

        # Si es llamada HTMX, retornar HTML fragment
        if request.headers.get('HX-Request'):
            return render(request, 'sale/partials/_payment_row.html', {'transaction': transaction})

        # Si no, retornar JSON (para Alpine.js o Fetch API)
        return JsonResponse({
            'success': True,
            'transaction': {
                'id': transaction.id,
                'amount': str(transaction.amount),
                'total_amount': str(transaction.total_amount),
                'card_type': transaction.card_type,
                'installments': transaction.installments,
                'interest_rate': str(transaction.interest_rate),
                'payment_method': {
                    'id': transaction.payment_method.id,
                    'name': transaction.payment_method.name,
                    'method_type': transaction.payment_method.method_type
                }
            }
        })

    except (ValueError, InvalidOperation) as e:
        error_msg = f'Datos inválidos: {str(e)}'
        if request.headers.get('HX-Request'):
            return HttpResponse(
                f'<div class="text-red-600 text-sm p-3 bg-red-50 rounded-lg border border-red-200">{error_msg}</div>',
                status=400
            )
        return JsonResponse({'success': False, 'error': error_msg}, status=400)

    except ValidationError as e:
        # Formatear errores de validación
        if hasattr(e, 'message_dict'):
            errors = ', '.join([f"{k}: {v[0]}" for k, v in e.message_dict.items()])
        else:
            errors = str(e)

        if request.headers.get('HX-Request'):
            return HttpResponse(
                f'<div class="text-red-600 text-sm p-3 bg-red-50 rounded-lg border border-red-200">{errors}</div>',
                status=400
            )
        return JsonResponse({'success': False, 'error': errors}, status=400)

    except Exception as e:
        error_msg = f'Error al procesar el pago: {str(e)}'
        if request.headers.get('HX-Request'):
            return HttpResponse(
                f'<div class="text-red-600 text-sm p-3 bg-red-50 rounded-lg border border-red-200">{error_msg}</div>',
                status=500
            )
        return JsonResponse({'success': False, 'error': error_msg}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def preview_interest(request):
    """
    Calcula y retorna el interés para un pago en cuotas.

    GET/POST /payments/preview-interest/
    HTMX: Retorna HTML fragment o JSON según el header

    Parámetros:
        - amount: Monto base del pago
        - installments: Número de cuotas
        - interest_rate: Tasa de interés mensual %

    Retorna:
        HTML fragment (si HTMX) o JSON (si API)
    """
    try:
        # Obtener parámetros (funciona con GET o POST)
        params = request.GET if request.method == 'GET' else request.POST

        amount = Decimal(params.get('amount', '0'))
        installments = int(params.get('installments', '1'))
        interest_rate = Decimal(params.get('interest_rate', '0.00'))

        # Calcular total con intereses
        total_amount = PaymentService.calculate_interest(
            amount=amount,
            installments=installments,
            interest_rate=interest_rate
        )

        # Calcular valor de cada cuota
        installment_value = total_amount / installments if installments > 0 else total_amount

        # Preparar datos
        interest_data = {
            'amount': amount,
            'total_amount': total_amount,
            'installments': installments,
            'installment_value': round(installment_value, 2),
            'interest_rate': interest_rate
        }

        # Si es llamada HTMX, retornar HTML fragment
        if request.headers.get('HX-Request'):
            return render(request, 'sale/partials/_interest_preview.html', {
                'interest_data': interest_data
            })

        # Si no, retornar JSON (para API o Alpine.js)
        return JsonResponse({
            'amount': str(amount),
            'total_amount': str(total_amount),
            'installments': installments,
            'installment_value': str(round(installment_value, 2)),
            'interest_rate': str(interest_rate)
        })

    except (ValueError, InvalidOperation) as e:
        if request.headers.get('HX-Request'):
            return HttpResponse(
                f'<div class="text-red-600 text-sm">Datos inválidos: {str(e)}</div>',
                status=400
            )
        return JsonResponse(
            {'error': f'Datos inválidos: {str(e)}'},
            status=400
        )
    except Exception as e:
        if request.headers.get('HX-Request'):
            return HttpResponse(
                f'<div class="text-red-600 text-sm">Error: {str(e)}</div>',
                status=500
            )
        return JsonResponse(
            {'error': f'Error al calcular interés: {str(e)}'},
            status=500
        )
