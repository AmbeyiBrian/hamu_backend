from django.db import models
from decimal import Decimal # Import Decimal
from customers.models import Customers
from shops.models import Shops
from django.utils import timezone
# from django.contrib.auth import get_user_model # Use if linking agent to Users model later

# User = get_user_model() # Use if linking agent to Users model later

class Credits(models.Model):
    """
    Tracks payments made by customers against their credit balance.
    """
    class PaymentMode(models.TextChoices):
        MPESA = 'MPESA', 'MPESA'
        CASH = 'CASH', 'CASH'

    # Customer FK now implicitly uses the Customer's 'id' PK
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE, related_name='credit_payments')
    # Removed default=1, shop should be explicitly provided
    shop = models.ForeignKey(Shops, on_delete=models.CASCADE, related_name='credit_payments')
    # Use DecimalField for money_paid
    money_paid = models.DecimalField(max_digits=10, decimal_places=2)
    # Use TextChoices for payment_mode
    payment_mode = models.CharField(
        max_length=20,
        choices=PaymentMode.choices,
        default=PaymentMode.MPESA
    )
    payment_date = models.DateTimeField() # Renamed 'date'
    # payment_date = models.DateTimeField(auto_now_add=True) # Renamed 'date'
    agent_name = models.CharField(max_length=20) # Kept as CharField for now
    # agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_credits') # Future: Link to Users model

    created_at = models.DateTimeField(default=timezone.now) # Renamed 'date'
    modified_at = models.DateTimeField(auto_now=True) # Renamed 'date'
    class Meta:
        verbose_name_plural = 'Credit Payments' # Changed name
        ordering = ['-payment_date']

    def __str__(self):
        return f"Credit payment of {self.money_paid} by {self.customer} ({self.payment_mode}) on {self.payment_date.strftime('%Y-%m-%d')}"