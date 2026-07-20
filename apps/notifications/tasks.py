from celery import shared_task
from django.contrib.auth import get_user_model
from .models import Notification, FCMToken

User = get_user_model()


@shared_task
def send_push_notification(notification_id):
    try:
        notification = Notification.objects.get(id=notification_id)
        tokens = FCMToken.objects.filter(user=notification.recipient).values_list('token', flat=True)

        if not tokens:
            return f"No FCM tokens for user {notification.recipient.email}"

        from firebase_admin import messaging
        message = messaging.MulticastMessage(
            tokens=list(tokens),
            notification=messaging.Notification(
                title=notification.get_type_display(),
                body=str(notification.payload),
            ),
        )
        response = messaging.send_multicast(message)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return f"Sent to {response.success_count} devices"
    except Notification.DoesNotExist:
        return f"Notification {notification_id} not found"
    except Exception as e:
        return f"Error sending notification: {str(e)}"


@shared_task
def send_fcm_to_user(user_id, title, body, data=None):
    try:
        user = User.objects.get(id=user_id)
        tokens = FCMToken.objects.filter(user=user).values_list('token', flat=True)
        if not tokens:
            return f"No FCM tokens for user {user.email}"

        from firebase_admin import messaging
        message = messaging.MulticastMessage(
            tokens=list(tokens),
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
        )
        response = messaging.send_multicast(message)
        return f"Sent to {response.success_count} devices"
    except User.DoesNotExist:
        return f"User {user_id} not found"
    except Exception as e:
        return f"Error sending FCM: {str(e)}"
