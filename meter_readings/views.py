from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F, Q
from .models import MeterReading
from .serializers import MeterReadingSerializer
from hamu_backend.permissions import IsShopAgentOrDirector


class MeterReadingViewSet(viewsets.ModelViewSet):
    """
    API endpoint for water meter readings management.
    Directors can see all meter readings across shops.
    Shop agents can only view meter readings from their shop.
    """
    serializer_class = MeterReadingSerializer
    permission_classes = [IsShopAgentOrDirector]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['agent_name', 'reading_type']
    ordering_fields = ['reading_date', 'value']
    filterset_fields = ['shop', 'reading_type']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_class == 'Director':
            # Directors see all meter readings across all shops
            return MeterReading.objects.all().select_related('shop')
        else:
            # Agents only see meter readings from their shop
            return MeterReading.objects.filter(shop=user.shop).select_related('shop')
    
    def perform_create(self, serializer):
        """Automatically set shop and agent_name for agent users"""
        user = self.request.user
        if user.user_class != 'Director' and not serializer.validated_data.get('shop'):
            serializer.validated_data['shop'] = user.shop
            
        if not serializer.validated_data.get('agent_name'):
            serializer.validated_data['agent_name'] = user.names
            
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def consumption_report(self, request):
        """
        Generate a consumption report showing water usage over time
        """
        user = request.user
        queryset = self.get_queryset()
        
        # Filter by date range if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(reading_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(reading_date__lte=end_date)
            
        # Group by shop and reading_type
        shop_grouped = {}
        
        for reading in queryset.order_by('shop__shopName', 'reading_type', 'reading_date'):
            shop_name = reading.shop.shopName
            reading_type = reading.reading_type
            
            if shop_name not in shop_grouped:
                shop_grouped[shop_name] = {}
                
            if reading_type not in shop_grouped[shop_name]:
                shop_grouped[shop_name][reading_type] = []
                
            shop_grouped[shop_name][reading_type].append({
                'date': reading.reading_date,
                'value': reading.value
            })
        
        # Calculate consumption between consecutive readings
        for shop_name, readings_by_type in shop_grouped.items():
            for reading_type, readings in readings_by_type.items():
                for i in range(1, len(readings)):
                    readings[i]['consumption'] = readings[i]['value'] - readings[i-1]['value']
        
        return Response(shop_grouped)
