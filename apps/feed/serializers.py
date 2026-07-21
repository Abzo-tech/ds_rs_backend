from rest_framework import serializers
from drf_extra_fields.geo_fields import PointField
from .models import Post, Report, Comment, Story, MediaAsset, StoryView
from apps.accounts.serializers import UserSerializer
from apps.ar_filters.serializers import ARFilterSerializer


class MediaAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaAsset
        fields = ['id', 'type', 'storage_url', 'watermarked_url', 'thumbnail_url', 'duration_seconds', 'has_watermark', 'created_at']
        read_only_fields = ['id', 'created_at']


class PostSerializer(serializers.ModelSerializer):
    location = PointField(required=False, allow_null=True)
    user = UserSerializer(read_only=True)
    media = MediaAssetSerializer(read_only=True)
    ar_filter = ARFilterSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_repost = serializers.SerializerMethodField()
    original_post = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'user', 'media', 'caption', 'ar_filter',
            'location', 'location_name', 'status', 'moderation_score',
            'is_sponsored', 'likes_count', 'comments_count', 'shares_count',
            'created_at', 'is_liked', 'is_repost', 'original_post'
        ]
        read_only_fields = [
            'id', 'user', 'media', 'likes_count', 'comments_count',
            'shares_count', 'created_at', 'is_liked', 'status', 'moderation_score',
            'is_repost', 'original_post'
        ]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes_set.filter(user=request.user).exists()
        return False

    def get_is_repost(self, obj):
        return obj.repost_of is not None

    def get_original_post(self, obj):
        if obj.repost_of:
            return PostSerializer(obj.repost_of, context=self.context).data
        return None

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)


class PostCreateSerializer(serializers.ModelSerializer):
    location = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Post
        fields = ['media', 'caption', 'ar_filter', 'location', 'location_name']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)


class ReportSerializer(serializers.ModelSerializer):
    comment = serializers.PrimaryKeyRelatedField(
        queryset=Comment.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Report
        fields = ['id', 'reason', 'description', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        view = self.context['view']
        user = self.context['request'].user
        post_id = view.kwargs.get('post_id')
        comment = attrs.get('comment')

        if post_id and not comment:
            try:
                post = Post.objects.get(id=post_id)
            except Post.DoesNotExist:
                raise serializers.ValidationError({"post": "Ce post n'existe pas."})
            if Report.objects.filter(user=user, post=post).exists():
                raise serializers.ValidationError({"detail": "Vous avez déjà signalé cette publication."})
        elif comment and not post_id:
            if Report.objects.filter(user=user, comment=comment).exists():
                raise serializers.ValidationError({"detail": "Vous avez déjà signalé ce commentaire."})
        return attrs


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class StorySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    media = MediaAssetSerializer(read_only=True)
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = ['id', 'user', 'media', 'caption', 'created_at', 'expires_at', 'is_active']
        read_only_fields = ['id', 'user', 'created_at', 'expires_at']

    def get_is_active(self, obj):
        from django.utils import timezone
        return obj.expires_at > timezone.now()


class StoryViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoryView
        fields = ['story', 'viewer', 'viewed_at']
        read_only_fields = ['story', 'viewer', 'viewed_at']


class MediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    type = serializers.ChoiceField(choices=['photo', 'video'])


class ModerationActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])


class MaadiRecommendSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    behavior_signals = serializers.DictField()
    location = serializers.DictField(required=False, allow_null=True)
    limit = serializers.IntegerField(default=20)
