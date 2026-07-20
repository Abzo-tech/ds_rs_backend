from django.contrib import admin
from .models import Post, Report, Like, Comment, Story, MediaAsset, SavedPost, Share


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'type', 'has_watermark', 'created_at')
    list_filter = ('type', 'has_watermark', 'created_at')
    search_fields = ('owner__email', 'storage_url')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'moderation_score', 'is_sponsored', 'created_at')
    list_filter = ('status', 'is_sponsored', 'created_at')
    search_fields = ('user__email', 'caption')
    ordering = ('-created_at',)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'reason', 'created_at')
    list_filter = ('reason', 'created_at')
    search_fields = ('user__email', 'post__id')


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'post__id')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'content')


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'expires_at', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email',)


@admin.register(SavedPost)
class SavedPostAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'saved_at')
    search_fields = ('user__email', 'post__id')


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'shared_at')
    search_fields = ('user__email', 'post__id')
