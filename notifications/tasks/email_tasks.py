from celery import shared_task
from notifications.channels.email_handler import EmailHandler
import logging

logger = logging.getLogger('notifications.tasks.email')

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_email_task(self, tenant_id, credentials, recipient, content, context, record_id=None):
    try:
        # Flatten context if nested under 'template_data'
        if isinstance(context, dict) and 'template_data' in context and isinstance(context['template_data'], dict):
            flat_context = context['template_data'].copy()
            # Merge any top-level keys that aren't 'template_data' (e.g., content)
            for k, v in context.items():
                if k != 'template_data':
                    flat_context[k] = v
            context = flat_context
        handler = EmailHandler(tenant_id, credentials)
        result = handler.send.__wrapped__(handler, recipient, content, context, record_id)  # Call sync version
        logger.info(f"[Celery] Email sent: {result}")
        return result
    except Exception as exc:
        logger.error(f"[Celery] Email send failed: {exc}")
        raise self.retry(exc=exc)
