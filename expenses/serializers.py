from rest_framework import serializers
from .models import Expenses
from shops.serializers import ShopSerializer


class ExpensesSerializer(serializers.ModelSerializer):
    shop_details = ShopSerializer(source='shop', read_only=True)
    
    class Meta:
        model = Expenses
        fields = [
            'id', 'shop', 'shop_details', 'description', 'cost',
            'receipt', 'agent_name', 'created_at'
        ]
        extra_kwargs = {
            'shop': {'write_only': True}
        }