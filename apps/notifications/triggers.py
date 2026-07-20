"""Déclencheurs de notifications métier.

Centralise la création des Notification (via la tâche Celery accounts.tasks.send_notification)
pour éviter la dispersion des appels dans les vues et le consumer WebSocket.
"""
from apps.accounts.tasks import send_notification


def notify(event_type, *, actor=None, recipient=None, payload=None, recipients=None):
    """Envoie une (ou plusieurs) notification(s) asynchrone(s).

    event_type: 'new_follower' | 'like' | 'comment' | 'message' | 'filter_unlocked' | 'joj_event'
    recipient / recipients: User cible (on ignore l'auteur pour éviter l'auto-notification).
    """
    payload = payload or {}
    if actor is not None:
        payload.setdefault('actor_id', str(actor.id))

    targets = []
    if recipient is not None:
        targets.append(recipient)
    if recipients:
        targets.extend(recipients)

    for user in targets:
        if actor is not None and user.id == actor.id:
            continue
        send_notification.delay(str(user.id), event_type, payload)
