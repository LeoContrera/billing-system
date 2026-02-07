"""
Vistas para el dashboard principal.

Vista delgada que solo maneja request/response,
delegando la lógica de negocio a DashboardService.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .services import DashboardService


@login_required
@require_http_methods(["GET"])
def dashboard_view(request):
    """
    Vista principal del dashboard.

    Muestra el rendimiento semanal y las últimas operaciones de caja.
    """
    # Obtener datos del servicio
    weekly_performance = DashboardService.get_weekly_performance()
    daily_breakdown = DashboardService.get_daily_breakdown()
    recent_sessions = DashboardService.get_recent_cash_sessions()

    context = {
        'weekly_performance': weekly_performance,
        'daily_breakdown': daily_breakdown,
        'recent_sessions': recent_sessions,
    }

    return render(request, 'dashboard/index.html', context)
