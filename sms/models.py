from django.db import models
from users.models import Users  # Import the User model

class SMS(models.Model):
    """
    Logs outgoing SMS messages.
    """
    # Changed max_length to be more reasonable for a phone number
    target_phone = models.CharField(max_length=20, help_text="Recipient phone number")
    sent_at = models.DateTimeField(auto_now_add=True) # Renamed 'date'
    sender = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, related_name='sent_sms')  # User who sent the SMS
    message_body = models.TextField() # Changed to TextField for potentially longer messages
    # Optional: Add status field if you track delivery status from provider
    # status = models.CharField(max_length=20, blank=True, null=True, choices=[...])

    def __str__(self):
        return f"SMS to {self.target_phone} at {self.sent_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name_plural = 'SMS Log'
        ordering = ['-sent_at']