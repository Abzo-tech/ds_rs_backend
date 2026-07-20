import time
import random
import json
import uuid
import requests
from django.conf import settings
from django.db.models import F, FloatField, Case, When
from django.core.cache import cache
from .models import Post, Like, Comment


MAADI_AI_URL = getattr(settings, 'MAADI_AI_URL', 'http://localhost:8001/maadi/recommend')
MAADI_AI_TIMEOUT = getattr(settings, 'MAADI_AI_TIMEOUT', 0.3)


def get_maadi_recommendations(user_id, lat=None, lng=None, limit=20):
    try:
        payload = {
            "user_id": str(user_id),
            "behavior_signals": {},
            "location": {"lat": lat, "lng": lng} if lat and lng else None,
            "limit": limit,
        }
        start = time.time()
        response = requests.post(MAADI_AI_URL, json=payload, timeout=MAADI_AI_TIMEOUT)
        elapsed = time.time() - start

        if response.status_code == 200:
            data = response.json()
            post_ids = data.get('post_ids', [])
            if post_ids:
                posts = Post.objects.filter(id__in=post_ids, status='published')
                posts_dict = {str(p.id): p for p in posts}
                ordered_posts = [posts_dict[pid] for pid in post_ids if pid in posts_dict]
                return ordered_posts, 'maadi'
    except requests.exceptions.Timeout:
        pass
    except Exception as e:
        print(f"[Maadi AI] Erreur: {e}")

    return None, None


def get_fallback_feed(user_id, lat=None, lng=None, limit=20):
    cache_key = f"feed:fallback:{user_id}:{lat}:{lng}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached, 'fallback-cache'

    posts = Post.objects.filter(status='published').select_related('user', 'media', 'ar_filter').prefetch_related('likes_set', 'comments_set')

    posts = posts.annotate(
        engagement_score=(
            F('likes_count') * 1.0 +
            F('comments_count') * 2.0 +
            F('shares_count') * 3.0 +
            Case(
                When(is_sponsored=True, then=1000),
                When(is_sponsored=False, then=0),
                default=0,
                output_field=FloatField()
            )
        )
    ).order_by('-engagement_score', '-created_at')[:limit]

    result = list(posts)
    cache.set(cache_key, result, timeout=60)
    return result, 'fallback'


def get_personalized_feed(user_id, lat=None, lng=None, limit=20):
    cache_key = f"feed:personalized:{user_id}:{lat}:{lng}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached, 'cache'

    try:
        import redis
        r = redis.Redis.from_url(getattr(settings, 'REDIS_URL', 'redis://127.0.0.1:6379/1'), decode_responses=True)
        timeline_key = f"feed:user:{user_id}"
        post_data_list = r.zrevrange(timeline_key, 0, limit - 1, withscores=True)

        if post_data_list:
            post_ids = []
            for post_data, score in post_data_list:
                data = json.loads(post_data)
                post_ids.append(uuid.UUID(data['post_id']))

            if post_ids:
                posts = list(Post.objects.filter(id__in=post_ids, status='published'))
                posts.sort(key=lambda p: post_ids.index(p.id))
                cache.set(cache_key, posts, timeout=30)
                return posts, 'redis-timeline'
    except Exception:
        pass

    recommended_posts, source = get_maadi_recommendations(user_id, lat, lng, limit)
    if recommended_posts is not None:
        cache.set(cache_key, recommended_posts, timeout=30)
        return recommended_posts, source

    fallback_posts, source = get_fallback_feed(user_id, lat, lng, limit)
    return fallback_posts, source
