from rest_framework import serializers
from .models import Refills
from customers.serializers import CustomerLightSerializer
from packages.serializers import PackageSerializer
from shops.serializers import ShopSerializer
from sms.utils import send_free_refill_notification, send_free_refill_thank_you_sms
from stock.services import StockCalculationService
from django.db import transaction


class RefillSerializer(serializers.ModelSerializer):
    customer_details = CustomerLightSerializer(source='customer', read_only=True)
    package_details = PackageSerializer(source='package', read_only=True)
    shop_details = ShopSerializer(source='shop', read_only=True)
    is_next_refill_free = serializers.SerializerMethodField()
    free_refills_available = serializers.SerializerMethodField()
    
    class Meta:
        model = Refills
        fields = [
            'id', 'customer', 'customer_details', 'shop', 'shop_details',
            'package', 'package_details', 'quantity', 'payment_mode', 
            'cost', 'is_free', 'is_partially_free', 'free_quantity', 
            'paid_quantity', 'loyalty_refill_count', 'delivered', 
            'created_at', 'agent_name', 'is_next_refill_free',
            'free_refills_available'
        ]
        extra_kwargs = {
            'customer': {'write_only': True},
            'shop': {'write_only': True},
            'package': {'write_only': True}
        }
    
    def get_is_next_refill_free(self, obj):
        """Check if the customer's next refill should be free based on loyalty."""
        if not obj.customer:
            return False
        
        # Get the shop's freeRefillInterval setting
        interval = obj.shop.freeRefillInterval
        if interval <= 0:
            return False
            
        # Count refills since the last free refill using the loyalty_refill_count
        refills_since_free = 0
        
        # Get all refills since the last free refill
        last_free_refill = Refills.objects.filter(
            customer=obj.customer,
            is_free=True
        ).order_by('-created_at').first()
        
        # If there was a last free refill, get refills after that
        if last_free_refill:
            refills_query = Refills.objects.filter(
                customer=obj.customer,
                created_at__gt=last_free_refill.created_at,
                is_free=False
            )
        else:
            # Otherwise get all non-free refills
            refills_query = Refills.objects.filter(
                customer=obj.customer,
                is_free=False
            )
        
        # Sum the loyalty_refill_count field
        refills_since_free = sum(refills_query.values_list('loyalty_refill_count', flat=True))
        
        # Return True if customer has reached the threshold
        return refills_since_free >= interval
    
    def get_free_refills_available(self, obj):
        """Calculate how many free refills the customer has earned."""
        if not obj.customer:
            return 0
            
        # Get the shop's freeRefillInterval setting
        interval = obj.shop.freeRefillInterval
        if interval <= 0:
            return 0
            
        # Count refills since the last free refill using the loyalty_refill_count
        refills_since_free = 0
        
        # Get all refills since the last free refill
        last_free_refill = Refills.objects.filter(
            customer=obj.customer,
            is_free=True
        ).order_by('-created_at').first()
        
        # If there was a last free refill, get refills after that
        if last_free_refill:
            refills_query = Refills.objects.filter(
                customer=obj.customer,
                created_at__gt=last_free_refill.created_at,
                is_free=False
            )
        else:
            # Otherwise get all non-free refills
            refills_query = Refills.objects.filter(
                customer=obj.customer,
                is_free=False
            )
        
        # Sum the loyalty_refill_count field
        refills_since_free = sum(refills_query.values_list('loyalty_refill_count', flat=True))
        
        # Calculate how many free refills are available
        return refills_since_free // interval
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Create a new refill record with data from the frontend.
        Also deducts caps and labels from inventory based on refill package.
        """
        customer = validated_data.get('customer')
        shop = validated_data.get('shop')
        agent_name = validated_data.get('agent_name', 'System')
        
        # Create the refill record directly with frontend data
        refill = super().create(validated_data)
        
        # Process inventory deduction for caps and labels
        try:
            StockCalculationService.deduct_caps_and_labels_for_refill(refill, agent_name)
        except ValueError as e:
            # Log the error but don't prevent the refill from being recorded
            # This allows the business to continue even if stock tracking has issues
            print(f"Inventory deduction warning: {str(e)}")
        
        # Only send notifications after creating the refill
        if customer:
            # Send SMS notification if this was a free/partially free refill
            if refill.free_quantity > 0:
                # Use the new function that includes free quantity information
                send_free_refill_thank_you_sms(refill.customer, refill.free_quantity, refill.package.water_amount_label)
            # If customer is close to earning a free refill, notify them
            elif shop and shop.freeRefillInterval > 0:
                # Calculate refills since last free one
                last_free_refill = Refills.objects.filter(
                    customer=customer,
                    is_free=True
                ).order_by('-created_at').first()
                
                if last_free_refill:
                    refills_query = Refills.objects.filter(
                        customer=customer,
                        created_at__gt=last_free_refill.created_at,
                        is_free=False
                    )
                else:
                    refills_query = Refills.objects.filter(
                        customer=customer,
                        is_free=False
                    )
                
                refills_since_free = sum(refills_query.values_list('loyalty_refill_count', flat=True))
                
                # If they're one refill away from a free one
                if shop.freeRefillInterval > 0:
                    remaining_for_free = shop.freeRefillInterval - (refills_since_free % shop.freeRefillInterval)
                    if remaining_for_free == 1:
                        send_free_refill_notification(customer, is_thankyou=False)
        
        return refill