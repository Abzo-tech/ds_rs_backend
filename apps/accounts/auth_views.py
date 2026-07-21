from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.views import TokenVerifyView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
import jwt
from django.conf import settings
from apps.accounts.models import CustomUser


@extend_schema(
    tags=['Authentification'],
    request=OpenApiTypes.OBJECT,
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    },
    description="""
    Vérifie un token JWT et retourne les informations de l'utilisateur.
    Utilisé par les autres plateformes (réservation, Maadi) pour valider
    un token émis par Discover Senegal, et vice-versa.
    
    Envoie le header: Authorization: Bearer <access_token>
    """
)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_token(request):
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return Response({
            'valid': False,
            'detail': 'Token manquant. Format: Authorization: Bearer <token>'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    token = auth_header.split(' ')[1]
    
    try:
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        
        user = CustomUser.objects.filter(id=decoded.get('user_id')).first()
        if not user:
            return Response({
                'valid': False,
                'detail': 'Utilisateur non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'valid': True,
            'user_id': str(user.id),
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'username': user.username,
        }, status=status.HTTP_200_OK)
        
    except jwt.ExpiredSignatureError:
        return Response({
            'valid': False,
            'detail': 'Token expiré'
        }, status=status.HTTP_401_UNAUTHORIZED)
    except jwt.InvalidTokenError:
        return Response({
            'valid': False,
            'detail': 'Token invalide'
        }, status=status.HTTP_401_UNAUTHORIZED)
