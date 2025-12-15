from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from notifications.models import NotificationRecord

@receiver(post_save, sender=NotificationRecord)
def send_inapp_notification_ws(sender, instance, created, **kwargs):
    if created and instance.channel == 'inapp':
        channel_layer = get_channel_layer()
        group_name = f"user_{instance.recipient}_tenant_{instance.tenant_id}"
        content = instance.context.get("content", {})
        notification_data = {
            "type": "inapp_notification",
            "id": str(instance.id),
            "title": content.get("title", "Notification"),
            "body": content.get("body", ""),
            "data": content.get("data", {}),
            "created_at": instance.created_at.isoformat(),
        }
        async_to_sync(channel_layer.group_send)(
            group_name,
            notification_data
        )
