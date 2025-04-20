from rest_framework import serializers
from .models import Customers
from shops.serializers import ShopSerializer


class CustomerSerializer(serializers.ModelSerializer):
    shop_details = ShopSerializer(source='shop', read_only=True)
    refill_count = serializers.IntegerField(source='refills.count', read_only=True)
    
    class Meta:
        model = Customers
        fields = [
            'id', 'shop', 'shop_details', 'names', 'phone_number', 
            'apartment_name', 'room_number', 'date_registered', 'refill_count'
        ]
        extra_kwargs = {
            'shop': {'write_only': True}
        }


class CustomerLightSerializer(serializers.ModelSerializer):
    """A lightweight serializer for Customers with minimal fields."""
    class Meta:
        model = Customers
        fields = ['id', 'shop', 'names', 'phone_number']