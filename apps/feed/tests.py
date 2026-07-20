from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class FeedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='SecurePass123!',
            role='public'
        )
        self.client.force_authenticate(user=self.user)

    def test_feed_list_returns_posts(self):
        response = self.client.get('/api/v1/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_feed_cursor_pagination(self):
        response = self.client.get('/api/v1/feed/')
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)

    def test_create_post_requires_media(self):
        response = self.client.post('/api/v1/feed/', {
            'caption': 'Test post'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_like_post(self):
        from apps.feed.models import Post, MediaAsset
        media = MediaAsset.objects.create(owner=self.user, type='photo', storage_url='https://example.com/img.jpg')
        post = Post.objects.create(user=self.user, media=media, caption='Test')
        response = self.client.post(f'/api/v1/feed/posts/{post.id}/like/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unlike_post(self):
        from apps.feed.models import Post, MediaAsset, Like
        media = MediaAsset.objects.create(owner=self.user, type='photo', storage_url='https://example.com/img.jpg')
        post = Post.objects.create(user=self.user, media=media, caption='Test')
        Like.objects.create(user=self.user, post=post)
        response = self.client.delete(f'/api/v1/feed/posts/{post.id}/like/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_report_post(self):
        from apps.feed.models import Post, MediaAsset
        media = MediaAsset.objects.create(owner=self.user, type='photo', storage_url='https://example.com/img.jpg')
        post = Post.objects.create(user=self.user, media=media, caption='Test')
        response = self.client.post(f'/api/v1/feed/posts/{post.id}/report/', {
            'reason': 'SPAM',
            'description': 'Test report'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_stories_list(self):
        response = self.client.get('/api/v1/feed/stories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_story(self):
        from apps.feed.models import MediaAsset
        media = MediaAsset.objects.create(owner=self.user, type='photo', storage_url='https://example.com/img.jpg')
        response = self.client.post('/api/v1/feed/stories/', {
            'media': str(media.id),
            'caption': 'Test story'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
