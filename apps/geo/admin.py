from django.contrib import admin
from .models import PointOfInterest, POIFilterUnlock


@admin.register(PointOfInterest)
class PointOfInterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')


@admin.register(POIFilterUnlock)
class POIFilterUnlockAdmin(admin.ModelAdmin):
    list_display = ('poi', 'ar_filter')
    list_filter = ('poi', 'ar_filter')
