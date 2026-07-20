from rest_framework import serializers
from .models import Message, Conversation, ConversationParticipant
from apps.accounts.serializers import UserSerializer


class ConversationParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ConversationParticipant
        fields = ['user', 'last_read_at', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    participants = ConversationParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'created_at', 'updated_at']


class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    recipient_email = serializers.EmailField(source='recipient.email', read_only=True)
    is_me = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'sender_email', 'recipient',
            'recipient_email', 'content', 'timestamp', 'is_read', 'is_me', 'conversation'
        ]
        read_only_fields = ['id', 'sender', 'timestamp', 'is_read', 'conversation']

    def get_is_me(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender == request.user
        return False
