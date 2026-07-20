import uuid
from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class Notification(models.Model):
    TYPE_CHOICES = [
        ('new_follower', 'Nouveau follower'),
        ('like', 'Like'),
        ('comment', 'Commentaire'),
        ('message', 'Message'),
        ('filter_unlocked', 'Filtre débloqué'),
        ('joj_event', 'Événement JOD'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    payload = models.JSONField(default=dict)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['type']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_display()} -> {self.recipient.email}"


class FCMToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_tokens')
    token = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=16, choices=[('ios', 'iOS'), ('android', 'Android')], default='android')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'token'])]

    def __str__(self):
        return f"FCM {self.device_type} - {self.user.email}"
