from rest_framework import serializers
from .models import PointOfInterest, POIFilterUnlock


class PointOfInterestSerializer(serializers.ModelSerializer):
    distance = serializers.SerializerMethodField()

    class Meta:
        model = PointOfInterest
        fields = [
            'id', 'name', 'category', 'location', 'unlock_radius_meters',
            'partner_establishment_id', 'description', 'is_active', 'created_at', 'distance'
        ]
        read_only_fields = ['id', 'created_at', 'distance']

    def get_distance(self, obj):
        if hasattr(obj, 'distance'):
            return round(obj.distance.m, 1)
        return None


class POIFilterUnlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = POIFilterUnlock
        fields = ['poi', 'ar_filter']
