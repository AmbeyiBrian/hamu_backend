from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum
from .models import Credits
from .serializers import CreditsSerializer
from hamu_backend.permissions import IsShopAgentOrDirector


class CreditsViewSet(viewsets.ModelViewSet):
    """
    API endpoint for customer credits management.
    Directors can see all credits across shops.
    Shop agents can only view credits from their shop.
    """
    serializer_class = CreditsSerializer
    permission_classes = [IsShopAgentOrDirector]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['customer__names', 'customer__phone_number', 'agent_name']
    ordering_fields = ['payment_date', 'money_paid']
    filterset_fields = ['shop', 'customer', 'payment_mode']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_class == 'Director':
            # Directors see all credits across all shops
            return Credits.objects.all().select_related('shop', 'customer')
        else:
            # Agents only see credits from their shop
            return Credits.objects.filter(shop=user.shop).select_related('shop', 'customer')
    
    def perform_create(self, serializer):
        """Automatically set shop and agent_name for agent users"""
        user = self.request.user
        if user.user_class != 'Director' and not serializer.validated_data.get('shop'):
            serializer.validated_data['shop'] = user.shop
            
        if not serializer.validated_data.get('agent_name'):
            serializer.validated_data['agent_name'] = user.names
            
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def customer_balance(self, request):
        """
        Get the credit balance for each customer
        """
        from refills.models import Refills
        from sales.models import Sales
        
        user = self.request.user
        queryset = self.get_queryset()
        
        # Filter by customer if provided
        customer_id = request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # Calculate total credits paid by each customer
        credits_by_customer = queryset.values(
            'customer__id', 
            'customer__names', 
            'customer__phone_number',
            'shop__shopName'
        ).annotate(
            total_credit=Sum('money_paid')
        )
        
        # For each customer, calculate total spent on refills with CREDIT payment mode
        for customer_credit in credits_by_customer:
            customer_id = customer_credit['customer__id']
            
            # Get total spent on refills using credit
            refill_spent = Refills.objects.filter(
                customer_id=customer_id,
                payment_mode='CREDIT'
            ).aggregate(total=Sum('cost'))['total'] or 0
            
            # Get total spent on sales using credit
            sales_spent = Sales.objects.filter(
                customer_id=customer_id,
                payment_mode='CREDIT'
            ).aggregate(total=Sum('cost'))['total'] or 0
            
            # Calculate remaining balance
            total_spent = refill_spent + sales_spent
            customer_credit['total_spent'] = total_spent
            customer_credit['balance'] = customer_credit['total_credit'] - total_spent
        
        return Response(credits_by_customer)
