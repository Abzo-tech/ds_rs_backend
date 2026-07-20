from rest_framework import serializers
from .models import ARFilter


class ARFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ARFilter
        fields = [
            'id', 'name', 'description', 'category', 'sdk_effect_id',
            'file_url', 'thumbnail_url', 'creator', 'location',
            'radius_meters', 'is_geolocated', 'is_time_limited',
            'available_from', 'available_until', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ARFilterManifestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ARFilter
        fields = [
            'id', 'name', 'description', 'category', 'sdk_effect_id',
            'thumbnail_url', 'is_geolocated', 'location', 'radius_meters'
        ]
