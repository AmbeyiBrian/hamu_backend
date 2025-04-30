from django.shortcuts import render
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Packages
from .serializers import PackageSerializer
from hamu_backend.permissions import IsShopAgentOrDirector


class PackageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for packages/products management.
    Directors can see and manage all packages across shops.
    Shop agents can only view packages from their shop.
    """
    serializer_class = PackageSerializer
    permission_classes = [IsShopAgentOrDirector]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['water_amount_label', 'bottle_type', 'description']
    ordering_fields = ['sale_type', 'price', 'water_amount_label']
    filterset_fields = ['shop', 'sale_type', 'bottle_type', 'water_amount_label']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_class == 'Director':
            # Directors see all packages across all shops
            return Packages.objects.all().select_related('shop')
        else:
            # Agents only see packages from their shop
            return Packages.objects.filter(shop=user.shop).select_related('shop')
    
    def perform_create(self, serializer):
        """Automatically set shop for agent users"""
        user = self.request.user
        if user.user_class != 'Director' and not serializer.validated_data.get('shop'):
            serializer.save(shop=user.shop)
        else:
            serializer.save()
