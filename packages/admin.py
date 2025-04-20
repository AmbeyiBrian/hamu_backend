from django.contrib import admin
from .models import Packages


@admin.register(Packages)
class PackagesAdmin(admin.ModelAdmin):
    list_display = ('sale_type', 'water_amount_label', 'bottle_type', 'price', 'shop')
    list_filter = ('sale_type', 'shop', 'date_updated')
    search_fields = ('water_amount_label', 'bottle_type', 'description')
    readonly_fields = ('date_updated', 'created_at')
