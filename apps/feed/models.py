import uuid
from django.contrib.gis.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class MediaAsset(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('photo', 'Photo'),
        ('video', 'Vidéo'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='media_assets')
    type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    storage_url = models.URLField(max_length=500)
    watermarked_url = models.URLField(max_length=500, blank=True, null=True)
    thumbnail_url = models.URLField(max_length=500, blank=True, null=True)
    duration_seconds = models.PositiveSmallIntegerField(blank=True, null=True)
    ar_filter = models.ForeignKey('ar_filters.ARFilter', on_delete=models.SET_NULL, blank=True, null=True, related_name='media_assets')
    has_watermark = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return f"{self.type} - {self.owner.email} - {self.id}"


class Post(models.Model):
    STATUS_CHOICES = [
        ('published', 'Publié'),
        ('pending_review', 'En attente de modération'),
        ('removed', 'Supprimé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    media = models.ForeignKey(MediaAsset, on_delete=models.CASCADE, related_name='posts')
    caption = models.TextField(blank=True, max_length=500)
    ar_filter = models.ForeignKey('ar_filters.ARFilter', on_delete=models.SET_NULL, blank=True, null=True, related_name='posts')
    repost_of = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='reposts')

    location = models.PointField(srid=4326, geography=True, null=True, blank=True)
    location_name = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='published',
    )
    moderation_score = models.FloatField(blank=True, null=True)
    is_sponsored = models.BooleanField(default=False)

    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"Post {self.id} by {self.user.email} - {self.status}"


class Report(models.Model):
    STATUS_CHOICES = [
        ('open', 'Ouvert'),
        ('reviewed', 'Examiné'),
        ('dismissed', 'Rejeté'),
    ]

    REASON_CHOICES = [
        ('INAPPROPRIATE', 'Contenu inapproprié / Nudité'),
        ('SPAM', 'Spam / Publicité indésirable'),
        ('HARASSMENT', 'Harcèlement / Discours de haine'),
        ('VIOLENCE', 'Violence / Contenu dangereux'),
        ('OTHER', 'Autre raison'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submitted_reports'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports'
    )
    comment = models.ForeignKey(
        'Comment',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports'
    )
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        default='OTHER',
    )
    description = models.TextField(blank=True, max_length=500)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(post__isnull=False) | models.Q(comment__isnull=False),
                name='report_target_not_null',
            )
        ]

    def __str__(self):
        target = self.post.id if self.post else self.comment.id
        kind = 'Post' if self.post else 'Comment'
        return f"Signalement de {self.user.email} sur le {kind} {target} ({self.reason})"


class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes_set')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'user']

    def __str__(self):
        return f"{self.user.email} likes {self.post.id}"


class Comment(models.Model):
    STATUS_CHOICES = [
        ('published', 'Publié'),
        ('pending_review', 'En attente de modération'),
        ('removed', 'Supprimé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments_set')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(max_length=300)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['post', '-created_at'])]

    def __str__(self):
        return f"Comment by {self.user.email} on Post {self.post.id}"


class Story(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stories'
    )
    media = models.ForeignKey(MediaAsset, on_delete=models.CASCADE, related_name='stories')
    caption = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.id or not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Story {self.id} by {self.user.email}"


class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='views')
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='story_views')
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['story', 'viewer']
        indexes = [models.Index(fields=['story', '-viewed_at'])]

    def __str__(self):
        return f"{self.viewer.email} viewed Story {self.story.id}"


class SavedPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_posts')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'post']
        indexes = [models.Index(fields=['user', '-saved_at'])]

    def __str__(self):
        return f"{self.user.email} saved {self.post.id}"


class Share(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shares')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='shares')
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['post', '-shared_at'])]

    def __str__(self):
        return f"{self.user.email} shared {self.post.id}"
