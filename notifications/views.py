from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Notification
from .serializers import NotificationSerializer
from hamu_backend.permissions import IsShopAgentOrDirector

class NotificationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for notifications management.
    Users can only view their own notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsShopAgentOrDirector]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'message']
    ordering_fields = ['timestamp', 'type', 'read']
    filterset_fields = ['type', 'read']
    
    def get_queryset(self):
        """
        Return only the user's own notifications
        """
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all of the user's notifications as read"""
        notifications = self.get_queryset()
        notifications.update(read=True)
        return Response({'status': 'All notifications marked as read'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a specific notification as read"""
        notification = self.get_object()
        notification.read = True
        notification.save()
        return Response({'status': 'Notification marked as read'}, status=status.HTTP_200_OK)
        
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get the count of unread notifications"""
        count = self.get_queryset().filter(read=False).count()
        return Response({'unread_count': count}, status=status.HTTP_200_OK)
