from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'

    def ready(self):
        import os
        from django.conf import settings
        try:
            import firebase_admin
            if settings.FIREBASE_ENABLED and not firebase_admin._apps:
                cred = firebase_admin.credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
        except Exception:
            pass
