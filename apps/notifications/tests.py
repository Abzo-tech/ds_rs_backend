from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class NotificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='SecurePass123!',
            role='public'
        )
        self.client.force_authenticate(user=self.user)

    def test_notification_list(self):
        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_register_fcm_token(self):
        response = self.client.post('/api/v1/notifications/fcm-token/', {
            'token': 'test_fcm_token_123',
            'device_type': 'android'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('id', response.data)
