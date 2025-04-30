from rest_framework import serializers
from .models import MeterReading
from shops.serializers import ShopSerializer


class MeterReadingSerializer(serializers.ModelSerializer):
    shop_details = ShopSerializer(source='shop', read_only=True)
    
    class Meta:
        model = MeterReading
        fields = [
            'id', 'shop', 'shop_details', 'agent_name', 'value',
            'reading_type', 'reading_date'
        ]
        extra_kwargs = {
            'shop': {'write_only': True}
        }