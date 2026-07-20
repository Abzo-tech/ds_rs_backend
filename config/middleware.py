import time
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import status

RATE_LIMITS = {
    'feed': {'requests': 1000, 'window': 3600},      # 1000 req/hour
    'moderation': {'requests': 200, 'window': 3600}, # 200 req/hour
    'notifications': {'requests': 500, 'window': 3600}, # 500 req/hour
}

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        user_id = None
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
        
        client_ip = request.META.get('REMOTE_ADDR', '')
        cache_key = f"ratelimit:{user_id or client_ip}:{path}"
        
        for route_prefix, limit_config in RATE_LIMITS.items():
            if path.startswith(f'/api/v1/{route_prefix}/') or path.startswith(f'/api/v1/{route_prefix}'):
                cache_key = f"ratelimit:{user_id or client_ip}:{route_prefix}"
                current = cache.get(cache_key, 0)
                if current >= limit_config['requests']:
                    return JsonResponse(
                        {'detail': 'Trop de requêtes. Veuillez réessayer plus tard.'},
                        status=status.HTTP_429_TOO_MANY_REQUESTS
                    )
                cache.set(cache_key, current + 1, limit_config['window'])
                break
        
        return self.get_response(request)