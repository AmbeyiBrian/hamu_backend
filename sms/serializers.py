from rest_framework import serializers
from .models import SMS
from users.serializers import UserSerializer


class SMSSerializer(serializers.ModelSerializer):
    """Serializer for the SMS model"""
    sender_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SMS
        fields = [
            'id', 'message_body', 'target_phone', 'sent_at', 'sender', 'sender_name'
        ]
        read_only_fields = ['id', 'sent_at']
    
    def get_sender_name(self, obj):
        """Get the name of the sender"""
        if obj.sender:
            return obj.sender.names
        return None


class SMSSendToCustomerSerializer(serializers.Serializer):
    """Serializer for sending an SMS to a customer"""
    customer_id = serializers.IntegerField()
    message = serializers.CharField()


class SMSSendCustomSerializer(serializers.Serializer):
    """Serializer for sending a custom SMS"""
    recipients = serializers.ListField(child=serializers.CharField())
    message = serializers.CharField()


class SMSSendToShopCustomersSerializer(serializers.Serializer):
    """Serializer for sending an SMS to all customers of a shop"""
    shop_id = serializers.IntegerField()
    message = serializers.CharField()


class SMSSendToCreditCustomersSerializer(serializers.Serializer):
    """Serializer for sending an SMS to customers with credits"""
    message = serializers.CharField()


class SMSSendFreeRefillSerializer(serializers.Serializer):
    """Serializer for sending a free refill notification"""
    customer_id = serializers.IntegerField()
    is_thankyou = serializers.BooleanField(required=False, default=False)