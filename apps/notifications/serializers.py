from rest_framework import serializers
from .models import Notification, FCMToken


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'type', 'payload', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']


class FCMTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMToken
        fields = ['id', 'token', 'device_type', 'created_at', 'last_used_at']
        read_only_fields = ['id', 'created_at', 'last_used_at']
