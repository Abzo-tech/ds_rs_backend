from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'

    def ready(self):
        import os
        from django.conf import settings
        import json
        try:
            import firebase_admin
            if settings.FIREBASE_ENABLED and not firebase_admin._apps:
                if settings.FIREBASE_CREDENTIALS_JSON:
                    cred = firebase_admin.credentials.Certificate(json.loads(settings.FIREBASE_CREDENTIALS_JSON))
                else:
                    cred = firebase_admin.credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
        except Exception:
            pass
