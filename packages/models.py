from django.db import models
from decimal import Decimal # Import Decimal
from shops.models import Shops
from django.core.exceptions import ValidationError

class Packages(models.Model):
    """
    Defines the types of water packages/services offered (refills, new sales).
    """
    class SaleType(models.TextChoices):
        REFILL = 'REFILL', 'Refill'
        SALE = 'SALE', 'Sale' # e.g., New bottle purchase
    
    class BottleType(models.TextChoices):
        DISPOSABLE = 'DISPOSABLE', 'Disposable'
        HARD = 'HARD', 'Hard'
        REFILL = 'REFILL', 'Refill'
        LOYAL_CUSTOMER = 'LOYAL_CUSTOMER', 'Loyal Customer'
        LOYAL_CUSTOMER_MBURU = 'LOYAL_CUSTOMER_MBURU', 'Loyal Customer Mburu'
        DIRECTOR = 'DIRECTOR', 'Director'
        BUNDLE = 'BUNDLE', 'Bundle'
        

    shop = models.ForeignKey(Shops, on_delete=models.CASCADE, related_name='packages')
    # Use TextChoices for saleType
    sale_type = models.CharField(
        max_length=10,
        choices=SaleType.choices,
        default=SaleType.REFILL
    )
    # Bottle type is only applicable for SALE type, with specific choices
    bottle_type = models.CharField(
        max_length=40, 
        choices=BottleType.choices,
        blank=True, 
        null=True,
        help_text="Bottle type (only required for Sale type: Disposable, Hard, Refill, Loyal Customer, Director, or Bundle)"
    )
    # Amount of water in Liters (can be descriptive like '5L', '10L', '20L')

    water_amount_label = models.DecimalField(
        max_digits=5,  # Adjust this depending on your expected max value
        decimal_places=1,  # Adjust this to control how many decimals you want
        help_text="Amount of water in Liters (e.g., 5.00, 10.5, 20.75)"
)    # Optional richer description
    description = models.CharField(max_length=50, blank=True, help_text="Optional extra description if needed")
    # Use DecimalField for price
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    date_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True) # Track creation

    def clean(self):
        """Validate model fields based on business rules"""
        super().clean()
        
        # For SALE type, bottle_type is required and must be one of the valid choices
        if self.sale_type == self.SaleType.SALE and not self.bottle_type:
            raise ValidationError({'bottle_type': 'Bottle type is required for Sale packages'})
            
        # For REFILL type, bottle_type should be empty
        if self.sale_type == self.SaleType.REFILL and self.bottle_type:
            # Just clear it automatically rather than raising an error
            self.bottle_type = None

    def save(self, *args, **kwargs):
        """Override save to ensure validation is always run"""
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        # Construct a clearer string representation
        parts = [str(self.sale_type), str(self.water_amount_label)]
        
        if self.description:
            parts.append(f"({self.description})")
            
        if self.bottle_type and self.sale_type == self.SaleType.SALE:
            parts.append(f"[{self.bottle_type}]")
            
        parts.append(f"@ {self.price}")
        
        return ' '.join(parts)


    class Meta:
        verbose_name_plural = 'Packages'
        # Ensure combinations are unique per shop
        unique_together = (
            ('shop', 'sale_type', 'water_amount_label', 'bottle_type', 'description', 'price') # Price included as slight variations might exist
        )
        ordering = ['shop', 'sale_type', 'price'] # Default ordering