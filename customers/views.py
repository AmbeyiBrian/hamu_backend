from django.shortcuts import render
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Customers
from .serializers import CustomerSerializer
from hamu_backend.permissions import IsShopAgentOrDirector


class CustomerViewSet(viewsets.ModelViewSet):
    """
    API endpoint for customers management.
    Directors can see and manage all customers across shops.
    Shop agents can only view and manage customers from their shop.
    """
    serializer_class = CustomerSerializer
    permission_classes = [IsShopAgentOrDirector]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['names', 'phone_number', 'apartment_name', 'room_number']
    ordering_fields = ['names', 'date_registered']
    filterset_fields = ['shop', 'apartment_name']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_class == 'Director':
            # Directors see all customers across all shops
            return Customers.objects.all().select_related('shop')
        else:
            # Agents only see customers from their shop
            return Customers.objects.filter(shop=user.shop).select_related('shop')
    
    def perform_create(self, serializer):
        """Automatically set shop for agent users"""
        user = self.request.user
        if user.user_class != 'Director' and not serializer.validated_data.get('shop'):
            serializer.save(shop=user.shop)
        else:
            serializer.save()
