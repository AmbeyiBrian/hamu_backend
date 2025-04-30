from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.contrib import messages

# No model to register yet, but we can add custom admin actions
# to send SMS notifications directly from the admin interface

class SMSAdmin(admin.ModelAdmin):
    """
    Base class with SMS sending functionality.
    Inherit from this in other admin classes to add SMS capabilities.
    """
    
    def send_sms_notification(self, request, obj):
        """Button to send SMS notification for a specific object"""
        from .utils import send_batch_sms
        
        # This is just a placeholder - implement according to your needs
        if hasattr(obj, 'phone_number'):
            try:
                message = f"Notification from {obj._meta.verbose_name}: {obj}"
                send_batch_sms([obj.phone_number], message)
                return True
            except Exception as e:
                self.message_user(request, f"Error sending SMS: {str(e)}", messages.ERROR)
                return False
        return False
    
    def send_sms_button(self, obj):
        """Renders a button to send SMS notification"""
        if hasattr(obj, 'phone_number'):
            return format_html(
                '<a class="button" href="{}">Send SMS</a>',
                reverse('admin:send-sms', args=[obj._meta.app_label, obj._meta.model_name, obj.pk])
            )
        return "No phone number"
    
    send_sms_button.short_description = 'Send SMS'
    send_sms_button.allow_tags = True

# Note: You'll need to register actual URL patterns for the admin:send-sms action
# in your project's urls.py if you want to use the send_sms_button function
