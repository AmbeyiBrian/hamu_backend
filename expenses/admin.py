from django.contrib import admin
from .models import Expenses


@admin.register(Expenses)
class ExpensesAdmin(admin.ModelAdmin):
    list_display = ('shop', 'description', 'cost', 'agent_name', 'created_at')
    list_filter = ('shop', 'created_at')
    search_fields = ('description', 'agent_name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
