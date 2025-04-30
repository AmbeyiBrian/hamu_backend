from django.contrib import admin
from .models import Customers


@admin.register(Customers)
class CustomersAdmin(admin.ModelAdmin):
    list_display = ('names', 'phone_number', 'shop', 'apartment_name', 'date_registered')
    list_filter = ('shop', 'date_registered')
    search_fields = ('names', 'phone_number', 'apartment_name', 'room_number')
    date_hierarchy = 'date_registered'
    readonly_fields = ('date_registered',)
