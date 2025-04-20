from rest_framework import serializers
from .models import Sales
from customers.serializers import CustomerLightSerializer
from packages.serializers import PackageSerializer
from shops.serializers import ShopSerializer
from stock.services import StockCalculationService
from django.db import transaction


class SalesSerializer(serializers.ModelSerializer):
    customer_details = CustomerLightSerializer(source='customer', read_only=True)
    package_details = PackageSerializer(source='package', read_only=True)
    shop_details = ShopSerializer(source='shop', read_only=True)
    
    class Meta:
        model = Sales
        fields = [
            'id', 'customer', 'customer_details', 'shop', 'shop_details',
            'package', 'package_details', 'quantity', 'payment_mode', 
            'cost', 'sold_at', 'agent_name'
        ]
        extra_kwargs = {
            'customer': {'write_only': True},
            'shop': {'write_only': True},
            'package': {'write_only': True}
        }
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Create a new sale record and deduct appropriate inventory items.
        - For bottle sales: deducts bottles and labels
        - For water bundles: deducts the corresponding bundle
        """
        agent_name = validated_data.get('agent_name', 'System')
        
        # Create the sale record
        sale = super().create(validated_data)
        
        # Process inventory deduction for the sale
        try:
            StockCalculationService.deduct_stock_for_sale(sale, agent_name)
        except ValueError as e:
            # Log the error but don't prevent the sale from being recorded
            # This allows business to continue even if stock tracking has issues
            print(f"Inventory deduction warning: {str(e)}")
        
        return sale