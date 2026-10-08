import os
import django
from django.core.asgi import get_asgi_application

# 1. Force set the settings module variable immediately
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# 2. Initialize the complete Django application configuration workspace
django.setup()

# 3. Pull the baseline HTTP handling app AFTER setup runs
django_asgi_app = get_asgi_application()

# 4. Now safely import your channel layer dependencies below the initialization bar
from channels.routing import ProtocolTypeRouter, URLRouter
from marketplace.channels_middleware import JWTAuthMiddleware
import marketplace.routing

application = ProtocolTypeRouter({
    # Handles standard REST API and HTTP requests
    "http": django_asgi_app,
    
    # Handles persistent live chat connections cleanly
    "websocket": JWTAuthMiddleware(
        URLRouter(
            marketplace.routing.websocket_urlpatterns
        )
    ),
})
