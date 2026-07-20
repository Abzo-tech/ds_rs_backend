from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from apps.accounts.models import CustomUser
from urllib.parse import parse_qs

@database_sync_to_async
def get_user_from_token(token_key):
    try:
        # Décode le token JWT d'accès
        access_token = AccessToken(token_key)
        user_id = access_token['user_id']
        return CustomUser.objects.get(id=user_id)
    except Exception:
        # Si le token est expiré, invalide ou que l'utilisateur n'existe pas
        return AnonymousUser()

class JWTAuthMiddleware:
    """
    Middleware personnalisé pour authentifier les connexions WebSocket 
    via un token JWT passé en paramètre d'URL (ex: ws://.../?token=XYZ)
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Récupère les paramètres de la chaîne de requête (Query String)
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        
        # Extrait le token s'il est présent
        token = query_params.get("token", [None])[0]
        
        if token:
            scope["user"] = await get_user_from_token(token)
        else:
            scope["user"] = AnonymousUser()
            
        return await self.inner(scope, receive, send)