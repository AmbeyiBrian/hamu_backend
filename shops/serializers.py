from rest_framework import serializers
from .models import Shops


class ShopSerializer(serializers.ModelSerializer):
    customer_count = serializers.IntegerField(read_only=True, source='customers.count')
    
    class Meta:
        model = Shops
        fields = ['id', 'shopName', 'freeRefillInterval', 'phone_number', 'customer_count']