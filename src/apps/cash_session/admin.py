from django.contrib import admin
from .models import CashSession


@admin.register(CashSession)
class CashSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'opening_timestamp', 'closing_timestamp', 'status']
    list_filter = ['status', 'user']
    search_fields = ['user__username']
    readonly_fields = ['opening_timestamp']
    ordering = ['-opening_timestamp']
