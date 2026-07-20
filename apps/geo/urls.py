from django.urls import path
from .views import PointOfInterestViewSet, NearbyView

app_name = 'geo'

urlpatterns = [
    path('pois/', PointOfInterestViewSet.as_view({'get': 'list'}), name='poi-list'),
    path('nearby/', NearbyView.as_view(), name='nearby'),
]
