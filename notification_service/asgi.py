import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')

# Import routing inside the application to avoid premature Django setup
def get_websocket_urlpatterns():
    import notifications.routing  # Import here to avoid AppRegistryNotReady
    return notifications.routing.websocket_urlpatterns

def get_websocket_application():
    from .websocket_middleware import WebSocketJWTMiddleware
    return WebSocketJWTMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                get_websocket_urlpatterns()
            )
        )
    )

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": get_websocket_application(),
})