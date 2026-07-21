from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from drf_spectacular.utils import extend_schema
from .models import PointOfInterest
from .serializers import PointOfInterestSerializer
from apps.ar_filters.models import ARFilter
from apps.ar_filters.serializers import ARFilterSerializer


@extend_schema(tags=['Géolocalisation'])
class PointOfInterestViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PointOfInterestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = PointOfInterest.objects.filter(is_active=True)
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        dist = self.request.query_params.get('dist', 5000)

        if lat and lng:
            try:
                user_location = Point(float(lng), float(lat), srid=4326)
                queryset = queryset.filter(
                    location__dwithin=(user_location, float(dist))
                ).annotate(
                    distance=Distance('location', user_location)
                ).order_by('distance', 'name')
            except (ValueError, TypeError):
                pass

        return queryset


@extend_schema(tags=['Géolocalisation'])
class NearbyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        dist = request.query_params.get('dist', 5000)

        pois = PointOfInterest.objects.filter(is_active=True)
        ar_filters = ARFilter.objects.filter(is_active=True, is_geolocated=True)

        if lat and lng:
            try:
                user_location = Point(float(lng), float(lat), srid=4326)
                pois = pois.filter(location__dwithin=(user_location, float(dist)))
                ar_filters = ar_filters.filter(location__isnull=False).extra(
                    where=["ST_DWithin(location, ST_GeogFromText(%s), radius_meters)"],
                    params=[f"SRID=4326;POINT({float(lng)} {float(lat)})"]
                )
            except (ValueError, TypeError):
                pass

        return Response({
            'pois': PointOfInterestSerializer(pois, many=True).data,
            'ar_filters': ARFilterSerializer(ar_filters, many=True).data,
        }, status=status.HTTP_200_OK)
