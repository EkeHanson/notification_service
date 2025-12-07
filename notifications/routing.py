from django.urls import re_path
from . import consumers, chat_consumers

websocket_urlpatterns = [
    # User-specific notifications
    re_path(r'ws/notifications/(?P<tenant_id>[^/]+)/$', consumers.NotificationConsumer.as_asgi()),

    # Tenant-wide broadcasts (optional)
    re_path(r'ws/tenant/(?P<tenant_id>[^/]+)/broadcast/$', consumers.TenantNotificationConsumer.as_asgi()),

    # Chat functionality
    re_path(r'ws/chat/(?P<tenant_id>[^/]+)/$', chat_consumers.ChatConsumer.as_asgi()),
]