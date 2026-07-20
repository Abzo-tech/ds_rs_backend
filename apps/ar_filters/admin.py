from django.contrib import admin
from .models import ARFilter


@admin.register(ARFilter)
class ARFilterAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'is_geolocated', 'created_at')
    list_filter = ('category', 'is_active', 'is_geolocated', 'is_time_limited')
    search_fields = ('name', 'description', 'sdk_effect_id')
    ordering = ('-created_at',)
