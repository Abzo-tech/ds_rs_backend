from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class ARFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='SecurePass123!',
            role='public'
        )
        self.client.force_authenticate(user=self.user)

    def test_list_ar_filters(self):
        from apps.ar_filters.models import ARFilter
        ARFilter.objects.create(name='Test Filter', sdk_effect_id='test_effect', is_active=True)
        response = self.client.get('/api/v1/ar-filters/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)

    def test_manifest_without_location(self):
        from apps.ar_filters.models import ARFilter
        ARFilter.objects.create(name='Global Filter', sdk_effect_id='global', is_active=True, is_geolocated=False)
        response = self.client.get('/api/v1/ar-filters/manifest')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)

    def test_manifest_with_location(self):
        from apps.ar_filters.models import ARFilter
        ARFilter.objects.create(name='Geo Filter', sdk_effect_id='geo', is_active=True, is_geolocated=True)
        response = self.client.get('/api/v1/ar-filters/manifest?lat=14.7&lng=-17.5')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
