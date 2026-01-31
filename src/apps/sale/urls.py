"""
URLs para la app sale (POS).
"""

from django.urls import path
from . import views

app_name = 'sale'

urlpatterns = [
    path('pos/', views.pos_index, name='pos_index'),
    path('create/', views.create_sale, name='create'),
    path('set-customer/', views.set_customer, name='set_customer'),
    path('add-item/', views.add_item, name='add_item'),
    path('add-payment/', views.add_payment, name='add_payment'),
    path('discount-global/', views.discount_global, name='discount_global'),
    path('discount-item/', views.discount_item, name='discount_item'),
    path('finalize/', views.finalize_sale, name='finalize'),
    path('preview-receipt-type/', views.preview_receipt_type, name='preview_receipt_type'),
]
