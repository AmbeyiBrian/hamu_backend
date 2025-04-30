from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F, Case, When, IntegerField
from django.utils.dateparse import parse_date
from .models import StockItem, StockLog
from .serializers import StockItemSerializer, StockLogSerializer
from hamu_backend.permissions import IsShopAgentOrDirector
from .services import StockCalculationService
from .filters import StockLogFilter


class StockItemViewSet(viewsets.ModelViewSet):
    """
    API endpoint for stock items management.
    Directors can see all stock items across shops.
    Shop agents can only view stock items from their shop.
    """
    serializer_class = StockItemSerializer
    permission_classes = [IsShopAgentOrDirector]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['item_name', 'item_type']
    ordering_fields = ['item_name', 'item_type', 'created_at']
    filterset_fields = ['shop', 'item_type']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_class == 'Director':
            # Directors see all stock items across all shops
            return StockItem.objects.all().select_related('shop')
        else:
            # Agents only see stock items from their shop
            return StockItem.objects.filter(shop=user.shop).select_related('shop')
    
    def perform_create(self, serializer):
        """Automatically set shop for agent users"""
        user = self.request.user
        if user.user_class != 'Director' and not serializer.validated_data.get('shop'):
            serializer.validated_data['shop'] = user.shop
            
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """
        List stock items that are low in inventory
        """
        queryset = self.get_queryset()
        
        # Get threshold from query params or use defaults
        thresholds = {
            'Bottle': int(request.query_params.get('bottle_threshold', 10)),
            'Shrink Wrap': int(request.query_params.get('shrink_wrap_threshold', 3)),
            'Cap': int(request.query_params.get('cap_threshold', 20)),
            'Label': int(request.query_params.get('label_threshold', 20)),
            'default': int(request.query_params.get('default_threshold', 5))
        }
        
        # For each stock item, calculate current quantity using the service
        results = []
        for item in queryset:
            quantity = StockCalculationService.get_current_stock_level(item)
            
            # Get appropriate threshold based on item type
            threshold = thresholds.get(item.item_type, thresholds['default'])
            
            # Check if quantity is below threshold
            if quantity < threshold:
                results.append({
                    'id': item.id,
                    'shop': item.shop.shopName,
                    'item_name': item.item_name,
                    'item_type': item.item_type,
                    'current_quantity': quantity,
                    'threshold': threshold
                })
                
        return Response(results)
    
    @action(detail=False, methods=['get'])
    def stock_by_shop(self, request):
        """
        Get current stock levels for all items in a shop
        """
        user = self.request.user
        shop_id = request.query_params.get('shop_id')
        
        # If no shop_id provided and user is an agent, use their shop
        if not shop_id and user.user_class != 'Director':
            shop_id = user.shop.id
            
        if not shop_id:
            return Response({"error": "shop_id parameter is required for directors"}, status=400)
            
        # Get stock by shop using the service
        result = StockCalculationService.get_current_stock_by_shop(shop_id)
        return Response(result)
        
    @action(detail=False, methods=['get'])
    def sales_impact(self, request):
        """
        Calculate how sales have impacted stock levels
        """
        # Get query parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        shop_id = request.query_params.get('shop_id')
        
        # Parse dates if provided
        parsed_start_date = parse_date(start_date) if start_date else None
        parsed_end_date = parse_date(end_date) if end_date else None
        
        # If user is an agent and no shop_id provided, use their shop
        user = self.request.user
        if not shop_id and user.user_class != 'Director':
            shop_id = user.shop.id
            
        # Calculate impact using the service
        impact = StockCalculationService.calculate_stock_impact_from_sales(
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            shop_id=shop_id
        )
        
        # Format the response
        results = [
            {"item": item, "impact": quantity}
            for item, quantity in impact.items()
        ]
        
        return Response(results)
        
    @action(detail=False, methods=['get'])
    def refills_impact(self, request):
        """
        Calculate how refills have impacted stock levels (water usage)
        """
        # Get query parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        shop_id = request.query_params.get('shop_id')
        
        # Parse dates if provided
        parsed_start_date = parse_date(start_date) if start_date else None
        parsed_end_date = parse_date(end_date) if end_date else None
        
        # If user is an agent and no shop_id provided, use their shop
        user = self.request.user
        if not shop_id and user.user_class != 'Director':
            shop_id = user.shop.id
            
        # Calculate impact using the service
        impact = StockCalculationService.calculate_stock_impact_from_refills(
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            shop_id=shop_id
        )
        
        # Format the response
        results = [
            {"item": item, "impact": quantity}
            for item, quantity in impact.items()
        ]
        
        return Response(results)


class StockLogViewSet(viewsets.ModelViewSet):
    """
    API endpoint for stock log entries management.
    Directors can see all stock logs across shops.
    Shop agents can only view stock logs from their shop.
    """
    serializer_class = StockLogSerializer
    permission_classes = [IsShopAgentOrDirector]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['notes', 'director_name', 'stock_item__item_name']
    ordering_fields = ['log_date', 'quantity_change']
    filterset_class = StockLogFilter
    
    def get_queryset(self):
        user = self.request.user
        if user.user_class == 'Director':
            # Directors see all stock logs across all shops
            return StockLog.objects.all().select_related('shop', 'stock_item')
        else:
            # Agents only see stock logs from their shop
            return StockLog.objects.filter(shop=user.shop).select_related('shop', 'stock_item')
    
    def perform_create(self, serializer):
        """Automatically set shop and director_name for agent users"""
        user = self.request.user
        if user.user_class != 'Director' and not serializer.validated_data.get('shop'):
            serializer.validated_data['shop'] = user.shop
            
        if not serializer.validated_data.get('director_name'):
            serializer.validated_data['director_name'] = user.names
            
        serializer.save()
        
    @action(detail=False, methods=['get'])
    def reconciliation_report(self, request):
        """
        Compare StockLog entries with calculated impacts from sales and refills
        """
        # Get query parameters
        shop_id = request.query_params.get('shop_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # This endpoint would call StockCalculationService.reconcile_stocklogs_with_events()
        # and return a detailed reconciliation report
        # Implementation depends on specific business requirements
        
        return Response({"message": "Reconciliation report feature coming soon"})
