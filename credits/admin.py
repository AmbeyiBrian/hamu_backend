from django.contrib import admin
from .models import Credits


@admin.register(Credits)
class CreditsAdmin(admin.ModelAdmin):
    list_display = ('customer', 'shop', 'money_paid', 'payment_mode', 'payment_date', 'agent_name')
    list_filter = ('shop', 'payment_mode', 'payment_date')
    search_fields = ('customer__names', 'customer__phone_number', 'agent_name')
    date_hierarchy = 'payment_date'
    readonly_fields = ('payment_date',)
