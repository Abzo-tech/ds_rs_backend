from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, FCMTokenView

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('fcm-token/', FCMTokenView.as_view(), name='fcm-token'),
] + router.urls
