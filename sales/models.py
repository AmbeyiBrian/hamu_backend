from django.db import models
from decimal import Decimal # Import Decimal
from customers.models import Customers
from packages.models import Packages # Import Packages
from shops.models import Shops
# from django.contrib.auth import get_user_model # Use if linking agent to Users model later

# User = get_user_model() # Use if linking agent to Users model later

class Sales(models.Model):
    """
    Tracks sales other than standard refills (e.g., new bottles with water).
    """
    class PaymentMode(models.TextChoices):
        MPESA = 'MPESA', 'MPESA'
        CASH = 'CASH', 'CASH'
        CREDIT = 'CREDIT', 'Credit'
        # FREE unlikely for new sales, but possible promotion
        # FREE = 'FREE', 'Free'

    # Customer FK now implicitly uses the Customer's 'id' PK
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE, related_name='sales', null=True, blank=True) # Allow anonymous sales?
    shop = models.ForeignKey(Shops, on_delete=models.CASCADE, related_name='sales')
    # Link to the specific Package being sold
    package = models.ForeignKey(Packages, on_delete=models.PROTECT, related_name='sales')
    quantity = models.IntegerField(default=1)
    # Use TextChoices for paymentMode
    payment_mode = models.CharField(
        max_length=7,
        choices=PaymentMode.choices,
        default=PaymentMode.CASH
    )
    # Use DecimalField for cost
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    # Delivery status/fee: null=Not Delivered, 0=Delivered(Free), >0 = Delivery Fee Charged
    delivered = models.IntegerField(
        null=True,
        blank=True,
        help_text="Null=Not Delivered, 0=Delivered(Free), >0 = Delivery Fee Charged"
    )
    # sold_at = models.DateTimeField(auto_now_add=True, null=True) # Renamed 'dateSold'
    sold_at = models.DateTimeField(null=True) # Renamed 'dateSold'
    agent_name = models.CharField(max_length=20, default='Unknown') # Kept as CharField for now
    # agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_sales') # Future: Link to Users model

    def __str__(self):
        cust_name = self.customer.names if self.customer else "Anonymous"
        # Removed redundant waterAmount, rely on package FK
        return f"{cust_name} - {self.quantity} x {self.package.water_amount_label} Sale on {self.sold_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name_plural = 'Sales'
        ordering = ['-sold_at'] # Show newest first