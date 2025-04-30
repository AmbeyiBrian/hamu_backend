from django.contrib import admin
from .models import MeterReading


@admin.register(MeterReading)
class MeterReadingAdmin(admin.ModelAdmin):
    list_display = ('shop', 'reading_type', 'value', 'agent_name', 'reading_date')
    list_filter = ('shop', 'reading_type', 'reading_date')
    search_fields = ('agent_name', 'shop__shopName')
    date_hierarchy = 'reading_date'
    readonly_fields = ('reading_date',)
