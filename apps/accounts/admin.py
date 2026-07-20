from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import PartnerDailyAnalytics, AuthProvider, Profile, Follow, Block

User = get_user_model()


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'phone_number', 'role', 'is_active', 'is_certified', 'created_at')
    search_fields = ('email', 'phone_number', 'first_name', 'last_name')
    list_filter = ('role', 'is_active', 'is_certified', 'created_at')
    ordering = ('-created_at',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'display_name', 'username', 'is_certified', 'followers_count')
    search_fields = ('username', 'display_name', 'user__email')
    list_filter = ('is_certified',)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'followee', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('follower__email', 'followee__email')


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('blocker__email', 'blocked__email')


@admin.register(PartnerDailyAnalytics)
class PartnerDailyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('partner', 'date', 'views_count', 'interactions_count')
    list_filter = ('date',)
    search_fields = ('partner__email',)


@admin.register(AuthProvider)
class AuthProviderAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'provider_user_id', 'created_at')
    list_filter = ('provider',)
    search_fields = ('user__email', 'provider_user_id')
