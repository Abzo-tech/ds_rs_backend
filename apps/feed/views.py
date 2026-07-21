from django.shortcuts import render
from django.db import transaction
from django.db.models import F
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework import generics, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import CursorPagination
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import Post, Report, Like, Comment, Story, MediaAsset, StoryView, SavedPost, Share
from .serializers import PostSerializer, PostCreateSerializer, ReportSerializer, CommentSerializer, StorySerializer, MediaAssetSerializer, StoryViewSerializer, StoryCreateSerializer, MediaUploadSerializer, ModerationActionSerializer, MaadiRecommendSerializer
from .filters import DistanceFilterBackend
from .services import get_personalized_feed
from .tasks import moderate_post_with_maadi_ai, apply_watermark, fanout_post_to_followers

User = get_user_model()


class FeedCursorPagination(CursorPagination):
    page_size = 10
    ordering = '-created_at'
    cursor_query_param = 'cursor'


@extend_schema(tags=['Feed'])
class FeedListView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FeedCursorPagination
    filter_backends = [DistanceFilterBackend]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PostCreateSerializer
        return PostSerializer

    def get_queryset(self):
        return Post.objects.filter(status='published').select_related('user', 'media', 'ar_filter').prefetch_related('likes_set', 'comments_set')

    def list(self, request, *args, **kwargs):
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')

        posts, source = get_personalized_feed(request.user.id, lat, lng)

        if hasattr(posts, 'order_by'):
            page = self.paginate_queryset(posts)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response = self.get_paginated_response(serializer.data)
                response.data['source'] = source
                return response

        serializer = self.get_serializer(posts, many=True)
        return Response({
            'results': serializer.data,
            'source': source,
        })

    def perform_create(self, serializer):
        post = serializer.save(user=self.request.user)
        moderate_post_with_maadi_ai.delay(post.id)
        fanout_post_to_followers.delay(post.id)


@extend_schema(tags=['Feed'])
class ReportCreateView(generics.CreateAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        post_id = self.kwargs.get('post_id')
        comment_id = self.kwargs.get('comment_id')
        if post_id:
            target = {'post': Post.objects.get(id=post_id)}
        elif comment_id:
            target = {'comment': Comment.objects.get(id=comment_id)}
        else:
            raise serializers.ValidationError({"detail": "post_id ou comment_id requis."})
        serializer.save(user=self.request.user, **target)


@extend_schema(tags=['Feed'])
class PostLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({"error": "Ce post n'existe pas."}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            like, created = Like.objects.get_or_create(user=request.user, post=post)
            if not created:
                return Response({"detail": "Vous avez déjà aimé cette publication."}, status=status.HTTP_400_BAD_REQUEST)
            post.likes_count = F('likes_count') + 1
            post.save(update_fields=['likes_count'])

        from apps.notifications.triggers import notify
        notify('like', actor=request.user, recipient=post.user, payload={'post_id': str(post.id)})

        return Response({"detail": "Publication aimée avec succès."}, status=status.HTTP_201_CREATED)

    def delete(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({"error": "Ce post n'existe pas."}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            like_queryset = Like.objects.filter(user=request.user, post=post)
            if not like_queryset.exists():
                return Response({"detail": "Vous n'avez pas encore aimé cette publication."}, status=status.HTTP_400_BAD_REQUEST)
            like_queryset.delete()
            post.likes_count = F('likes_count') - 1
            post.save(update_fields=['likes_count'])

        return Response({"detail": "Like retiré avec succès."}, status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Feed'])
class PostCommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FeedCursorPagination

    def get_queryset(self):
        post_id = self.kwargs.get('post_id')
        return Comment.objects.filter(post_id=post_id, status='published').select_related('user')

    def perform_create(self, serializer):
        post_id = self.kwargs.get('post_id')
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            raise serializers.ValidationError({"error": "Ce post n'existe pas."})

        with transaction.atomic():
            serializer.save(user=self.request.user, post=post)
            post.comments_count = F('comments_count') + 1
            post.save(update_fields=['comments_count'])

        from apps.notifications.triggers import notify
        notify('comment', actor=self.request.user, recipient=post.user, payload={'post_id': str(post.id)})


@extend_schema(tags=['Feed'], request=StoryCreateSerializer)
class StoryListCreateView(generics.ListCreateAPIView):
    serializer_class = StorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FeedCursorPagination

    def get_queryset(self):
        return Story.objects.filter(expires_at__gt=timezone.now()).select_related('user', 'media')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(tags=['Feed'], request=MediaUploadSerializer)
class MediaUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MediaAssetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        media = serializer.save(owner=request.user)
        apply_watermark.delay(media.id)
        return Response(MediaAssetSerializer(media).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Feed'])
class StoryViewTrackingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, story_id):
        try:
            story = Story.objects.get(id=story_id)
        except Story.DoesNotExist:
            return Response({"detail": "Story non trouvée."}, status=status.HTTP_404_NOT_FOUND)

        story_view, created = StoryView.objects.get_or_create(story=story, viewer=request.user)
        if created:
            return Response(StoryViewSerializer(story_view).data, status=status.HTTP_201_CREATED)
        return Response(StoryViewSerializer(story_view).data, status=status.HTTP_200_OK)


@extend_schema(tags=['Feed'])
class PostSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({"detail": "Post non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        SavedPost.objects.create(user=request.user, post=post)
        return Response({"detail": "Post sauvegardé."}, status=status.HTTP_201_CREATED)

    def delete(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({"detail": "Post non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        saved = SavedPost.objects.filter(user=request.user, post=post).first()
        if not saved:
            return Response({"detail": "Post non sauvegardé."}, status=status.HTTP_400_BAD_REQUEST)
        saved.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Feed'])
class PostShareView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({"detail": "Post non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        Share.objects.create(user=request.user, post=post)
        post.shares_count = F('shares_count') + 1
        post.save(update_fields=['shares_count'])
        return Response({"detail": "Partage enregistré."}, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Feed'])
class PostRepostView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try:
            original_post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({"detail": "Post original non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        if original_post.repost_of:
            return Response({"detail": "Vous ne pouvez pas reposter un repost."}, status=status.HTTP_400_BAD_REQUEST)

        repost = Post.objects.create(
            user=request.user,
            media=original_post.media,
            caption=original_post.caption,
            ar_filter=original_post.ar_filter,
            location=original_post.location,
            location_name=original_post.location_name,
            repost_of=original_post
        )
        serializer = PostSerializer(repost, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Feed'])
class MediaListView(generics.ListAPIView):
    serializer_class = MediaAssetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MediaAsset.objects.filter(owner=self.request.user).order_by('-created_at')


@extend_schema(tags=['Feed'])
class MediaDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, media_id):
        try:
            media = MediaAsset.objects.get(id=media_id, owner=request.user)
        except MediaAsset.DoesNotExist:
            return Response({"detail": "Média non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        media.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Modération'])
class ModerationQueueView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role != 'admin':
            raise PermissionDenied("Accès restreint aux modérateurs.")
        return Post.objects.filter(status='pending_review').select_related('user', 'media', 'ar_filter').prefetch_related('likes_set', 'comments_set')


@extend_schema(tags=['Modération'])
class CommentModerationQueueView(generics.ListAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role != 'admin':
            raise PermissionDenied("Accès restreint aux modérateurs.")
        return Comment.objects.filter(status='pending_review').select_related('user', 'post')


@extend_schema(tags=['Modération'], request=ModerationActionSerializer)
class ModerationActionView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_target(self, target_type, target_id):
        if target_type == 'post':
            return Post.objects.get(id=target_id)
        elif target_type == 'comment':
            return Comment.objects.get(id=target_id)
        raise serializers.ValidationError({"detail": "target_type invalide (post|comment)."})

    def post(self, request, target_type, target_id, action):
        user = request.user
        if user.role != 'admin':
            raise PermissionDenied("Accès restreint aux admins / modérateurs.")

        try:
            target = self._get_target(target_type, target_id)
        except (Post.DoesNotExist, Comment.DoesNotExist):
            return Response({"detail": "Cible non trouvée."}, status=status.HTTP_404_NOT_FOUND)

        valid_statuses = dict(Post.STATUS_CHOICES) if target_type == 'post' else dict(Comment.STATUS_CHOICES)
        if target.status != 'pending_review':
            return Response(
                {"detail": "Cette cible n'est pas en attente de modération."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if action == 'approve':
            target.status = 'published'
            if target_type == 'post':
                target.moderation_score = 1.0
        elif action == 'reject':
            target.status = 'removed'
        else:
            return Response(
                {"detail": "Action invalide. Utilisez 'approve' ou 'reject'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        update_fields = ['status']
        if target_type == 'post':
            update_fields.append('moderation_score')
        target.save(update_fields=update_fields)
        return Response(
            {"detail": f"{target_type.capitalize()} {action} avec succès.", "status": target.status},
            status=status.HTTP_200_OK
        )


@extend_schema(tags=['Feed'])
class DiscoverView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FeedCursorPagination

    def get_queryset(self):
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        queryset = Post.objects.filter(status='published').select_related('user', 'media', 'ar_filter').prefetch_related('likes_set', 'comments_set')

        if lat and lng:
            try:
                point = Point(float(lng), float(lat), srid=4326)
                queryset = queryset.filter(location__dwithin=(point, 50000))
            except (ValueError, TypeError):
                pass

        return queryset.order_by('-likes_count', '-created_at')


@extend_schema(tags=['Interne'], request=MaadiRecommendSerializer)
class MaadiRecommendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        payload = request.data.copy()
        payload.setdefault('user_id', str(user.id))
        posts, source = get_personalized_feed(user.id, payload.get('lat'), payload.get('lng'))
        serializer = PostSerializer(posts, many=True)
        return Response({
            'posts': serializer.data,
            'source': source,
        }, status=status.HTTP_200_OK)
