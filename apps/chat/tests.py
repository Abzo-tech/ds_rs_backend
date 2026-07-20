from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class ChatTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='SecurePass123!',
            role='public'
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='SecurePass123!',
            role='public'
        )
        self.client.force_authenticate(user=self.user1)

    def test_create_conversation(self):
        response = self.client.post('/api/v1/chat/conversations/create/', {
            'user_id': str(self.user2.id)
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('id', response.data)

    def test_conversation_list(self):
        response = self.client.get('/api/v1/chat/conversations/list/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_messages_in_conversation(self):
        from apps.chat.models import Conversation, ConversationParticipant, Message
        conv = Conversation.objects.create()
        ConversationParticipant.objects.create(conversation=conv, user=self.user1)
        ConversationParticipant.objects.create(conversation=conv, user=self.user2)
        Message.objects.create(conversation=conv, sender=self.user1, recipient=self.user2, content='Hello')
        response = self.client.get(f'/api/v1/chat/messages/?conversation_id={conv.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
