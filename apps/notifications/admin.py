from django.contrib import admin
from .models import Notification, FCMToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('recipient__email', 'type')


@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'device_type', 'last_used_at')
    list_filter = ('device_type',)
    search_fields = ('user__email', 'token')
