from django.db import models
from decimal import Decimal # Import Decimal
from customers.models import Customers
from packages.models import Packages # Import Packages
from shops.models import Shops
# from django.contrib.auth import get_user_model # Use if linking agent to Users model later

# User = get_user_model() # Use if linking agent to Users model later

class Refills(models.Model):
    """
    Tracks individual customer water refill transactions.
    """
    class PaymentMode(models.TextChoices):
        MPESA = 'MPESA', 'MPESA'
        CASH = 'CASH', 'CASH'
        CREDIT = 'CREDIT', 'Credit'
        FREE = 'FREE', 'Free' # For loyalty refills

    # Customer FK now implicitly uses the Customer's 'id' PK
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE, related_name='refills', null=True, blank=True) # Allow anonymous refills? If not, remove null/blank
    shop = models.ForeignKey(Shops, on_delete=models.CASCADE, related_name='refills')
    # Link to the specific Package being refilled
    package = models.ForeignKey(Packages, on_delete=models.PROTECT, related_name='refills')
    quantity = models.IntegerField(default=1)
    # Use TextChoices for paymentMode
    payment_mode = models.CharField(
        max_length=7,
        choices=PaymentMode.choices
    )
    # Use DecimalField for cost
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    # Boolean to indicate if this specific refill was the free one from loyalty
    is_free = models.BooleanField(default=False, help_text="True if this was a free refill earned through loyalty.")
    # Boolean to indicate if this refill contains both free and paid portions
    is_partially_free = models.BooleanField(default=False, help_text="True if this refill contains both free and paid portions.")
    # Fields to track quantity breakdown for partially free refills
    free_quantity = models.IntegerField(default=0, help_text="Number of free refills in this transaction.")
    paid_quantity = models.IntegerField(default=0, help_text="Number of paid refills in this transaction.")
    # Field to track refill counts for loyalty program
    loyalty_refill_count = models.IntegerField(default=0, help_text="Number of refills to count toward loyalty program.")
    # Delivery status/fee: null=Not Delivered, 0=Delivered(Free), >0 = Delivery Fee Charged
    delivered = models.IntegerField(
        null=True,
        blank=True,
        help_text="Null=Not Delivered, 0=Delivered(Free), >0 = Delivery Fee Charged"
        )
    # created_at = models.DateTimeField(auto_now_add=True) # Renamed 'date'
    created_at = models.DateTimeField() # Renamed 'date'
    agent_name = models.CharField(max_length=20, default='Brian') # Kept as CharField for now
    # agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_refills') # Future: Link to Users model

    def __str__(self):
        cust_name = self.customer.names if self.customer else "Anonymous"
        status = " (Free)" if self.is_free else ""
        return f"{cust_name} - {self.quantity} x {self.package.water_amount_label} Refill{status} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name_plural = 'Refills'
        ordering = ['-created_at'] # Show newest first