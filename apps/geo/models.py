import uuid
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class PointOfInterest(models.Model):
    CATEGORY_CHOICES = [
        ('tourist', 'Touristique'),
        ('cultural', 'Culturel'),
        ('gastronomy', 'Gastronomique'),
        ('sport', 'Sportif'),
        ('joj_2026', 'JOD Dakar 2026'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='tourist')
    location = gis_models.PointField(srid=4326, geography=True)
    unlock_radius_meters = models.PositiveIntegerField(default=200)
    partner_establishment_id = models.UUIDField(blank=True, null=True)
    description = models.TextField(blank=True, max_length=500)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name


class POIFilterUnlock(models.Model):
    poi = models.ForeignKey(PointOfInterest, on_delete=models.CASCADE, related_name='filter_unlocks')
    ar_filter = models.ForeignKey('ar_filters.ARFilter', on_delete=models.CASCADE, related_name='poi_unlocks')

    class Meta:
        unique_together = ['poi', 'ar_filter']
        indexes = [models.Index(fields=['poi', 'ar_filter'])]

    def __str__(self):
        return f"{self.poi.name} -> {self.ar_filter.name}"
