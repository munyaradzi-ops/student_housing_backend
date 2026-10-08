# core/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from marketplace.channels_middleware import JWTAuthMiddleware # ◄ IMPORT YOUR NEW MIDDLEWARE
import marketplace.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = ProtocolTypeRouter({
    # Handles traditional HTTP queries
    "http": get_asgi_application(),
    
    # Updated WebSocket routing gate
    "websocket": JWTAuthMiddleware(
        URLRouter(
            marketplace.routing.websocket_urlpatterns
        )
    ),
})
