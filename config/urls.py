"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.feed.views import MaadiRecommendView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.accounts.urls')),
    path('api/v1/feed/', include('apps.feed.urls')),
    path('api/v1/chat/', include('apps.chat.urls')),
    path('api/v1/ar-filters/', include('apps.ar_filters.urls')),
    path('api/v1/geo/', include('apps.geo.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/internal/maadi/recommend/', MaadiRecommendView.as_view(), name='maadi-recommend'),
    path('api/docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
