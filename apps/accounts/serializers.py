from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import PartnerDailyAnalytics, AuthProvider, Profile, Follow, PostAnalyticsDaily

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    consent_ai_training = serializers.BooleanField(required=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'password', 'first_name', 'last_name', 'role',
            'consent_ai_training', 'partner_establishment_id', 'phone_number',
            'preferred_language', 'username'
        ]
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'role': {'default': 'public'},
            'phone_number': {'required': False},
            'preferred_language': {'default': 'fr'},
            'username': {'required': False},
        }

    def validate(self, attrs):
        if attrs.get('role') == 'partner' and not attrs.get('partner_establishment_id'):
            raise serializers.ValidationError({
                "partner_establishment_id": "L'identifiant de l'établissement est obligatoire pour un compte partenaire."
            })
        if attrs.get('role') in ['tourist', 'partner', 'creator', 'admin'] and not attrs.get('phone_number'):
            raise serializers.ValidationError({
                "phone_number": "Le numéro de téléphone est obligatoire pour ce type de compte."
            })
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role', 'consent_ai_training',
            'partner_establishment_id', 'partner_link', 'phone_number', 'preferred_language',
            'is_certified', 'username', 'followers_count', 'following_count', 'posts_count'
        ]


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role', 'bio', 'avatar_url',
            'consent_ai_training', 'partner_establishment_id', 'partner_link', 'created_at',
            'phone_number', 'preferred_language', 'is_certified', 'username',
            'external_link', 'followers_count', 'following_count', 'posts_count'
        ]
        read_only_fields = [
            'id', 'email', 'role', 'partner_establishment_id', 'partner_link', 'created_at',
            'is_certified', 'followers_count', 'following_count', 'posts_count'
        ]


class PartnerDailyAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerDailyAnalytics
        fields = ['id', 'date', 'views_count', 'interactions_count']


class PostAnalyticsDailySerializer(serializers.ModelSerializer):
    class Meta:
        model = PostAnalyticsDaily
        fields = ['post', 'day', 'views', 'reach', 'engagement']
        read_only_fields = ['post', 'day']


class AuthProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthProvider
        fields = ['id', 'provider', 'provider_user_id', 'created_at']
        read_only_fields = ['id', 'created_at']


class OAuthLoginSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['google', 'apple'])
    access_token = serializers.CharField()
    id_token = serializers.CharField(required=False, allow_blank=True)


class PhoneLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    otp_code = serializers.CharField(min_length=4, max_length=10)


class PhoneRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    otp_code = serializers.CharField(min_length=4, max_length=10)
    password = serializers.CharField(min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    preferred_language = serializers.ChoiceField(choices=[('fr', 'Français'), ('en', 'English'), ('wo', 'Wolof')], default='fr')
    username = serializers.CharField(required=False, allow_blank=True)
    consent_ai_training = serializers.BooleanField(required=True)


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = ['user', 'display_name', 'username', 'avatar_media', 'location_label', 'is_certified', 'followers_count', 'following_count', 'posts_count']
        read_only_fields = ['user', 'is_certified', 'followers_count', 'following_count', 'posts_count']


class FollowSerializer(serializers.ModelSerializer):
    follower = UserSerializer(read_only=True)
    followee = UserSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ['follower', 'followee', 'created_at']
        read_only_fields = ['follower', 'followee', 'created_at']


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    all_devices = serializers.BooleanField(default=False)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    otp = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class CertifiedBadgeSerializer(serializers.Serializer):
    pass


class BlockSerializer(serializers.Serializer):
    pass


class ConsentToggleSerializer(serializers.Serializer):
    consent_ai_training = serializers.BooleanField()


class AdminBroadcastSerializer(serializers.Serializer):
    recipient_ids = serializers.ListField(child=serializers.UUIDField())
    type = serializers.ChoiceField(choices=['new_follower', 'like', 'comment', 'message', 'filter_unlocked', 'joo_event'])
    payload = serializers.DictField()
