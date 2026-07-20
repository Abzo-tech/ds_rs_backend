import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message, Conversation, ConversationParticipant

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if self.user.is_anonymous:
            await self.close()
            return

        conversation_id = self.scope["url_route"]["kwargs"].get("conversation_id")
        if not conversation_id:
            await self.close()
            return

        self.conversation_id = conversation_id
        self.room_group_name = f"chat_{conversation_id}"

        is_participant = await self.check_participant(self.user.id, conversation_id)
        if not is_participant:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get('content')

        if not content:
            return

        message_obj = await self.save_message(self.user, self.conversation_id, content)
        if message_obj:
            from apps.notifications.triggers import notify
            await database_sync_to_async(notify)(
                'message',
                actor=self.user,
                recipient=message_obj.recipient,
                payload={'conversation_id': str(self.conversation_id), 'message_id': str(message_obj.id)},
            )
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": content,
                    "sender_id": str(message_obj.sender.id),
                    "timestamp": message_obj.timestamp.isoformat(),
                    "message_id": str(message_obj.id),
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender_id": event["sender_id"],
            "timestamp": event["timestamp"],
            "message_id": event["message_id"],
        }))

    @database_sync_to_async
    def check_participant(self, user_id, conversation_id):
        return ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            user_id=user_id
        ).exists()

    @database_sync_to_async
    def save_message(self, sender, conversation_id, content):
        try:
            if sender.is_anonymous:
                return None
            conversation = Conversation.objects.get(id=conversation_id)
            other_participant = conversation.participants.exclude(user=sender).first()
            if not other_participant:
                return None
            return Message.objects.create(
                conversation=conversation,
                sender=sender,
                recipient=other_participant.user,
                content=content
            )
        except (Conversation.DoesNotExist, ConversationParticipant.DoesNotExist):
            return None
