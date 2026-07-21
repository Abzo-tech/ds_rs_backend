from django.db.models import Q, Max, Count
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from apps.accounts.models import CustomUser
from .models import Message, Conversation, ConversationParticipant
from .serializers import MessageSerializer, ConversationSerializer


@extend_schema(tags=['Chat'])class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            participants__user=user
        ).distinct().order_by('-updated_at')

    def list(self, request):
        user = request.user
        conversations = self.get_queryset().annotate(
            last_message_time=Max('messages__timestamp'),
            unread_count=Count('messages', filter=Q(messages__is_read=False, messages__recipient=user))
        ).order_by('-last_message_time')

        data = []
        for conv in conversations:
            other = conv.participants.exclude(user=user).first()
            last_message = conv.messages.order_by('-timestamp').first()
            data.append({
                "id": str(conv.id),
                "other_user": {
                    "id": str(other.user.id) if other else None,
                    "email": other.user.email if other else None,
                    "first_name": getattr(other.user, 'first_name', '') if other else '',
                    "last_name": getattr(other.user, 'last_name', '') if other else '',
                } if other else None,
                "last_message": {
                    "content": last_message.content if last_message else "",
                    "timestamp": last_message.timestamp.isoformat() if last_message else None,
                    "sender_id": str(last_message.sender.id) if last_message else None,
                } if last_message else None,
                "unread_count": conv.unread_count,
                "updated_at": conv.updated_at.isoformat(),
            })
        return Response(data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"detail": "user_id est requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            other_user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"detail": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        existing = Conversation.objects.filter(
            participants__user=request.user
        ).filter(
            participants__user=other_user
        ).distinct()

        if existing.exists():
            conv = existing.first()
        else:
            conv = Conversation.objects.create()
            ConversationParticipant.objects.create(conversation=conv, user=request.user)
            ConversationParticipant.objects.create(conversation=conv, user=other_user)

        serializer = self.get_serializer(conv)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=['Chat'])class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Message.objects.filter(
            Q(conversation__participants__user=user)
        ).distinct().select_related('sender', 'recipient', 'conversation')

        conversation_id = self.request.query_params.get('conversation_id')
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id).order_by('timestamp')
        else:
            queryset = queryset.order_by('-timestamp')

        return queryset

    def create(self, request, *args, **kwargs):
        conversation_id = request.data.get('conversation_id')
        content = request.data.get('content')
        recipient_id = request.data.get('recipient_id')

        if not conversation_id or not content:
            return Response({"detail": "conversation_id et content sont requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Conversation non trouvée."}, status=status.HTTP_404_NOT_FOUND)

        if not ConversationParticipant.objects.filter(conversation=conversation, user=request.user).exists():
            return Response({"detail": "Vous n'êtes pas participant de cette conversation."}, status=status.HTTP_403_FORBIDDEN)

        if recipient_id:
            try:
                recipient = CustomUser.objects.get(id=recipient_id)
            except CustomUser.DoesNotExist:
                return Response({"detail": "Destinataire non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        else:
            other = conversation.participants.exclude(user=request.user).first()
            if not other:
                return Response({"detail": "Aucun destinataire trouvé."}, status=status.HTTP_400_BAD_REQUEST)
            recipient = other.user

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            recipient=recipient,
            content=content
        )

        conversation.updated_at = message.timestamp
        conversation.save(update_fields=['updated_at'])

        serializer = self.get_serializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Chat'])class ConversationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Conversation non trouvée."}, status=status.HTTP_404_NOT_FOUND)

        participant = ConversationParticipant.objects.filter(conversation=conversation, user=request.user).first()
        if not participant:
            return Response({"detail": "Vous n'êtes pas participant."}, status=status.HTTP_403_FORBIDDEN)

        participant.last_read_at = timezone.now()
        participant.save(update_fields=['last_read_at'])
        return Response({"detail": "Conversation marquée comme lue."}, status=status.HTTP_200_OK)


@extend_schema(tags=['Chat'])class ConversationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Conversation non trouvée."}, status=status.HTTP_404_NOT_FOUND)

        if not ConversationParticipant.objects.filter(conversation=conversation, user=request.user).exists():
            return Response({"detail": "Vous n'êtes pas participant."}, status=status.HTTP_403_FORBIDDEN)

        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
