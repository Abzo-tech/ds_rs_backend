from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import F, Q as models_Q
from django.core.cache import cache
import random
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

from .serializers import (
    RegisterSerializer,
    UserSerializer,
    UserProfileSerializer,
    PartnerDailyAnalyticsSerializer,
    PostAnalyticsDailySerializer,
    OAuthLoginSerializer,
    PhoneLoginSerializer,
    PhoneRegisterSerializer,
    ProfileSerializer,
    FollowSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    CertifiedBadgeSerializer,
    BlockSerializer,
    ConsentToggleSerializer,
    AdminBroadcastSerializer,
    AdminUserUpdateSerializer,
)
from apps.ar_filters.serializers import ARFilterSerializer
from .models import PartnerDailyAnalytics, AuthProvider, Profile, Follow, PostAnalyticsDaily, Block
from apps.ar_filters.models import ARFilter
from apps.notifications.models import Notification

User = get_user_model()


@extend_schema(tags=['Authentification'], request=RegisterSerializer)
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Inscription réussie",
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Authentification'], request=OAuthLoginSerializer)
class OAuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, provider):
        if provider not in ['google', 'apple']:
            return Response(
                {"detail": "Fournisseur OAuth non supporté."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = OAuthLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_token = serializer.validated_data['access_token']
        id_token = serializer.validated_data.get('id_token', '')

        try:
            if provider == 'google':
                try:
                    from google.oauth2 import id_token as google_id_token
                    from google.auth.transport import requests as google_requests
                except ImportError:
                    return Response({"detail": "Google OAuth non configuré sur le serveur."}, status=status.HTTP_501_NOT_IMPLEMENTED)

                google_request = google_requests.Request()
                idinfo = google_id_token.verify_oauth2_token(
                    id_token or access_token,
                    google_request(),
                    audience=None
                )
                email = idinfo.get('email')
                provider_user_id = idinfo.get('sub')
                first_name = idinfo.get('given_name', '')
                last_name = idinfo.get('family_name', '')
            elif provider == 'apple':
                try:
                    import jwt
                    from jwt import PyJWKClient
                except ImportError:
                    return Response({"detail": "Apple OAuth non configuré sur le serveur."}, status=status.HTTP_501_NOT_IMPLEMENTED)

                jwks_url = 'https://appleid.apple.com/auth/keys'
                jwk_client = PyJWKClient(jwks_url)
                signing_key = jwk_client.get_signing_key_from_jwt(id_token or access_token)
                decoded = jwt.decode(
                    id_token or access_token,
                    signing_key.key,
                    algorithms=['RS256'],
                    audience=None,
                    issuer='https://appleid.apple.com'
                )
                email = decoded.get('email')
                provider_user_id = decoded.get('sub')
                first_name = decoded.get('name', {}).get('first_name', '')
                last_name = decoded.get('name', {}).get('last_name', '')

            if not email:
                return Response(
                    {"detail": "Email non fourni par le fournisseur OAuth."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            auth_provider, created = AuthProvider.objects.get_or_create(
                provider=provider,
                provider_user_id=provider_user_id,
                defaults={'user': None}
            )

            if auth_provider.user_id:
                user = auth_provider.user
            else:
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'username': email,
                        'role': 'public',
                        'is_active': True,
                    }
                )
                auth_provider.user = user
                auth_provider.save()

            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Connexion OAuth réussie",
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Erreur lors de la vérification OAuth: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(tags=['Authentification'], request=PhoneLoginSerializer)
class PhoneLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        otp_code = serializer.validated_data['otp_code']

        try:
            user = User.objects.get(phone_number=phone_number, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"detail": "Numéro de téléphone non enregistré ou compte inactif."},
                status=status.HTTP_404_NOT_FOUND
            )

        from django.core.cache import cache
        cached_otp = cache.get(f"otp:{phone_number}")
        if not cached_otp or cached_otp != otp_code:
            return Response(
                {"detail": "Code OTP invalide ou expiré."},
                status=status.HTTP_400_BAD_REQUEST
            )

        cache.delete(f"otp:{phone_number}")
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Connexion par téléphone réussie",
            "user": UserSerializer(user).data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)


@extend_schema(tags=['Authentification'], request=PhoneRegisterSerializer)
class PhoneRegisterRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response({"detail": "phone_number est requis."}, status=status.HTTP_400_BAD_REQUEST)

        from django.core.cache import cache
        otp = str(random.randint(1000, 9999))
        cache.set(f"otp:{phone_number}", otp, timeout=600)

        return Response({"detail": "Code OTP envoyé (mock).", "otp": otp}, status=status.HTTP_200_OK)


@extend_schema(tags=['Authentification'], request=PhoneRegisterSerializer)
class PhoneRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PhoneRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        otp_code = serializer.validated_data['otp_code']
        password = serializer.validated_data['password']

        from django.core.cache import cache
        cached_otp = cache.get(f"otp:{phone_number}")
        if not cached_otp or cached_otp != otp_code:
            return Response(
                {"detail": "Code OTP invalide ou expiré."},
                status=status.HTTP_400_BAD_REQUEST
            )

        cache.delete(f"otp:{phone_number}")

        if User.objects.filter(phone_number=phone_number).exists():
            return Response(
                {"detail": "Ce numéro de téléphone est déjà enregistré."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            email=f"{phone_number}@phone.local",
            password=password,
            phone_number=phone_number,
            first_name=serializer.validated_data.get('first_name', ''),
            last_name=serializer.validated_data.get('last_name', ''),
            preferred_language=serializer.validated_data.get('preferred_language', 'fr'),
            role='public',
            is_active=True,
        )

        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Inscription par téléphone réussie",
            "user": UserSerializer(user).data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Utilisateurs'], request=UserProfileSerializer)
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(tags=['Partenaires'], request=None)
class PartnerAnalyticsListView(generics.ListAPIView):
    serializer_class = PartnerDailyAnalyticsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'partner':
            raise PermissionDenied("Accès restreint. Ce profil n'est pas un compte partenaire certifié.")
        return PartnerDailyAnalytics.objects.filter(partner=self.request.user)


@extend_schema(tags=['Partenaires'], request=None)
class PostAnalyticsDailyListView(generics.ListAPIView):
    serializer_class = PostAnalyticsDailySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'partner':
            raise PermissionDenied("Accès restreint. Ce profil n'est pas un compte partenaire certifié.")
        return PostAnalyticsDaily.objects.filter(post__user=self.request.user).order_by('-day')


@extend_schema(tags=['Utilisateurs'], request=ProfileSerializer)
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile


@extend_schema(tags=['Utilisateurs'], request=FollowSerializer)
class FollowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        if target_user == request.user:
            return Response({"detail": "Vous ne pouvez pas vous suivre vous-même."}, status=status.HTTP_400_BAD_REQUEST)

        follow, created = Follow.objects.get_or_create(follower=request.user, followee=target_user)
        if not created:
            return Response({"detail": "Vous suivez déjà cet utilisateur."}, status=status.HTTP_400_BAD_REQUEST)

        target_user.followers_count = F('followers_count') + 1
        request.user.following_count = F('following_count') + 1
        target_user.save(update_fields=['followers_count'])
        request.user.save(update_fields=['following_count'])

        from .tasks import send_notification
        send_notification.delay(str(target_user.id), 'new_follower', {'actor_id': str(request.user.id)})

        return Response(FollowSerializer(follow).data, status=status.HTTP_201_CREATED)

    def delete(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        follow = Follow.objects.filter(follower=request.user, followee=target_user).first()
        if not follow:
            return Response({"detail": "Vous ne suivez pas cet utilisateur."}, status=status.HTTP_400_BAD_REQUEST)

        follow.delete()
        target_user.followers_count = F('followers_count') - 1
        request.user.following_count = F('following_count') - 1
        target_user.save(update_fields=['followers_count'])
        request.user.save(update_fields=['following_count'])

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Utilisateurs'], request=CertifiedBadgeSerializer)
class CertifiedBadgeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        user = request.user
        if user.role not in ['admin']:
            return Response({"detail": "Accès restreint."}, status=status.HTTP_403_FORBIDDEN)

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        target_user.is_certified = True
        target_user.save(update_fields=['is_certified'])
        return Response({"detail": "Badge certifié attribué.", "is_certified": target_user.is_certified}, status=status.HTTP_200_OK)

    def delete(self, request, user_id):
        user = request.user
        if user.role not in ['admin']:
            return Response({"detail": "Accès restreint."}, status=status.HTTP_403_FORBIDDEN)

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        target_user.is_certified = False
        target_user.save(update_fields=['is_certified'])
        return Response({"detail": "Badge certifié retiré.", "is_certified": target_user.is_certified}, status=status.HTTP_200_OK)


@extend_schema(tags=['Authentification'], request=LogoutSerializer)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        all_devices = request.data.get('all_devices', False)

        if all_devices:
            OutstandingToken.objects.filter(user=request.user).update(revoked=True)
            return Response({"detail": "Déconnexion de tous les appareils réussie."}, status=status.HTTP_200_OK)

        if not refresh_token:
            return Response({"detail": "Le refresh token est requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Déconnexion réussie."}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({"detail": "Refresh token invalide ou expiré."}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Authentification'], request=PasswordChangeSerializer)
class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        if not old_password or not new_password:
            return Response({"detail": "old_password et new_password sont requis."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(old_password):
            return Response({"detail": "Ancien mot de passe incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Mot de passe modifié avec succès."}, status=status.HTTP_200_OK)


@extend_schema(tags=['Authentification'], request=PasswordResetRequestSerializer)
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"detail": "email est requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "Aucun compte avec cet email."}, status=status.HTTP_404_NOT_FOUND)

        from django.core.cache import cache
        otp = str(random.randint(1000, 9999))
        cache.set(f"password_reset:{user.id}", otp, timeout=600)

        return Response({"detail": "Code OTP envoyé (mock).", "otp": otp}, status=status.HTTP_200_OK)


@extend_schema(tags=['Authentification'], request=PasswordResetConfirmSerializer)
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')
        if not all([user_id, otp, new_password]):
            return Response({"detail": "user_id, otp et new_password sont requis."}, status=status.HTTP_400_BAD_REQUEST)

        from django.core.cache import cache
        cached_otp = cache.get(f"password_reset:{user_id}")
        if not cached_otp or cached_otp != otp:
            return Response({"detail": "Code OTP invalide ou expiré."}, status=status.HTTP_400_BAD_REQUEST)

        cache.delete(f"password_reset:{user_id}")
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Mot de passe réinitialisé."}, status=status.HTTP_200_OK)


@extend_schema(tags=['Utilisateurs'], request=ProfileSerializer)
class UserSearchView(generics.ListAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if not query:
            return Profile.objects.none()
        return Profile.objects.filter(
            models.Q(username__icontains=query) |
            models.Q(display_name__icontains=query) |
            models.Q(user__email__icontains=query)
        ).select_related('user')


@extend_schema(tags=['Utilisateurs'], request=ConsentToggleSerializer)
class ConsentToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        consent = request.data.get('consent_ai_training')
        if not isinstance(consent, bool):
            return Response(
                {"detail": "consent_ai_training (bool) est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )
        user = request.user
        user.consent_ai_training = consent
        user.save(update_fields=['consent_ai_training'])
        return Response(
            {"detail": "Consentement mis à jour.", "consent_ai_training": user.consent_ai_training},
            status=status.HTTP_200_OK
        )

    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if not query:
            return Profile.objects.none()
        return Profile.objects.filter(
            models.Q(username__icontains=query) |
            models.Q(display_name__icontains=query) |
            models.Q(user__email__icontains=query)
        ).select_related('user')


@extend_schema(tags=['Utilisateurs'], request=BlockSerializer)
class BlockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        target = User.objects.filter(id=user_id).first()
        if not target:
            return Response({"detail": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        if target == request.user:
            return Response({"detail": "Vous ne pouvez pas vous bloquer vous-même."}, status=status.HTTP_400_BAD_REQUEST)

        Block.objects.get_or_create(blocker=request.user, blocked=target)
        return Response({"detail": "Utilisateur bloqué."}, status=status.HTTP_200_OK)

    def delete(self, request, user_id):
        target = User.objects.filter(id=user_id).first()
        if not target:
            return Response({"detail": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        block = Block.objects.filter(blocker=request.user, blocked=target).first()
        if not block:
            return Response({"detail": "Utilisateur non bloqué."}, status=status.HTTP_400_BAD_REQUEST)
        block.delete()
        return Response({"detail": "Blocage retiré."}, status=status.HTTP_200_OK)


@extend_schema(tags=['Admin'], request=None)
class AdminUserListView(generics.ListAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role not in ['admin']:
            raise PermissionDenied("Accès restreint.")
        return User.objects.all().order_by('-created_at')


@extend_schema(tags=['Admin'], request=AdminUserUpdateSerializer)
class AdminUserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id):
        user = request.user
        if user.role != 'admin':
            return Response({"detail": "Accès restreint aux admins."}, status=status.HTTP_403_FORBIDDEN)
        target = User.objects.filter(id=user_id).first()
        if not target:
            return Response({"detail": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        target.delete()
        return Response({"detail": "Utilisateur supprimé."}, status=status.HTTP_200_OK)

    def patch(self, request, user_id):
        user = request.user
        if user.role not in ['admin']:
            return Response({"detail": "Accès restreint."}, status=status.HTTP_403_FORBIDDEN)
        target = User.objects.filter(id=user_id).first()
        if not target:
            return Response({"detail": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        is_active = request.data.get('is_active')
        if is_active is not None:
            target.is_active = is_active
            target.save(update_fields=['is_active'])
        role = request.data.get('role')
        if role:
            target.role = role
            target.save(update_fields=['role'])
        return Response({"detail": "Utilisateur mis à jour."}, status=status.HTTP_200_OK)


@extend_schema(tags=['Admin'], request=ARFilterSerializer)
class AdminARFilterListView(generics.ListCreateAPIView):
    serializer_class = ARFilterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role not in ['admin']:
            raise PermissionDenied("Accès restreint.")
        return ARFilter.objects.all().order_by('-created_at')


@extend_schema(tags=['Admin'], request=ARFilterSerializer)
class AdminARFilterDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ARFilterSerializer
    permission_classes = [IsAuthenticated]
    queryset = ARFilter.objects.all()

    def check_object_permissions(self, request, obj):
        if request.user.role not in ['admin']:
            raise PermissionDenied("Accès restreint.")
        super().check_object_permissions(request, obj)


@extend_schema(tags=['Admin'], request=AdminBroadcastSerializer)
class AdminBroadcastView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role not in ['admin']:
            return Response({"detail": "Accès restreint."}, status=status.HTTP_403_FORBIDDEN)

        from .tasks import send_notification
        recipient_ids = request.data.get('recipient_ids', [])
        notification_type = request.data.get('type', 'joj_event')
        payload = request.data.get('payload', {})

        if not recipient_ids:
            return Response({"detail": "recipient_ids requis."}, status=status.HTTP_400_BAD_REQUEST)

        created = []
        for uid in recipient_ids:
            try:
                User.objects.get(id=uid)
            except User.DoesNotExist:
                continue
            notification_id = send_notification.delay(uid, notification_type, payload)
            created.append(str(notification_id))

        return Response({"detail": f"{len(created)} notifications créées.", "tasks": created}, status=status.HTTP_200_OK)
