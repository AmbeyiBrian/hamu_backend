from django.db import models
from shops.models import Shops

class Customers(models.Model):
    """
    Represents a customer registered with a specific shop.
    Uses default Django ID as PK, phone_number must be unique.
    """
    shop = models.ForeignKey(Shops, on_delete=models.CASCADE, related_name='customers')
    names = models.CharField(max_length=50)
    # Phone number is unique but not the primary key
    phone_number = models.CharField(max_length=14, unique=False) # False for testing, True for production
    apartment_name = models.CharField(max_length=50, blank=True) # Made blank=True, might not always be relevant
    room_number = models.CharField(max_length=30, blank=True)    # Made blank=True
    date_registered = models.DateTimeField(null=True) # Renamed 'date' for clarity
    # date_registered = models.DateTimeField(auto_now_add=True, null=True) # Renamed 'date' for clarity

    def __str__(self):
        return f"{self.names} ({self.phone_number})"

    class Meta:
        verbose_name_plural = 'Customers'
        # Optional: Add constraint to ensure phone_number uniqueness per shop if needed
        # unique_together = ('shop', 'phone_number')