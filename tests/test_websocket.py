import os
import sys
import django
import json
from asgiref.sync import async_to_sync, sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps'))
django.setup()

from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TransactionTestCase
from apps.chat.models import Conversation, ConversationParticipant
from apps.chat.routing import websocket_urlpatterns
from channels.routing import URLRouter
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class ChatWebSocketTestCase(TransactionTestCase):
    def _make_user(self, email):
        return User.objects.create_user(
            email=email,
            password='wspass123',
            first_name='Ws',
            last_name='One',
            role='public',
        )

    async def _make_conversation(self, u1, u2):
        from apps.chat.models import Conversation, ConversationParticipant
        conversation = await Conversation.objects.acreate()
        await ConversationParticipant.objects.acreate(conversation=conversation, user=u1)
        await ConversationParticipant.objects.acreate(conversation=conversation, user=u2)
        return conversation

    def setUp(self):
        self.user1 = self._make_user('ws1@example.com')
        self.user2 = self._make_user('ws2@example.com')
        self.conversation = async_to_sync(self._make_conversation)(self.user1, self.user2)

    async def test_websocket_chat(self):
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            f'/ws/chat/{self.conversation.id}/'
        )
        communicator.scope['user'] = self.user1
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_to(text_data=json.dumps({'content': 'Hello WebSocket'}))
        response = await communicator.receive_from()
        self.assertIn('Hello WebSocket', response)

        await communicator.disconnect()

    async def test_websocket_anonymous_rejected(self):
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            f'/ws/chat/{self.conversation.id}/'
        )
        communicator.scope['user'] = AnonymousUser()
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_websocket_non_participant_rejected(self):
        outsider = await User.objects.acreate(
            email='ws-out@x.com', password='wspass123', first_name='Out', last_name='Sider', role='public'
        )
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            f'/ws/chat/{self.conversation.id}/'
        )
        communicator.scope['user'] = outsider
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_websocket_message_persisted_and_notifies(self):
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            f'/ws/chat/{self.conversation.id}/'
        )
        communicator.scope['user'] = self.user1
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_to(text_data=json.dumps({'content': 'Hello WebSocket'}))
        response = await communicator.receive_from()
        self.assertIn('Hello WebSocket', response)

        from apps.chat.models import Message
        exists = await sync_to_async(
            Message.objects.filter(conversation=self.conversation, content='Hello WebSocket').exists
        )()
        self.assertTrue(exists)

        await communicator.disconnect()