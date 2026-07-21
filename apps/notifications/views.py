from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import CursorPagination
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from .models import Notification, FCMToken
from .serializers import NotificationSerializer, FCMTokenSerializer


class NotificationCursorPagination(CursorPagination):
    page_size = 20
    ordering = '-created_at'
    cursor_query_param = 'cursor'


@extend_schema(tags=['Notifications'])
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = NotificationCursorPagination

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({"detail": "Notification marquée comme lue."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        updated = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"detail": f"{updated} notifications marquées comme lues."}, status=status.HTTP_200_OK)


@extend_schema(tags=['Notifications'], request=FCMTokenSerializer)
class FCMTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = FCMTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_str = serializer.validated_data['token']
        device_type = serializer.validated_data.get('device_type', 'android')

        fcm_token, created = FCMToken.objects.get_or_create(
            token=token_str,
            defaults={'user': request.user, 'device_type': device_type}
        )
        if not created:
            fcm_token.user = request.user
            fcm_token.device_type = device_type
            fcm_token.save(update_fields=['user', 'device_type', 'last_used_at'])

        return Response(FCMTokenSerializer(fcm_token).data, status=status.HTTP_200_OK)

    def delete(self, request):
        token_str = request.data.get('token')
        if not token_str:
            return Response({"detail": "token est requis."}, status=status.HTTP_400_BAD_REQUEST)
        fcm_token = FCMToken.objects.filter(token=token_str, user=request.user).first()
        if not fcm_token:
            return Response({"detail": "Token non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        fcm_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
