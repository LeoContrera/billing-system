"""
URLs para gestión de sesiones de caja.
"""

from django.urls import path
from . import views

app_name = 'cash_session'

urlpatterns = [
    # Página principal (layout completo con CSS)
    path('', views.session_page_view, name='session-page'),

    # Endpoint HTMX para partials (sin layout)
    path('control/', views.session_control_htmx_view, name='session-control'),
]
