from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, ChatMessageViewSet, ConversationMarkReadView, ConversationDeleteView

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', ChatMessageViewSet, basename='chat-message')

urlpatterns = [
    path('', include(router.urls)),
    path('conversations/<uuid:conversation_id>/mark-read/', ConversationMarkReadView.as_view(), name='conversation-mark-read'),
    path('conversations/<uuid:conversation_id>/delete/', ConversationDeleteView.as_view(), name='conversation-delete'),
]
