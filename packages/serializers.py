from rest_framework import serializers
from .models import Packages
from shops.serializers import ShopSerializer


class PackageSerializer(serializers.ModelSerializer):
    shop_details = ShopSerializer(source='shop', read_only=True)
    
    class Meta:
        model = Packages
        fields = [
            'id', 'shop', 'shop_details', 'sale_type', 'bottle_type', 
            'water_amount_label', 'description', 'price', 
            'date_updated', 'created_at'
        ]
        extra_kwargs = {
            'shop': {'write_only': True}
        }