from celery import shared_task
from django.utils import timezone
from django.db.models import Count
from django.conf import settings
from .models import Story, Post, Report
import json


@shared_task
def purge_expired_stories():
    expired = Story.objects.filter(expires_at__lt=timezone.now())
    count = expired.count()
    expired.delete()
    return f"Purged {count} expired stories"


@shared_task
def moderate_post_with_maadi_ai(post_id):
    from .models import Post
    try:
        post = Post.objects.get(id=post_id)

        from django.conf import settings
        if getattr(settings, 'MAADI_MOCK', True):
            _mock_moderate(post)
        else:
            _maadi_moderate(post)

        post.save(update_fields=['status', 'moderation_score'])
        print(f"[Maadi AI] Post {post_id} analysé. Statut final : {post.status}")
    except Post.DoesNotExist:
        print(f"[Maadi AI] Erreur : Le post {post_id} n'existe pas.")


def _mock_moderate(post):
    import random
    banned_words = ['scam', 'arnaque', 'insulte', 'piratage']
    contains_banned_word = any(word in (post.caption or '').lower() for word in banned_words)
    is_media_unsafe = random.random() < 0.10

    if contains_banned_word or is_media_unsafe:
        post.status = 'pending_review'
        post.moderation_score = 0.0
    else:
        post.status = 'published'
        post.moderation_score = round(random.uniform(0.7, 1.0), 2)


def _maadi_moderate(post):
    """Appel réel au service Maadi AI (fallback si indisponible)."""
    import requests
    from django.conf import settings
    try:
        response = requests.post(
            settings.MAADI_AI_URL,
            json={'post_id': str(post.id), 'caption': post.caption or ''},
            timeout=settings.MAADI_AI_TIMEOUT,
        )
        if response.status_code == 200:
            data = response.json()
            score = data.get('score', 1.0)
            post.moderation_score = score
            post.status = 'pending_review' if score < 0.5 else 'published'
            return
    except Exception as e:
        print(f"[Maadi AI] Service indisponible, fallback published: {e}")
    post.status = 'published'
    post.moderation_score = 1.0


@shared_task
def apply_watermark(media_asset_id):
    from .models import MediaAsset
    from PIL import Image, ImageDraw, ImageFont
    import requests
    import io
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    try:
        media = MediaAsset.objects.get(id=media_asset_id)
        if media.has_watermark:
            return f"Watermark déjà appliqué sur le média {media_asset_id}"

        if media.type != 'photo':
            return f"Le média {media_asset_id} n'est pas une image, watermark ignoré."

        response = requests.get(media.storage_url, timeout=10)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGBA")

        draw = ImageDraw.Draw(image)
        text = "Discover Sénégal"
        x = image.width - 10
        y = image.height - 10

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((x, y), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = x - text_width - 10
        y = y - text_height - 10

        overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle([x - 5, y - 5, x + text_width + 5, y + text_height + 5], fill=(0, 0, 0, 120))
        image = Image.alpha_composite(image, overlay)
        draw = ImageDraw.Draw(image)
        draw.text((x, y), text, fill=(255, 255, 255, 200), font=font)

        output_buffer = io.BytesIO()
        image.save(output_buffer, format="PNG")
        output_buffer.seek(0)

        file_path = f"watermarked/{media.id}.png"
        default_storage.save(file_path, ContentFile(output_buffer.read()))
        new_url = default_storage.url(file_path)

        media.watermarked_url = new_url
        media.has_watermark = True
        media.save(update_fields=['watermarked_url', 'has_watermark'])
        print(f"[Watermark] Watermark appliqué sur le média {media_asset_id}")
        return f"Watermark appliqué sur le média {media_asset_id}"
    except MediaAsset.DoesNotExist:
        print(f"[Watermark] Erreur : Le média {media_asset_id} n'existe pas.")
    except Exception as e:
        print(f"[Watermark] Erreur : {e}")


@shared_task
def check_report_threshold():
    reports = Report.objects.filter(created_at__gte=timezone.now() - timezone.timedelta(hours=24))
    post_reports = reports.values('post').annotate(count=Count('id')).filter(count__gte=3)
    for item in post_reports:
        post = Post.objects.get(id=item['post'])
        post.status = 'pending_review'
        post.save(update_fields=['status'])


@shared_task
def fanout_post_to_followers(post_id):
    from .models import Post
    from django.contrib.auth import get_user_model
    from apps.accounts.models import Follow
    import redis
    try:
        post = Post.objects.get(id=post_id)
        author_id = str(post.user_id)

        followers = Follow.objects.filter(followee_id=author_id).values_list('follower_id', flat=True)

        r = redis.Redis.from_url(getattr(settings, 'REDIS_URL', 'redis://127.0.0.1:6379/1'), decode_responses=True)

        score = post.created_at.timestamp()
        post_data = json.dumps({
            'post_id': str(post.id),
            'user_id': author_id,
            'created_at': post.created_at.isoformat(),
        })

        pipe = r.pipeline()
        for follower_id in followers:
            pipe.zadd(f"feed:user:{follower_id}", {post_data: score})
        pipe.execute()

        pipe = r.pipeline()
        pipe.zadd(f"feed:user:{author_id}", {post_data: score})
        pipe.execute()
    except Post.DoesNotExist:
        pass
    except Exception as e:
        print(f"[Fanout] Erreur: {e}")
