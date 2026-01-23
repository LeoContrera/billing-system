"""
URLs para la app customers.
"""

from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('search/', views.search_customers, name='search'),
]
