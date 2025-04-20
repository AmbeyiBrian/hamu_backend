from django.db import models

class Shops(models.Model):
    """
    Represents a physical shop/branch location.
    """
    shopName = models.CharField(max_length=30, unique=True) # Added unique=True assuming shop names should be unique
    # Interval for free refills (e.g., buy 7 get 8th free means interval is 7)
    freeRefillInterval = models.IntegerField(
        help_text="Number of paid refills needed to qualify for one free refill."
    )
    phone_number = models.CharField(max_length=13, default='0700000000')

    def __str__(self):
        return self.shopName

    class Meta:
        verbose_name_plural = 'Shops'