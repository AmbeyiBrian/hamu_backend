from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'type', 'read', 'timestamp', 'link']
        read_only_fields = ['id', 'timestamp']
