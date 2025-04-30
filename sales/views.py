from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F, Count
from .models import Sales
from .serializers import SalesSerializer
from hamu_backend.permissions import IsShopAgentOrDirector


class SalesViewSet(viewsets.ModelViewSet):
    """
    API endpoint for sales management.
    Directors can see all sales across shops.
    Shop agents can only view sales from their shop.
    """
    serializer_class = SalesSerializer
    permission_classes = [IsShopAgentOrDirector]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['customer__names', 'customer__phone_number', 'agent_name']
    ordering_fields = ['sold_at', 'payment_mode', 'cost']
    filterset_fields = ['shop', 'customer', 'payment_mode', 'package']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_class == 'Director':
            # Directors see all sales across all shops
            return Sales.objects.all().select_related('shop', 'customer', 'package')
        else:
            # Agents only see sales from their shop
            return Sales.objects.filter(shop=user.shop).select_related('shop', 'customer', 'package')
    
    def perform_create(self, serializer):
        """Automatically set shop and agent_name for agent users"""
        user = self.request.user
        if user.user_class != 'Director' and not serializer.validated_data.get('shop'):
            serializer.validated_data['shop'] = user.shop
            
        if not serializer.validated_data.get('agent_name'):
            serializer.validated_data['agent_name'] = user.names
            
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def sales_summary(self, request):
        """
        Get a summary of sales by shop, package, and payment mode
        """
        user = request.user
        queryset = self.get_queryset()
        
        # Group by shop
        shop_summary = queryset.values('shop__shopName').annotate(
            total_sales=Count('id'),
            total_amount=Sum('cost')
        )
        
        # Group by package
        package_summary = queryset.values('package__sale_type', 'package__water_amount_label', 'package__bottle_type').annotate(
            total_sales=Count('id'),
            total_amount=Sum('cost')
        )
        
        # Group by payment mode
        payment_summary = queryset.values('payment_mode').annotate(
            total_sales=Count('id'),
            total_amount=Sum('cost')
        )
        
        return Response({
            'by_shop': shop_summary,
            'by_package': package_summary,
            'by_payment': payment_summary
        })
