from django.contrib import admin
from django.db.models import Sum
from django import forms
from django.contrib import messages
from .models import StockItem, StockLog
from .services import StockCalculationService


class StockLogInline(admin.TabularInline):
    model = StockLog
    extra = 1
    fields = ('quantity_change', 'notes', 'director_name', 'log_date')
    readonly_fields = ('log_date',)


class StockItemAdminForm(forms.ModelForm):
    """Custom form for StockItem that dynamically updates item_type choices based on item_name"""
    # Override the item_type field to always be a Select widget
    item_type = forms.ChoiceField(
        choices=[], 
        required=True,
        help_text="Specific type within the category"
    )
    
    class Meta:
        model = StockItem
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If this is a new instance or an instance with an item_name
        selected_item_name = None
        
        # Get the item_name from the instance or POST data
        if self.instance.pk:
            selected_item_name = self.instance.item_name
        elif kwargs.get('data') and 'item_name' in kwargs['data']:
            selected_item_name = kwargs['data']['item_name']
        
        # Set initial choices based on available choices
        initial_choices = [('', '---------')]
        
        # If an item name is selected, load the appropriate choices
        if selected_item_name:
            if selected_item_name == StockItem.ItemName.BOTTLE:
                initial_choices = StockItem.BottleType.choices
            elif selected_item_name == StockItem.ItemName.CAP:
                initial_choices = StockItem.CapType.choices
            elif selected_item_name == StockItem.ItemName.LABEL:
                initial_choices = StockItem.LabelType.choices
            elif selected_item_name == StockItem.ItemName.SHRINK_WRAP:
                initial_choices = StockItem.ShrinkWrapType.choices
            elif selected_item_name == StockItem.ItemName.WATER_BUNDLE:
                initial_choices = StockItem.WaterBundleType.choices
        
        # Set the choices for the item_type field
        self.fields['item_type'].choices = initial_choices
        
        # Set the initial value if it exists
        if self.instance.pk and self.instance.item_type:
            self.fields['item_type'].initial = self.instance.item_type


class StockItemAdmin(admin.ModelAdmin):
    form = StockItemAdminForm
    list_display = ('item_name', 'item_type', 'shop', 'unit', 'current_quantity', 'created_at')
    list_filter = ('shop', 'item_name', 'item_type')
    search_fields = ('item_name', 'item_type')
    readonly_fields = ('created_at', 'current_quantity')
    inlines = [StockLogInline]
    fieldsets = (
        (None, {
            'fields': ('shop', 'item_name')
        }),
        ('Item Details', {
            'fields': ('item_type', 'unit')
        }),
        ('Tracking', {
            'fields': ('created_at', 'current_quantity')
        })
    )
    
    def current_quantity(self, obj):
        """Calculate current stock level by summing all stock log entries"""
        quantity = StockLog.objects.filter(stock_item=obj).aggregate(
            total=Sum('quantity_change')
        )['total'] or 0
        return quantity
    
    current_quantity.short_description = 'Current Quantity'
    
    class Media:
        js = [
            'admin/js/jquery.init.js',  # Load Django's jQuery
            'admin/js/stock_item_form.js',  # Our custom JS
        ]


@admin.register(StockLog)
class StockLogAdmin(admin.ModelAdmin):
    list_display = ('stock_item', 'shop', 'quantity_change', 'director_name', 'log_date')
    list_filter = ('shop', 'stock_item__item_name', 'stock_item__item_type', 'log_date')
    search_fields = ('stock_item__item_name', 'stock_item__item_type', 'notes', 'director_name')
    date_hierarchy = 'log_date'
    readonly_fields = ('log_date',)
    
    def save_model(self, request, obj, form, change):
        """
        Override save_model to process water bundle creation
        """
        super().save_model(request, obj, form, change)
        
        # Only process for new stock logs, not updates
        if not change and obj.stock_item.item_name == 'Water Bundle' and obj.quantity_change > 0:
            try:
                # Process water bundle creation
                created_logs = StockCalculationService.process_water_bundle_creation(obj)
                if created_logs:
                    messages.success(
                        request, 
                        f"Successfully created water bundle and deducted {len(created_logs)} related stock items."
                    )
            except ValueError as e:
                # If there's an error, delete the stock log and show error
                obj.delete()
                messages.error(request, str(e))


# Register StockItem with its custom admin
admin.site.register(StockItem, StockItemAdmin)
