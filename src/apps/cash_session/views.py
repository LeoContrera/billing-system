"""
Vistas para gestión de sesiones de caja.

Este módulo implementa vistas delgadas que solo manejan request/response,
delegando la lógica de negocio a CashSessionService.
"""

from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .services import CashSessionService


@login_required
@require_http_methods(["GET", "POST"])
def session_control_view(request):
    """
    Control de apertura/cierre de sesión de caja.

    GET /cash-session/control/
        - Si NO hay sesión activa: Muestra formulario de apertura
        - Si hay sesión activa: Muestra dashboard de sesión abierta

    POST /cash-session/control/
        - Procesa apertura de sesión con monto inicial
        - Retorna dashboard de sesión abierta (HTMX swap)
    """
    # GET: Renderizar estado actual
    if request.method == "GET":
        active_session = CashSessionService.get_active_session(request.user)

        if active_session:
            # Estado: Caja abierta -> Mostrar dashboard
            context = {
                'session': active_session,
            }
            return render(request, 'cash_session/partials/session_dashboard.html', context)
        else:
            # Estado: Caja cerrada -> Mostrar formulario de apertura
            return render(request, 'cash_session/partials/session_open_form.html')

    # POST: Procesar apertura de sesión
    if request.method == "POST":
        try:
            # Obtener monto inicial del form
            opening_balance_str = request.POST.get('opening_balance', '0.00')
            try:
                opening_balance = Decimal(opening_balance_str)
            except (InvalidOperation, ValueError):
                opening_balance = Decimal('0.00')

            # Abrir sesión (service layer)
            session = CashSessionService.open_session(
                user=request.user,
                opening_balance=opening_balance
            )

            # Retornar dashboard (HTMX swap)
            context = {
                'session': session,
            }
            return render(request, 'cash_session/partials/session_dashboard.html', context)

        except ValidationError as e:
            # Mostrar error en el formulario
            context = {
                'error': str(e),
            }
            return render(
                request,
                'cash_session/partials/session_open_form.html',
                context,
                status=400
            )
