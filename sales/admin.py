from django.contrib import admin
from .models import Sales


@admin.register(Sales)
class SalesAdmin(admin.ModelAdmin):
    list_display = ('customer', 'shop', 'package', 'quantity', 'payment_mode', 'cost', 'sold_at')
    list_filter = ('shop', 'payment_mode', 'sold_at')
    search_fields = ('customer__names', 'customer__phone_number', 'agent_name')
    date_hierarchy = 'sold_at'
    readonly_fields = ('sold_at',)
