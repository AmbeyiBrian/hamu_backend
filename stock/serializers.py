from rest_framework import serializers
from django.db.models import Sum
from django.db import transaction
from .models import StockItem, StockLog
from shops.serializers import ShopSerializer
from .services import StockCalculationService


class StockLogSerializer(serializers.ModelSerializer):
    shop_details = ShopSerializer(source='shop', read_only=True)
    stock_item_name = serializers.CharField(source='stock_item.item_name', read_only=True)
    stock_item_type = serializers.CharField(source='stock_item.item_type', read_only=True)
    
    class Meta:
        model = StockLog
        fields = [
            'id', 'stock_item', 'stock_item_name', 'stock_item_type',
            'quantity_change', 'notes', 'shop', 'shop_details',
            'director_name', 'log_date'
        ]
        extra_kwargs = {
            'stock_item': {'write_only': True},
            'shop': {'write_only': True}
        }
    
    @transaction.atomic
    def create(self, validated_data):
        # Create the stock log entry
        stock_log = StockLog.objects.create(**validated_data)
        
        try:
            # Process water bundle creation if applicable
            # This automatically deducts bottles and shrink wraps as needed
            StockCalculationService.process_water_bundle_creation(stock_log)
        except ValueError as e:
            # If there's an error in processing the water bundle,
            # delete the created stock log and raise the error
            stock_log.delete()
            raise serializers.ValidationError(str(e))
        
        return stock_log


class StockItemSerializer(serializers.ModelSerializer):
    shop_details = ShopSerializer(source='shop', read_only=True)
    current_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = StockItem
        fields = [
            'id', 'shop', 'shop_details', 'item_name', 'item_type',
            'unit', 'created_at', 'current_quantity'
        ]
        extra_kwargs = {
            'shop': {'write_only': True}
        }
    
    def get_current_quantity(self, obj):
        """Calculate current stock level using the StockCalculationService"""
        return StockCalculationService.get_current_stock_level(obj)
        
    def to_representation(self, instance):
        """Add a low_stock warning if quantity is below threshold"""
        representation = super().to_representation(instance)
        current_qty = representation.get('current_quantity', 0)
        
        # Set thresholds based on item types
        threshold = 5  # Default threshold
        if instance.item_type == 'Bottle':
            threshold = 10
        elif instance.item_type == 'Shrink Wrap':
            threshold = 3
        elif instance.item_type == 'Cap':
            threshold = 20
        elif instance.item_type == 'Label':
            threshold = 20
            
        representation['low_stock'] = current_qty < threshold
        return representation