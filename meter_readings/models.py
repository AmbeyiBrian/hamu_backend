from django.db import models
from shops.models import Shops
# from django.contrib.auth import get_user_model # Use if linking agent to Users model later

# User = get_user_model() # Use if linking agent to Users model later

class MeterReading(models.Model):
    """
    Stores water meter readings for different machines within a shop.
    """
    class ReadingType(models.TextChoices):
        BLUE_RIGHT = 'Blue Machine Right', 'Blue Machine Right'
        BLUE_LEFT = 'Blue Machine Left', 'Blue Machine Left'
        BLUE_SINGLE = 'Blue Machine', 'Blue Machine' # If only one blue machine exists
        PURIFIER = 'Purifier Machine', 'Purifier Machine'
        # Add more types as needed

    shop = models.ForeignKey(Shops, on_delete=models.CASCADE, related_name='meter_readings')
    agent_name = models.CharField(max_length=30) # Kept as CharField for now
    # agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_meter_readings') # Future: Link to Users model
    value = models.FloatField(help_text="The reading value from the meter.")
    # Ensure upload_to is appropriate
    meter_photo = models.ImageField(upload_to='meter_reading_photos/', blank=True, null=True) # Made optional
    # Use TextChoices for reading_type
    reading_type = models.CharField(
        max_length=30,
        choices=ReadingType.choices
    )    
    reading_date = models.DateField() # Changed to auto_now_add to automatically set the date when created
    reading_time = models.TimeField() # Removed auto_now_add to allow setting historical times

    # reading_date = models.DateField(auto_now_add=True) # Changed to auto_now_add to automatically set the date when created
    # reading_time = models.TimeField(auto_now_add=True) # Removed auto_now_add to allow setting historical times

    class Meta:
        # Unique constraint remains
        unique_together = ['shop', 'reading_date', 'reading_type']
        verbose_name_plural = 'Meter Readings'
        ordering = ['-reading_date', '-reading_time']

    def __str__(self):
        return f"{self.reading_type} reading at {self.shop} on {self.reading_date}: {self.value}"