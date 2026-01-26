"""
URLs para la app payments.
"""

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('add/', views.add_payment, name='add_payment'),
    path('preview-interest/', views.preview_interest, name='preview_interest'),
]
