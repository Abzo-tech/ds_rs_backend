import uuid
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

CATEGORY_CHOICES = [
    ('culture_traditions', 'Culture & Traditions'),
    ('lieux_patrimoine', 'Lieux & Patrimoine'),
    ('joj_2026', 'JOD Dakar 2026'),
    ('nature_faune', 'Nature & Faune'),
]


class ARFilter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name=_("Nom du filtre"))
    description = models.TextField(blank=True, max_length=500)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='joj_2026')
    sdk_effect_id = models.CharField(max_length=255, help_text=_("Identifiant du pack Banuba/DeepAR côté CDN"))
    file_url = models.URLField(max_length=500, verbose_name=_("Lien vers l'asset 3D / Filtre"))
    thumbnail_url = models.URLField(max_length=500, blank=True, null=True)
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_filters")
    location = gis_models.PointField(srid=4326, geography=True, null=True, blank=True, verbose_name=_("Lieu exclusif"))
    radius_meters = models.PositiveIntegerField(default=500, verbose_name=_("Rayon de disponibilité (mètres)"))
    is_geolocated = models.BooleanField(default=False)
    is_time_limited = models.BooleanField(default=False)
    available_from = models.DateTimeField(blank=True, null=True)
    available_until = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name=_("Disponible sur l'application"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'is_geolocated']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.name
