from django.db import models
from decimal import Decimal # Import Decimal
from shops.models import Shops
# from django.contrib.auth import get_user_model # Use if linking agent to Users model later

# User = get_user_model() # Use if linking agent to Users model later

class Expenses(models.Model):
    """
    Records operational expenses for a shop.
    """
    shop = models.ForeignKey(Shops, on_delete=models.CASCADE, related_name='expenses')
    description = models.CharField(max_length=100) # Increased length slightly
    # Use DecimalField for cost
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    # Ensure upload_to is appropriate
    receipt = models.ImageField(upload_to='receipts/', null=True, blank=True) # Made optional
    agent_name = models.CharField(max_length=20) # Kept as CharField for now
    # agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_expenses') # Future: Link to Users model
    # created_at = models.DateTimeField(auto_now_add=True) # Renamed 'dateTime'
    created_at = models.DateTimeField() # Renamed 'dateTime'

    class Meta:
        verbose_name_plural = 'Expenses'
        ordering = ['-created_at']

    def __str__(self):
        return f"Expense: {self.description} ({self.cost}) at {self.shop} on {self.created_at.strftime('%Y-%m-%d')}"