from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class GeoTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='SecurePass123!',
            role='public'
        )
        self.client.force_authenticate(user=self.user)

    def test_poi_list(self):
        from apps.geo.models import PointOfInterest
        PointOfInterest.objects.create(
            name='Test POI',
            location='POINT(-17.5 14.7)',
            is_active=True
        )
        response = self.client.get('/api/v1/geo/pois/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_poi_with_distance_filter(self):
        from apps.geo.models import PointOfInterest
        PointOfInterest.objects.create(
            name='Test POI',
            location='POINT(-17.5 14.7)',
            is_active=True
        )
        response = self.client.get('/api/v1/geo/pois/?lat=14.7&lng=-17.5&dist=5000')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
