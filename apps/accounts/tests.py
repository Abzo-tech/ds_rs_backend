from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'public',
            'consent_ai_training': True,
        }

    def test_register_success(self):
        response = self.client.post('/api/v1/auth/register/', self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertEqual(response.data['user']['email'], self.user_data['email'])

    def test_register_duplicate_email(self):
        User.objects.create_user(email=self.user_data['email'], password=self.user_data['password'])
        response = self.client.post('/api/v1/auth/register/', self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_partner_requires_establishment_id(self):
        data = self.user_data.copy()
        data['role'] = 'partner'
        response = self.client.post('/api/v1/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        User.objects.create_user(email=self.user_data['email'], password=self.user_data['password'])
        response = self.client.post('/api/v1/auth/login/', {
            'email': self.user_data['email'],
            'password': self.user_data['password'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_login_invalid_credentials(self):
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'wrong@example.com',
            'password': 'wrongpass',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_me_authenticated(self):
        user = User.objects.create_user(email=self.user_data['email'], password=self.user_data['password'])
        self.client.force_authenticate(user=user)
        response = self.client.get('/api/v1/users/me')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user_data['email'])

    def test_profile_me_unauthenticated(self):
        response = self.client.get('/api/v1/users/me')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
