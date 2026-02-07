from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='base.html'), name='home'),
    path('dashboard/', include('dashboard.urls')),
    path('customers/', include('customers.urls')),
    path('products/', include('products.urls')),
    path('inventory/', include('inventory.urls')),
    path('sale/', include('sale.urls')),
    path('payments/', include('payments.urls')),
    path('invoices/', include('invoices.urls')),
    path('cash-session/', include('cash_session.urls')),
]
