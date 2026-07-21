import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

User = settings.AUTH_USER_MODEL

class AuthProvider(models.Model):
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('apple', 'Apple'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auth_providers')
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['provider', 'provider_user_id']
        indexes = [models.Index(fields=['provider', 'provider_user_id'])]

    def __str__(self):
        return f"{self.provider} - {self.user.email}"


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire")
        email = self.normalize_email(email)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', True)
        if 'username' not in extra_fields:
            extra_fields['username'] = email
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('public', 'Public'),
        ('tourist', 'Touriste'),
        ('partner', 'Partenaire / Établissement'),
        ('creator', 'Créateur'),
        ('admin', 'Administrateur'),
    ]

    LANGUAGE_CHOICES = [
        ('fr', 'Français'),
        ('en', 'English'),
        ('wo', 'Wolof'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=32, unique=True, blank=True, null=True)
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='public')
    preferred_language = models.CharField(max_length=3, choices=LANGUAGE_CHOICES, default='fr')
    is_active = models.BooleanField(default=True)
    is_certified = models.BooleanField(default=False)
    
    bio = models.TextField(blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    external_link = models.URLField(blank=True, null=True)
    username = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)
    posts_count = models.PositiveIntegerField(default=0)
    
    consent_ai_training = models.BooleanField(default=False)
    partner_establishment_id = models.UUIDField(blank=True, null=True)
    partner_link = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.email
    

class PartnerDailyAnalytics(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'partner'}, related_name='daily_analytics')
    date = models.DateField(auto_now_add=True)
    views_count = models.PositiveIntegerField(default=0)
    interactions_count = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = 'accounts'
        unique_together = ['partner', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"Analytics for {self.partner.email} on {self.date}"


class PostAnalyticsDaily(models.Model):
    post = models.ForeignKey('feed.Post', on_delete=models.CASCADE, related_name='daily_analytics')
    day = models.DateField()
    views = models.PositiveIntegerField(default=0)
    reach = models.PositiveIntegerField(default=0)
    engagement = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = 'accounts'
        unique_together = ['post', 'day']
        ordering = ['-day']

    def __str__(self):
        return f"Analytics for Post {self.post.id} on {self.day}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=100)
    username = models.CharField(max_length=50, unique=True)
    avatar_media = models.ForeignKey('feed.MediaAsset', on_delete=models.SET_NULL, blank=True, null=True, related_name='avatars')
    location_label = models.CharField(max_length=150, blank=True)
    is_certified = models.BooleanField(default=False)
    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)
    posts_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['username']), models.Index(fields=['user'])]

    def __str__(self):
        return f"Profile of {self.user.email}"


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_set')
    followee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers_set')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['follower', 'followee']
        indexes = [models.Index(fields=['followee', '-created_at'])]

    def __str__(self):
        return f"{self.follower.email} follows {self.followee.email}"


class Block(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocking_set')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_set')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['blocker', 'blocked']
        indexes = [models.Index(fields=['blocker', 'blocked'])]

    def __str__(self):
        return f"{self.blocker.email} blocks {self.blocked.email}"