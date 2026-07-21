#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.ar_filters.models import ARFilter

User = get_user_model()

# Create or get a creator user
creator, created = User.objects.get_or_create(
    email='ar-filter-creator@discover-senegal.sn',
    defaults={
        'first_name': 'AR',
        'last_name': 'Creator',
        'role': 'admin',
    }
)
if created:
    creator.set_password('ARFilter2026!')
    creator.save()
    print(f"Created creator user: {creator.email}")
else:
    print(f"Using existing creator user: {creator.email}")

# Example AR filters
filters_data = [
    {
        'name': 'Lion du Sénégal',
        'description': 'Filtre lion africain pour la coupe du monde',
        'category': 'joj_2026',
        'sdk_effect_id': 'lion_snr_01',
        'file_url': 'https://discover-senegal-media.r2.cloudflarestorage.com/filters/lion_snr_01.zip',
        'thumbnail_url': 'https://discover-senegal-media.r2.cloudflarestorage.com/filters/lion_snr_01_thumb.jpg',
        'creator': creator,
        'is_geolocated': False,
        'is_time_limited': False,
        'is_active': True,
    },
    {
        'name': 'Gorgette Traditionnelle',
        'description': 'Bijou traditionnel sénégalais',
        'category': 'culture_traditions',
        'sdk_effect_id': 'gorgette_snr_01',
        'file_url': 'https://discover-senegal-media.r2.cloudflarestorage.com/filters/gorgette_snr_01.zip',
        'thumbnail_url': 'https://discover-senegal-media.r2.cloudflarestorage.com/filters/gorgette_snr_01_thumb.jpg',
        'creator': creator,
        'is_geolocated': True,
        'location': 'POINT(-17.4677 14.7167)',
        'radius_meters': 500,
        'is_time_limited': False,
        'is_active': True,
    },
    {
        'name': 'Monument de la Renaissance',
        'description': 'Filtre exclusif du Monument de la Renaissance Africaine',
        'category': 'lieux_patrimoine',
        'sdk_effect_id': 'renaissance_snr_01',
        'file_url': 'https://discover-senegal-media.r2.cloudflarestorage.com/filters/renaissance_snr_01.zip',
        'thumbnail_url': 'https://discover-senegal-media.r2.cloudflarestorage.com/filters/renaissance_snr_01_thumb.jpg',
        'creator': creator,
        'is_geolocated': True,
        'location': 'POINT(-17.4753 14.7208)',
        'radius_meters': 200,
        'is_time_limited': True,
        'available_from': '2026-07-01T00:00:00Z',
        'available_until': '2026-08-01T00:00:00Z',
        'is_active': True,
    },
    {
        'name': 'Faune du Saloum',
        'description': 'Filtre animaux du Parc du Saloum',
        'category': 'nature_faune',
        'sdk_effect_id': 'saloum_snr_01',
        'file_url': 'https://discover-senegal-media.r2.cloudflarestorage.com/filters/saloum_snr_01.zip',
        'thumbnail_url': 'https://discover-senegal-media.r2.cloudflarestorage.com/filters/saloum_snr_01_thumb.jpg',
        'creator': creator,
        'is_geolocated': True,
        'location': 'POINT(-16.7167 13.8667)',
        'radius_meters': 5000,
        'is_time_limited': False,
        'is_active': True,
    },
]

created_count = 0
for data in filters_data:
    filter_obj, created = ARFilter.objects.get_or_create(
        sdk_effect_id=data['sdk_effect_id'],
        defaults=data
    )
    if created:
        created_count += 1
        print(f"Created filter: {filter_obj.name}")
    else:
        print(f"Filter already exists: {filter_obj.name}")

print(f"\nTotal filters created: {created_count}")
print(f"Total filters in DB: {ARFilter.objects.count()}")