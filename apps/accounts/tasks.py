from celery import shared_task
from django.contrib.auth import get_user_model
from apps.notifications.models import Notification, FCMToken

User = get_user_model()


@shared_task
def send_notification(recipient_id, notification_type, payload=None):
    """Crée une Notification en base et déclenche le push FCM si possible."""
    payload = payload or {}
    try:
        recipient = User.objects.get(id=recipient_id)
    except User.DoesNotExist:
        return f"Recipient {recipient_id} not found"

    notification = Notification.objects.create(
        recipient=recipient,
        type=notification_type,
        payload=payload,
    )
    _dispatch_fcm.delay(notification.id)
    return str(notification.id)


def _dispatch_fcm(notification_id):
    from apps.notifications.tasks import send_fcm_to_user

    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return f"Notification {notification_id} not found"

    title = _notification_title(notification.type)
    body = _notification_body(notification)
    data = {k: str(v) for k, v in notification.payload.items()}
    return send_fcm_to_user(notification.recipient_id, title, body, data)


def _notification_title(notification_type):
    return {
        "new_follower": "Nouveau follower",
        "like": "Nouveau like",
        "comment": "Nouveau commentaire",
        "message": "Nouveau message",
        "filter_unlocked": "Filtre débloqué",
        "joj_event": "Événement JOJ 2026",
    }.get(notification_type, "Discover Sénégal")


def _notification_body(notification):
    payload = notification.payload or {}
    return payload.get("text") or str(payload)
