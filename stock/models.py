from django.db import models
from shops.models import Shops
# from django.contrib.auth import get_user_model # Use if linking agent/director to Users model later

# User = get_user_model() # Use if linking agent/director to Users model later

class StockItem(models.Model):
    """
    Defines the types of items that can be stocked (e.g., Bottles, Caps, Labels).
    """
    # Define closed choices for item names
    class ItemName(models.TextChoices):
        BOTTLE = 'Bottle', 'Bottle'
        CAP = 'Cap', 'Cap'
        LABEL = 'Label', 'Label'
        SHRINK_WRAP = 'Shrink Wrap', 'Shrink Wrap'
        WATER_BUNDLE= 'Water Bundle', 'Water Bundle'
        
    # Define choices for bottle types
    class BottleType(models.TextChoices):
        HALF_LITER = '0.5L', '0.5L'
        ONE_LITER = '1L', '1L'
        ONE_HALF_LITER = '1.5L', '1.5L'
        TWO_LITER = '2L', '2L'
        FIVE_LITER = '5L', '5L'
        TEN_LITER = '10L', '10L'
        TWENTY_LITER = '20L', '20L'
        TWENTY_LITER_HARD = '20L Hard', '20L Hard (Reusable)'
        
    # Define choices for cap types
    class CapType(models.TextChoices):
        TEN_LITER = '10/20L', '10/20L'
        
    # Define choices for label types
    class LabelType(models.TextChoices):
        FIVE_LITER = '5L', '5L'
        TEN_LITER = '10L', '10L'
        TWENTY_LITER = '20L', '20L'
    
    # Define choices for shrink wrap types
    class ShrinkWrapType(models.TextChoices):
        TWELVE_X_ONE_L = '12x1L', '12x1L'
        TWENTY_FOUR_X_ZERO_POINT_FIVE_L = '24x0.5L', '24x0.5L'
        EIGHT_X_ONE_POINT_FIVE_L = '8x1.5L', '8x1.5L'
        # Add more shrink wrap types if needed

    class WaterBundleType(models.TextChoices):
        TWELVE_X_ONE_L = '12x1L', '12x1L'
        TWENTY_FOUR_X_ZERO_POINT_FIVE_L = '24x0.5L', '24x0.5L'
        EIGHT_X_ONE_POINT_FIVE_L = '8x1.5L', '8x1.5L'
    
    shop = models.ForeignKey(Shops, on_delete=models.CASCADE, related_name='stock_items')
    
    # Name of the stock item from closed choices
    item_name = models.CharField(
        max_length=100,
        choices=ItemName.choices,
        help_text="Category of inventory item"
    )
    
    # Type depends on the selected item_name
    item_type = models.CharField(
        max_length=50,
        help_text="Specific type within the category"
    )
    
    # Unit of measure if not implied by name (e.g., 'piece', 'roll', 'kg')
    unit = models.CharField(max_length=20, default='piece')
    
    # Threshold for low stock warning (when to reorder)
    threshold = models.IntegerField(default=200, help_text="Threshold level for low stock warning")
    
    # Reorder point (when stock should be replenished)
    reorder_point = models.IntegerField(default=300, help_text="Stock level at which reordering is recommended")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """Validate that item_type is appropriate for the selected item_name"""
        from django.core.exceptions import ValidationError
        
        if self.item_name == self.ItemName.BOTTLE and self.item_type not in self.BottleType.values:
            raise ValidationError({"item_type": f"Invalid bottle type. Must be one of {', '.join(self.BottleType.values)}"})
        elif self.item_name == self.ItemName.CAP and self.item_type not in self.CapType.values:
            raise ValidationError({"item_type": f"Invalid cap type. Must be one of {', '.join(self.CapType.values)}"})
        elif self.item_name == self.ItemName.LABEL and self.item_type not in self.LabelType.values:
            raise ValidationError({"item_type": f"Invalid label type. Must be one of {', '.join(self.LabelType.values)}"})
        elif self.item_name == self.ItemName.SHRINK_WRAP and self.item_type not in self.ShrinkWrapType.values:
            raise ValidationError({"item_type": f"Invalid shrink wrap type. Must be one of {', '.join(self.ShrinkWrapType.values)}"})
        elif self.item_name == self.ItemName.WATER_BUNDLE and self.item_type not in self.WaterBundleType.values:
            raise ValidationError({"item_type": f"Invalid water bundle type. Must be one of {', '.join(self.WaterBundleType.values)}"})

    def __str__(self):
        return f"{self.item_name}: {self.item_type} at {self.shop}"

    class Meta:
        verbose_name_plural = 'Stock Items Definitions'
        unique_together = ('shop', 'item_name', 'item_type')
        ordering = ['shop', 'item_name', 'item_type']

class StockLog(models.Model):
    """
    Records changes (additions/removals) to the quantity of a specific StockItem.
    This replaces the old 'Stock' model.
    """
    stock_item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name='stock_logs')
    # Positive for additions, negative for removals/usage
    quantity_change = models.IntegerField(help_text="Positive for additions, negative for removals/usage.")
    # Optional field for notes about the change
    notes = models.CharField(max_length=255, blank=True)
    shop = models.ForeignKey(Shops, on_delete=models.CASCADE, related_name='stock_logs') # Link shop directly for easier filtering
    director_name = models.CharField(max_length=30) # Kept as CharField for now
    # director = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_stock_changes') # Future: Link to Users
    # log_date = models.DateTimeField(auto_now_add=True) # Renamed 'date'
    log_date = models.DateTimeField() # Renamed 'date'

    def __str__(self):
        action = "Added" if self.quantity_change > 0 else "Removed"
        return f"{action} {abs(self.quantity_change)} of {self.stock_item.item_name} on {self.log_date.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name_plural = 'Stock Change Log'
        ordering = ['-log_date']

# Note: Calculating the *current* stock level for a StockItem involves summing
# the 'quantity_change' from all related StockLog entries. This is usually done
# in a view or manager method, not stored directly on the StockItem model itself
# to avoid data duplication and potential inconsistencies.