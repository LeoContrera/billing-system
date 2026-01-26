"""
URLs para gestión de sesiones de caja.
"""

from django.urls import path
from . import views

app_name = 'cash_session'

urlpatterns = [
    path('', views.session_control_view, name='session-control'),
    path('control/', views.session_control_view, name='session-control-alt'),
]
