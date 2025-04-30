from django.contrib import admin
from .models import Refills


@admin.register(Refills)
class RefillsAdmin(admin.ModelAdmin):
    list_display = ('customer', 'shop', 'package', 'payment_mode', 'cost', 'is_free', 'created_at')
    list_filter = ('shop', 'payment_mode', 'is_free', 'created_at')
    search_fields = ('customer__names', 'customer__phone_number', 'agent_name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
