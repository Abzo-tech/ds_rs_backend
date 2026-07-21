from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.contrib.gis.geos import Point
from drf_spectacular.utils import extend_schema
from .models import ARFilter
from .serializers import ARFilterSerializer, ARFilterManifestSerializer


@extend_schema(tags=['AR Filters'])class ARFilterListView(generics.ListAPIView):
    serializer_class = ARFilterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ARFilter.objects.filter(is_active=True)


@extend_schema(tags=['AR Filters'])class ARFilterDetailView(generics.RetrieveAPIView):
    serializer_class = ARFilterSerializer
    permission_classes = [IsAuthenticated]
    queryset = ARFilter.objects.filter(is_active=True)


@extend_schema(tags=['AR Filters'])class ARFilterManifestView(generics.ListAPIView):
    serializer_class = ARFilterManifestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')

        global_filters = ARFilter.objects.filter(is_active=True, is_geolocated=False)

        if lat and lng:
            try:
                user_location = Point(float(lng), float(lat), srid=4326)
                geo_filters = ARFilter.objects.filter(
                    is_active=True,
                    is_geolocated=True,
                    location__isnull=False
                ).extra(
                    where=["ST_DWithin(location, ST_GeogFromText(%s), radius_meters)"],
                    params=[f"SRID=4326;POINT({float(lng)} {float(lat)})"]
                )
                return (global_filters | geo_filters).distinct().order_by('-created_at')
            except (ValueError, TypeError):
                pass

        return global_filters.order_by('-created_at')
