from django.contrib import admin
from django import forms
from .models import Packages


class PackagesForm(forms.ModelForm):
    class Meta:
        model = Packages
        fields = ['shop', 'sale_type', 'bottle_type', 'water_amount_label', 'description', 'price']


@admin.register(Packages)
class PackagesAdmin(admin.ModelAdmin):
    form = PackagesForm
    list_display = ('sale_type', 'water_amount_label', 'bottle_type', 'price', 'shop')
    list_filter = ('sale_type', 'shop', 'date_updated')
    search_fields = ('water_amount_label', 'bottle_type', 'description')
    readonly_fields = ('date_updated', 'created_at')
    
    fieldsets = [
        (None, {'fields': ['shop', 'sale_type', 'bottle_type', 'water_amount_label', 'description', 'price']}),
        ('Timestamps', {'fields': ['date_updated', 'created_at'], 'classes': ['collapse']}),
    ]
