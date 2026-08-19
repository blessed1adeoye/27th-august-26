# a/asgi.py



import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import b.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'a.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            b.routing.websocket_urlpatterns
        )
    ),
})