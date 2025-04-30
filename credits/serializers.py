from rest_framework import serializers
from .models import Credits
from customers.serializers import CustomerLightSerializer
from shops.serializers import ShopSerializer


class CreditsSerializer(serializers.ModelSerializer):
    customer_details = CustomerLightSerializer(source='customer', read_only=True)
    shop_details = ShopSerializer(source='shop', read_only=True)
    
    class Meta:
        model = Credits
        fields = [
            'id', 'customer', 'customer_details', 'shop', 'shop_details',
            'money_paid', 'payment_mode', 'payment_date', 'agent_name', 'created_at', 'modified_at', 
        ]
        extra_kwargs = {
            'customer': {'write_only': True},
            'shop': {'write_only': True}
        }