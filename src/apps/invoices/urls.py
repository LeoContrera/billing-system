"""
URL Configuration para el módulo de facturación electrónica.
"""

from django.urls import path
from . import views

app_name = 'invoices'

urlpatterns = [
    # Flujo completo (recomendado)
    path('process-sale/<int:sale_id>/', views.process_sale_afip, name='process_sale'),

    # Flujo paso a paso (legacy)
    path('create/<int:sale_id>/', views.create_invoice, name='create'),
    path('<int:invoice_id>/emit-cae/', views.emit_cae, name='emit_cae'),

    # Detalles
    path('<int:invoice_id>/', views.invoice_details, name='details'),
]
