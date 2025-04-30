from django.shortcuts import render
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Shops
from .serializers import ShopSerializer
from hamu_backend.permissions import IsDirector, IsShopAgentOrDirector


class ShopViewSet(viewsets.ModelViewSet):
    """
    API endpoint for shops management.
    Directors can see and manage all shops.
    Shop agents can only view their own shop.
    """
    serializer_class = ShopSerializer
    permission_classes = [IsShopAgentOrDirector]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['shopName']
    ordering_fields = ['shopName']
    filterset_fields = ['shopName', 'freeRefillInterval']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_class == 'Director':
            # Directors see all shops
            return Shops.objects.all()
        else:
            # Agents only see their shop
            return Shops.objects.filter(id=user.shop.id)
