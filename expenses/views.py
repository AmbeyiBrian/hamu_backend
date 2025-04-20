from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum
from .models import Expenses
from .serializers import ExpensesSerializer
from hamu_backend.permissions import IsShopAgentOrDirector


class ExpensesViewSet(viewsets.ModelViewSet):
    """
    API endpoint for shop expenses management.
    Directors can see all expenses across shops.
    Shop agents can only view expenses from their shop.
    """
    serializer_class = ExpensesSerializer
    permission_classes = [IsShopAgentOrDirector]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description', 'agent_name']
    ordering_fields = ['created_at', 'cost']
    filterset_fields = ['shop', 'agent_name']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_class == 'Director':
            # Directors see all expenses across all shops
            return Expenses.objects.all().select_related('shop')
        else:
            # Agents only see expenses from their shop
            return Expenses.objects.filter(shop=user.shop).select_related('shop')
    
    def perform_create(self, serializer):
        """Automatically set shop and agent_name for agent users"""
        user = self.request.user
        if user.user_class != 'Director' and not serializer.validated_data.get('shop'):
            serializer.validated_data['shop'] = user.shop
            
        if not serializer.validated_data.get('agent_name'):
            serializer.validated_data['agent_name'] = user.names
            
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def expenses_summary(self, request):
        """
        Generate a summary of expenses by shop and month
        """
        user = request.user
        queryset = self.get_queryset()
        
        # Filter by date range if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
            
        # Group by shop and month
        from django.db.models.functions import TruncMonth
        
        month_summary = queryset.annotate(
            month=TruncMonth('created_at')
        ).values(
            'shop__shopName',
            'month'
        ).annotate(
            total_expenses=Sum('cost')
        ).order_by('shop__shopName', 'month')
        
        # Group by description type
        description_summary = queryset.values(
            'shop__shopName',
            'description'
        ).annotate(
            total_expenses=Sum('cost')
        ).order_by('shop__shopName', '-total_expenses')
        
        return Response({
            'by_month': list(month_summary),
            'by_description': list(description_summary)
        })
