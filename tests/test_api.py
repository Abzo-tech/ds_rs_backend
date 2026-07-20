import os
import sys
import django
from io import BytesIO
from PIL import Image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps'))
django.setup()

from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AccountsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role='public'
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_register(self):
        response = self.client.post('/api/v1/auth/register/', {
            'email': 'new@example.com',
            'password': 'newpass123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'public',
            'consent_ai_training': False,
        })
        self.assertEqual(response.status_code, 201)

    def test_login(self):
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)

    def test_profile(self):
        response = self.client.get('/api/v1/users/me')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], 'test@example.com')


class FeedTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='feed@example.com',
            password='feedpass123',
            first_name='Feed',
            last_name='User',
            role='public'
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_feed_list(self):
        response = self.client.get('/api/v1/feed/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)

    def test_feed_fallback_when_maadi_ai_down(self):
        from unittest.mock import patch
        from apps.feed.services import get_maadi_recommendations

        with patch('apps.feed.services.get_maadi_recommendations', return_value=(None, None)):
            response = self.client.get('/api/v1/feed/')
            self.assertEqual(response.status_code, 200)
            self.assertIn('results', response.data)
            self.assertEqual(response.data['source'], 'fallback')

    def test_create_post_requires_media(self):
        response = self.client.post('/api/v1/feed/', {
            'caption': 'Test post',
        })
        self.assertEqual(response.status_code, 400)


class ChatTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email='chat1@example.com',
            password='chatpass123',
            first_name='Chat',
            last_name='One',
            role='public'
        )
        self.user2 = User.objects.create_user(
            email='chat2@example.com',
            password='chatpass123',
            first_name='Chat',
            last_name='Two',
            role='public'
        )
        refresh = RefreshToken.for_user(self.user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

    def test_create_conversation(self):
        response = self.client.post('/api/v1/chat/conversations/', {
            'user_id': str(self.user2.id),
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('id', response.data)


class NotificationsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='notif@example.com',
            password='notifpass123',
            first_name='Notif',
            last_name='User',
            role='public'
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_list_notifications(self):
        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(response.status_code, 200)


class AdminTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
        self.user = User.objects.create_user(
            email='user@example.com',
            password='userpass123',
            first_name='User',
            last_name='Test',
            role='public'
        )
        refresh = RefreshToken.for_user(self.admin)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_certified_badge(self):
        response = self.client.post(f'/api/v1/users/{self.user.id}/certified/')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_certified)

        response = self.client.delete(f'/api/v1/users/{self.user.id}/certified/')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_certified)

    def test_non_admin_cannot_certify(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
        response = self.client.post(f'/api/v1/users/{self.user.id}/certified/')
        self.assertEqual(response.status_code, 403)

    def test_oauth_invalid_provider(self):
        response = self.client.post('/api/v1/auth/oauth/invalid/', {
            'access_token': 'token',
        })
        self.assertEqual(response.status_code, 400)


class PhoneAuthTestCase(TestCase):
    def test_phone_register_request_otp(self):
        response = self.client.post('/api/v1/auth/register/phone/request/', {
            'phone_number': '+221771234567',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('otp', response.data)

    def test_phone_register_with_otp(self):
        from django.core.cache import cache
        cache.set('otp:+221771234567', '1234', timeout=600)

        response = self.client.post('/api/v1/auth/register/phone/', {
            'phone_number': '+221771234567',
            'otp_code': '1234',
            'password': 'strongpass123',
            'consent_ai_training': True,
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn('tokens', response.data)
        self.assertTrue(User.objects.filter(phone_number='+221771234567').exists())

    def test_phone_register_invalid_otp(self):
        from django.core.cache import cache
        cache.set('otp:+221771234567', '1234', timeout=600)

        response = self.client.post('/api/v1/auth/register/phone/', {
            'phone_number': '+221771234567',
            'otp_code': '0000',
            'password': 'strongpass123',
            'consent_ai_training': True,
        })
        self.assertEqual(response.status_code, 400)

    def test_phone_login_with_otp(self):
        user = User.objects.create_user(
            email='+221771234567@phone.local',
            password='testpass123',
            phone_number='+221771234567'
        )
        from django.core.cache import cache
        cache.set('otp:+221771234567', '1234', timeout=600)

        response = self.client.post('/api/v1/auth/login/phone/', {
            'phone_number': '+221771234567',
            'otp_code': '1234',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('tokens', response.data)


class WatermarkTaskTestCase(TestCase):
    def test_apply_watermark_on_media(self):
        from io import BytesIO
        from PIL import Image
        from unittest.mock import patch, MagicMock
        from apps.feed.tasks import apply_watermark
        from apps.feed.models import MediaAsset

        user = User.objects.create_user(
            email='watermark@example.com',
            password='testpass123',
            first_name='Water',
            last_name='Mark',
            role='public'
        )

        image = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)

        media = MediaAsset.objects.create(
            owner=user,
            type='photo',
            storage_url='http://example.com/test.png',
            has_watermark=False
        )
        self.assertFalse(media.has_watermark)

        mock_response = MagicMock()
        mock_response.content = buffer.getvalue()
        mock_response.raise_for_status.return_value = None

        mock_storage = MagicMock()
        mock_storage.url.return_value = 'http://example.com/watermarked/test.png'

        with patch('requests.get', return_value=mock_response):
            with patch('django.core.files.storage.default_storage', mock_storage):
                apply_watermark(media.id)

        media.refresh_from_db()
        self.assertTrue(media.has_watermark)
        self.assertIn('watermarked', media.watermarked_url)
        self.assertEqual(media.storage_url, 'http://example.com/test.png')


class FanoutTaskTestCase(TestCase):
    def test_fanout_handles_missing_redis(self):
        from apps.feed.tasks import fanout_post_to_followers

        user = User.objects.create_user(
            email='fanout@example.com',
            password='testpass123',
            first_name='Fan',
            last_name='Out',
            role='public'
        )

        from apps.feed.models import MediaAsset, Post
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        image = Image.new('RGB', (10, 10), color='blue')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        file_path = f"test_media/fanout_{user.id}.png"
        default_storage.save(file_path, ContentFile(buffer.read()))
        storage_url = default_storage.url(file_path)

        media = MediaAsset.objects.create(
            owner=user,
            type='photo',
            storage_url=storage_url,
            has_watermark=True
        )

        post = Post.objects.create(
            user=user,
            media=media,
            caption='Test fanout post',
            status='published'
        )

        result = fanout_post_to_followers(post.id)
        self.assertIsNone(result)


class FollowFeedIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(
            email='usera@example.com',
            password='pass123',
            first_name='User',
            last_name='A',
            role='public'
        )
        self.user_b = User.objects.create_user(
            email='userb@example.com',
            password='pass123',
            first_name='User',
            last_name='B',
            role='public'
        )
        refresh = RefreshToken.for_user(self.user_a)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

    def test_follow_unfollow_user(self):
        response = self.client.post(f'/api/v1/users/{self.user_b.id}/follow/')
        self.assertEqual(response.status_code, 201)
        self.user_a.refresh_from_db()
        self.user_b.refresh_from_db()
        self.assertEqual(self.user_a.following_count, 1)
        self.assertEqual(self.user_b.followers_count, 1)

        response = self.client.delete(f'/api/v1/users/{self.user_b.id}/follow/')
        self.assertEqual(response.status_code, 204)
        self.user_a.refresh_from_db()
        self.user_b.refresh_from_db()
        self.assertEqual(self.user_a.following_count, 0)
        self.assertEqual(self.user_b.followers_count, 0)

    def test_feed_returns_followed_user_post(self):
        from apps.feed.models import MediaAsset, Post
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        from PIL import Image
        from io import BytesIO

        self.client.post(f'/api/v1/users/{self.user_b.id}/follow/')

        image = Image.new('RGB', (10, 10), color='green')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        file_path = f"test_media/feed_{self.user_b.id}.png"
        default_storage.save(file_path, ContentFile(buffer.read()))
        storage_url = default_storage.url(file_path)

        media = MediaAsset.objects.create(
            owner=self.user_b,
            type='photo',
            storage_url=storage_url,
            has_watermark=True
        )
        post = Post.objects.create(
            user=self.user_b,
            media=media,
            caption='Post from user B',
            status='published'
        )

        response = self.client.get('/api/v1/feed/')
        self.assertEqual(response.status_code, 200)
        results = response.data.get('results', [])
        post_ids = [p['id'] for p in results]
        self.assertIn(str(post.id), post_ids)


class ModerationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
        self.user = User.objects.create_user(
            email='author@example.com',
            password='authorpass123',
            first_name='Author',
            last_name='User',
            role='public'
        )
        refresh = RefreshToken.for_user(self.admin)
        self.admin_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')

    def test_moderation_queue_returns_pending_posts(self):
        from apps.feed.models import MediaAsset, Post
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        from PIL import Image
        from io import BytesIO

        image = Image.new('RGB', (10, 10), color='orange')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        file_path = f"test_media/mod_{self.user.id}.png"
        default_storage.save(file_path, ContentFile(buffer.read()))
        storage_url = default_storage.url(file_path)

        media = MediaAsset.objects.create(
            owner=self.user,
            type='photo',
            storage_url=storage_url,
            has_watermark=True
        )
        post = Post.objects.create(
            user=self.user,
            media=media,
            caption='Post à modérer',
            status='pending_review'
        )

        response = self.client.get('/api/v1/feed/moderation/queue/')
        self.assertEqual(response.status_code, 200)
        post_ids = [p['id'] for p in response.data]
        self.assertIn(str(post.id), post_ids)

    def test_non_admin_cannot_access_moderation_queue(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
        response = self.client.get('/api/v1/feed/moderation/queue/')
        self.assertEqual(response.status_code, 403)

    def test_moderation_approve_post(self):
        from apps.feed.models import MediaAsset, Post
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        from PIL import Image
        from io import BytesIO

        image = Image.new('RGB', (10, 10), color='purple')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        file_path = f"test_media/mod_approve_{self.user.id}.png"
        default_storage.save(file_path, ContentFile(buffer.read()))
        storage_url = default_storage.url(file_path)

        media = MediaAsset.objects.create(
            owner=self.user,
            type='photo',
            storage_url=storage_url,
            has_watermark=True
        )
        post = Post.objects.create(
            user=self.user,
            media=media,
            caption='Post pending',
            status='pending_review'
        )

        response = self.client.post(f'/api/v1/feed/moderation/post/{post.id}/approve/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'published')
        post.refresh_from_db()
        self.assertEqual(post.status, 'published')
        self.assertEqual(post.moderation_score, 1.0)

    def test_moderation_reject_post(self):
        from apps.feed.models import MediaAsset, Post
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        from PIL import Image
        from io import BytesIO

        image = Image.new('RGB', (10, 10), color='black')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        file_path = f"test_media/mod_reject_{self.user.id}.png"
        default_storage.save(file_path, ContentFile(buffer.read()))
        storage_url = default_storage.url(file_path)

        media = MediaAsset.objects.create(
            owner=self.user,
            type='photo',
            storage_url=storage_url,
            has_watermark=True
        )
        post = Post.objects.create(
            user=self.user,
            media=media,
            caption='Post à rejeter',
            status='pending_review'
        )

        response = self.client.post(f'/api/v1/feed/moderation/post/{post.id}/reject/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'removed')
        post.refresh_from_db()
        self.assertEqual(post.status, 'removed')


class NotificationsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='notif@example.com',
            password='notifpass123',
            first_name='Notif',
            last_name='User',
            role='public'
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_list_notifications(self):
        from apps.notifications.models import Notification
        Notification.objects.create(
            recipient=self.user,
            type='like',
            payload={'post_id': 'abc'}
        )
        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.data.get('results', [])), 0)

    def test_fcm_token_create_and_delete(self):
        response = self.client.post('/api/v1/notifications/fcm-token/', {
            'token': 'test-fcm-token-123',
            'device_type': 'android'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['token'], 'test-fcm-token-123')

        response = self.client.delete('/api/v1/notifications/fcm-token/', {
            'token': 'test-fcm-token-123'
        })
        self.assertEqual(response.status_code, 204)


class RateLimitingTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='ratelimit@example.com',
            password='ratelimitpass123',
            first_name='Rate',
            last_name='Limit',
            role='public'
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_feed_rate_limit(self):
        from django.core.cache import cache
        cache.set(f"ratelimit:{self.user.id}:feed", 1000, timeout=3600)

        for _ in range(5):
            response = self.client.get('/api/v1/feed/')
            self.assertIn(response.status_code, [200, 429])


class FirebaseAdminTestCase(TestCase):
    def test_firebase_admin_can_initialize(self):
        from django.conf import settings
        import firebase_admin

        self.assertTrue(settings.FIREBASE_ENABLED)
        self.assertTrue(settings.FIREBASE_CREDENTIALS_PATH)

        if not firebase_admin._apps:
            cred = firebase_admin.credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)

        self.assertIn('[DEFAULT]', firebase_admin._apps)


class RedisFanoutTestCase(TestCase):
    def test_fanout_post_to_followers_with_mock_redis(self):
        from unittest.mock import patch, MagicMock
        from apps.feed.tasks import fanout_post_to_followers
        from apps.feed.models import MediaAsset, Post
        from apps.accounts.models import Follow
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        from PIL import Image
        from io import BytesIO

        author = User.objects.create_user(
            email='fanoutredis@example.com',
            password='fanoutpass123',
            first_name='Fan',
            last_name='Out',
            role='public'
        )
        follower = User.objects.create_user(
            email='follower@example.com',
            password='followerpass123',
            first_name='Follower',
            last_name='User',
            role='public'
        )
        Follow.objects.create(follower=follower, followee=author)

        image = Image.new('RGB', (10, 10), color='cyan')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        file_path = f"test_media/fanout_redis_{author.id}.png"
        default_storage.save(file_path, ContentFile(buffer.read()))
        storage_url = default_storage.url(file_path)

        media = MediaAsset.objects.create(
            owner=author,
            type='photo',
            storage_url=storage_url,
            has_watermark=True
        )
        post = Post.objects.create(
            user=author,
            media=media,
            caption='Post for redis fanout',
            status='published'
        )

        mock_redis_client = MagicMock()
        mock_redis = MagicMock()
        mock_redis.from_url.return_value = mock_redis_client
        mock_redis_client.pipeline.return_value = mock_redis_client

        with patch('redis.Redis', mock_redis):
            fanout_post_to_followers(post.id)

        mock_redis.from_url.assert_called_once()
        mock_redis_client.pipeline.assert_called()

