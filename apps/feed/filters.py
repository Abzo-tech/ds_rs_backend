from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from rest_framework import filters

class DistanceFilterBackend(filters.BaseFilterBackend):
    """
    Filtre personnalisé permettant de récupérer les posts dans un rayon donné (en mètres)
    Exemple d'URL : /api/v1/feed/?lat=14.7214&lng=-17.4947&dist=5000
    """
    def filter_queryset(self, request, queryset, view):
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        dist = request.query_params.get('dist', 5000)

        if lat and lng:
            try:
                user_location = Point(float(lng), float(lat), srid=4326)
                queryset = queryset.filter(
                    location__dwithin=(user_location, float(dist))
                ).annotate(
                    distance=Distance('location', user_location)
                ).order_by('distance', '-created_at')
            except (ValueError, TypeError):
                pass

        return queryset