"""
URLs para gestión de sesiones de caja.
"""

from django.urls import path
from . import views

app_name = 'cash_session'

urlpatterns = [
    # Login de cajeros
    path('login/', views.cashier_login_view, name='cashier-login'),
    path('logout/', views.cashier_logout_view, name='cashier-logout'),

    # Página principal (layout completo con CSS)
    path('', views.session_page_view, name='session-page'),

    # Endpoint HTMX para partials (sin layout)
    path('control/', views.session_control_htmx_view, name='session-control'),

    # Página de cierre de caja
    path('close/', views.close_session_page_view, name='close-page'),

    # Endpoint HTMX para cerrar sesión
    path('close/submit/', views.close_session_htmx_view, name='close-submit'),
]
