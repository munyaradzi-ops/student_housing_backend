# marketplace/channels_middleware.py
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from marketplace.models import User
from urllib.parse import parse_qs

@database_sync_to_async
def get_user_from_token(token_key):
    try:
        # Decode the JWT token explicitly
        access_token = AccessToken(token_key)
        user_id = access_token["user_id"]
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()

class JWTAuthMiddleware:
    """
    Custom Middleware to authenticate WebSockets using a JWT token query param.
    Expects: ws://127.0.0.1:8000/ws/chat/1/?token=<jwt_access_token>
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Extract the query string from the socket connection request scope
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        
        token = query_params.get("token", [None])[0]
        
        if token:
            scope["user"] = await get_user_from_token(token)
        else:
            scope["user"] = AnonymousUser()
            
        return await self.inner(scope, receive, send)
