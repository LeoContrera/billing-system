"""
Vistas para gestión de sesiones de caja.

Este módulo implementa vistas delgadas que solo manejan request/response,
delegando la lógica de negocio a CashSessionService.
"""

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from .decorators import cashier_required
from .services import CashSessionService


@cashier_required
@require_http_methods(["GET"])
def session_page_view(request):
    """
    Página principal de control de caja.

    Renderiza el layout completo con session_control.html (incluye CSS, navbar, etc).
    HTMX cargará dinámicamente el contenido apropiado desde session_control_htmx_view.
    """
    return render(request, 'cash_session/session_control.html')


@cashier_required
@require_http_methods(["GET", "POST"])
def session_control_htmx_view(request):
    """
    Endpoint HTMX para control de apertura/cierre de sesión de caja.

    GET (HTMX):
        - Si NO hay sesión activa: Retorna formulario de apertura (partial)
        - Si hay sesión activa: Retorna dashboard de sesión abierta (partial)

    POST (HTMX):
        - Procesa apertura de sesión con monto inicial
        - Retorna dashboard de sesión abierta (partial para swap)
    """
    # GET: Renderizar estado actual (partial)
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


@cashier_required
@require_http_methods(["GET"])
def close_session_page_view(request):
    """
    Página de cierre de caja.

    Renderiza el layout completo con close_session.html.
    Verifica que haya una sesión activa antes de mostrar el formulario.
    """
    # Verificar que el usuario tenga una sesión activa
    active_session = CashSessionService.get_active_session(request.user)

    if not active_session:
        # Si no hay sesión activa, redirigir a la página de control
        from django.shortcuts import redirect
        return redirect('cash_session:session-page')

    context = {
        'session': active_session,
    }
    return render(request, 'cash_session/close_session.html', context)


@cashier_required
@require_http_methods(["POST"])
def close_session_htmx_view(request):
    """
    Endpoint HTMX para procesar el cierre de sesión.

    POST (HTMX):
        - Procesa cierre de sesión con monto final
        - Retorna mensaje de éxito (partial para swap)
    """
    try:
        # Obtener sesión activa
        active_session = CashSessionService.get_active_session(request.user)

        if not active_session:
            return render(
                request,
                'cash_session/partials/close_error.html',
                {'error': 'No tienes una sesión activa para cerrar.'},
                status=400
            )

        # Obtener monto final del form
        closing_balance_str = request.POST.get('closing_balance', '0.00')
        try:
            closing_balance = Decimal(closing_balance_str)
        except (InvalidOperation, ValueError):
            closing_balance = Decimal('0.00')

        # Cerrar sesión (service layer)
        closed_session = CashSessionService.close_session(
            session=active_session,
            closing_balance=closing_balance
        )

        # Retornar mensaje de éxito (HTMX swap)
        context = {
            'session': closed_session,
        }
        return render(request, 'cash_session/partials/close_success.html', context)

    except ValidationError as e:
        # Mostrar error
        return render(
            request,
            'cash_session/partials/close_error.html',
            {'error': str(e)},
            status=400
        )


@require_http_methods(["GET", "POST"])
def cashier_login_view(request):
    """
    Vista de login específica para cajeros.

    GET: Muestra el formulario de login
    POST: Procesa las credenciales y verifica que el usuario sea cajero
    """
    # Si el usuario ya está autenticado y es cajero, redirigir a cash-session
    if request.user.is_authenticated and request.user.groups.filter(name='Cajeros').exists():
        return redirect('cash_session:session-page')

    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Validar que se proporcionen ambos campos
        if not username or not password:
            messages.error(request, 'Por favor, ingresa tu usuario y contraseña.')
            return render(request, 'cash_session/cashier_login.html')

        # Autenticar usuario
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Verificar que el usuario pertenezca al grupo 'Cajeros'
            if user.groups.filter(name='Cajeros').exists():
                login(request, user)
                messages.success(request, f'¡Bienvenido, {user.get_full_name() or user.username}!')
                return redirect('cash_session:session-page')
            else:
                messages.error(
                    request,
                    'No tienes permisos para acceder al sistema de caja. '
                    'Contacta al administrador si crees que esto es un error.'
                )
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'cash_session/cashier_login.html')


@require_http_methods(["POST"])
def cashier_logout_view(request):
    """
    Vista para cerrar sesión de cajero.
    """
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('cash_session:cashier-login')
