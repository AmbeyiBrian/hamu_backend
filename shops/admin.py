from django.contrib import admin
from .models import Shops


@admin.register(Shops)
class ShopsAdmin(admin.ModelAdmin):
    list_display = ('shopName', 'phone_number', 'freeRefillInterval')
    search_fields = ('shopName', 'phone_number')
    list_filter = ('freeRefillInterval',)
