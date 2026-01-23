from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='base.html'), name='home'),
    path('customers/', include('customers.urls')),
    path('sale/', include('sale.urls')),
    path('payments/', include('payments.urls')),
]
