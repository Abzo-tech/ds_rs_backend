import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps'))
django.setup()

from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.gis.geos import Point

from apps.geo.models import PointOfInterest
from apps.ar_filters.models import ARFilter

User = get_user_model()


class GeoAndFiltersTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='geo@example.com',
            password='geopass123',
            first_name='Geo',
            last_name='User',
            role='public',
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

        self.filter_global = ARFilter.objects.create(
            name='Filtre Culture',
            category='culture_traditions',
            sdk_effect_id='effect_global_001',
            is_active=True,
            is_geolocated=False,
        )
        self.filter_geo = ARFilter.objects.create(
            name='Filtre Gorée',
            category='lieux_patrimoine',
            sdk_effect_id='effect_geo_001',
            is_active=True,
            is_geolocated=True,
            location=Point(-17.8517, 14.6685, srid=4326),
            radius_meters=5000,
        )
        self.poi = PointOfInterest.objects.create(
            name='Île de Gorée',
            category='tourist',
            location=Point(-17.8517, 14.6685, srid=4326),
            unlock_radius_meters=5000,
            is_active=True,
        )
        self.poi.filter_unlocks.create(ar_filter=self.filter_geo)

    def test_ar_filter_manifest_global_only(self):
        response = self.client.get('/api/v1/ar-filters/manifest/')
        self.assertEqual(response.status_code, 200)
        ids = [f['id'] for f in response.data]
        self.assertIn(str(self.filter_global.id), ids)
        self.assertNotIn(str(self.filter_geo.id), ids)

    def test_ar_filter_manifest_with_location_unlocks_geo(self):
        # Position sur Gorée -> le filtre géolocalisé doit apparaître
        response = self.client.get('/api/v1/ar-filters/manifest/?lat=14.6685&lng=-17.8517')
        self.assertEqual(response.status_code, 200)
        ids = [f['id'] for f in response.data]
        self.assertIn(str(self.filter_global.id), ids)
        self.assertIn(str(self.filter_geo.id), ids)

    def test_poi_list_nearby(self):
        # Dakar centre ~ un peu au nord de Gorée, dist large
        response = self.client.get('/api/v1/geo/pois/?lat=14.7167&lng=-17.4677&dist=60000')
        self.assertEqual(response.status_code, 200)
        names = [p['name'] for p in response.data]
        self.assertIn('Île de Gorée', names)

    def test_nearby_endpoint_returns_geo_filters(self):
        response = self.client.get('/api/v1/geo/nearby/?lat=14.6685&lng=-17.8517&dist=6000')
        self.assertEqual(response.status_code, 200)
        self.assertIn('pois', response.data)
        self.assertIn('ar_filters', response.data)
        geo_ids = [f['id'] for f in response.data['ar_filters']]
        self.assertIn(str(self.filter_geo.id), geo_ids)
