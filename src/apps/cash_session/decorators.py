"""
Decoradores personalizados para control de acceso a sesiones de caja.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def cashier_required(view_func):
    """
    Decorador que verifica si el usuario pertenece al grupo 'Cajeros'.

    Si el usuario no está autenticado, redirige al login de cajeros.
    Si está autenticado pero no es cajero, muestra un mensaje de error
    y redirige al login de cajeros.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Verificar si el usuario está autenticado
        if not request.user.is_authenticated:
            return redirect('cash_session:cashier-login')

        # Verificar si el usuario pertenece al grupo 'Cajeros'
        if not request.user.groups.filter(name='Cajeros').exists():
            messages.error(
                request,
                'No tienes permisos para acceder a esta sección. '
                'Debes ser miembro del grupo de Cajeros.'
            )
            return redirect('cash_session:cashier-login')

        # Usuario autorizado, ejecutar la vista
        return view_func(request, *args, **kwargs)

    return wrapper
