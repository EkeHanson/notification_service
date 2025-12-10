from celery import shared_task, group
from notifications.models import (
    NotificationRecord, NotificationStatus, FailureReason,
    Campaign, CampaignStatus
)
from notifications.orchestrator.dispatcher import Dispatcher
from notifications.orchestrator.validator import validate_tenant_and_channel
from notifications.orchestrator.logger import log_event
from notifications.utils.exceptions import NotificationFailedError
from notifications.utils.kafka_producer import NotificationProducer
from django.utils import timezone
from django.conf import settings
import asyncio
import logging
import json
import smtplib
import socket

logger = logging.getLogger('notifications.tasks')

@shared_task
def send_bulk_campaign_task(campaign_id: str):
    campaign = Campaign.objects.get(id=campaign_id)
    campaign.status = CampaignStatus.SENDING.value
    campaign.save()

    # Create sub-tasks for each recipient
    sub_tasks = group(
        send_notification_task.s(
            str(NotificationRecord.objects.create(
                tenant_id=campaign.tenant_id,
                channel=campaign.channel,
                recipient=r['recipient'],
                context=r.get('context', {})
            ).id),
            campaign.channel,
            r['recipient'],
            campaign.content or {},
            r.get('context', {})
        )
        for r in campaign.recipients
    )

    # Execute group
    result = sub_tasks.delay()
    result.save()  # Track for progress

    # On completion (use chord for callback if needed)
    # For now, poll or use beat to update status
    # TODO: Implement callback to increment sent_count and set COMPLETED

    log_event('bulk_started', campaign_id, {'total': len(campaign.recipients)})
    logger.info(f"Bulk campaign {campaign_id} started with {len(campaign.recipients)} recipients")

# Optional: Callback task
@shared_task(bind=True)
def update_campaign_completion(self, campaign_id: str, results: list):
    campaign = Campaign.objects.get(id=campaign_id)
    successes = sum(1 for r in results if r.successful())
    campaign.sent_count = successes
    campaign.status = CampaignStatus.COMPLETED.value if successes == campaign.total_recipients else CampaignStatus.FAILED.value
    campaign.save()
    log_event('bulk_completed', campaign_id, {'sent': successes})


@shared_task(bind=True, max_retries=3)
def send_notification_task(self, record_id: str, channel: str, recipient: str, content: dict, context: dict):
    record = NotificationRecord.objects.get(id=record_id)
    record.status = NotificationStatus.RETRYING.value
    record.save()

    producer = NotificationProducer()

    try:
        creds = validate_tenant_and_channel(record.tenant_id, channel)
        # DIAGNOSTIC: log masked credentials and attempt a quick SMTP auth check
        try:
            _pwd = creds.get('password', '') or ''
            _pwd_preview = (_pwd[:6] + '...') if len(_pwd) > 6 else _pwd
            _looks_encrypted = str(_pwd).startswith('gAAAA')
            logger.info(f"🔍 TASK DIAG - creds summary for tenant {record.tenant_id}: smtp_host={creds.get('smtp_host')}, smtp_port={creds.get('smtp_port')}, username={creds.get('username')}, password_preview={_pwd_preview}, password_len={len(_pwd)}, looks_encrypted={_looks_encrypted}")

            # Quick SMTP auth probe (no message send) to detect auth failure early
            if creds.get('smtp_host') and creds.get('username'):
                try:
                    timeout = 10
                    if creds.get('use_ssl'):
                        conn = smtplib.SMTP_SSL(host=creds.get('smtp_host'), port=int(creds.get('smtp_port') or 465), timeout=timeout)
                    else:
                        conn = smtplib.SMTP(host=creds.get('smtp_host'), port=int(creds.get('smtp_port') or 587), timeout=timeout)
                    conn.ehlo()
                    if creds.get('use_tls') and not creds.get('use_ssl'):
                        conn.starttls()
                        conn.ehlo()
                    # set_debuglevel(0) to avoid verbose output; rely on exceptions
                    conn.set_debuglevel(0)
                    try:
                        conn.login(creds.get('username'), creds.get('password'))
                        logger.info(f"🔍 TASK DIAG - SMTP auth probe OK for tenant {record.tenant_id}")
                    except Exception as e:
                        logger.warning(f"🔍 TASK DIAG - SMTP auth probe FAILED for tenant {record.tenant_id}: {e}")
                    finally:
                        try:
                            conn.quit()
                        except Exception:
                            pass
                except (socket.timeout, socket.error) as e:
                    logger.warning(f"🔍 TASK DIAG - SMTP connection error for tenant {record.tenant_id}: {e}")
        except Exception as _diag_e:
            logger.warning(f"🔍 TASK DIAG - failed to run SMTP diagnostic: {_diag_e}")
        handler = Dispatcher.get_handler(channel, record.tenant_id, creds)

        # Use async_to_sync for proper async handling in Celery
        from asgiref.sync import async_to_sync
        result = async_to_sync(handler.send)(recipient, content, context, record_id)

        if result['success']:
            record.status = NotificationStatus.SUCCESS.value
            record.provider_response = json.dumps(result['response'])
            record.sent_at = timezone.now()
            log_event('sent', record_id, result)

            # Produce Kafka event
            producer.send_event(
                settings.KAFKA_TOPICS['notification_events'],
                {
                    'event_type': 'notification_sent',
                    'notification_id': str(record_id),
                    'tenant_id': str(record.tenant_id),
                    'channel': channel,
                    'recipient': recipient,
                    'timestamp': record.sent_at.isoformat()
                }
            )
        else:
            record.status = NotificationStatus.FAILED.value
            record.failure_reason = FailureReason.UNKNOWN_ERROR.value
            record.provider_response = result['error']
            raise NotificationFailedError(result['error'])

        record.save()

    except Exception as exc:
        record.retry_count += 1
        if record.retry_count >= record.max_retries:
            record.status = NotificationStatus.FAILED.value
            record.failure_reason = FailureReason.UNKNOWN_ERROR.value
            log_event('failed', record_id, {'error': str(exc)})

            # Produce failure event
            producer.send_event(
                settings.KAFKA_TOPICS['notification_events'],
                {
                    'event_type': 'notification_failed',
                    'notification_id': str(record_id),
                    'tenant_id': str(record.tenant_id),
                    'error': str(exc),
                    'timestamp': timezone.now().isoformat()
                }
            )
        else:
            self.retry(countdown=60 * (2 ** record.retry_count), exc=exc)
        record.save()



@shared_task
def process_error_task(record_id: str):
    # Handle dead-letter or final errors (e.g., notify tenant admin)
    logger.warning(f"Final error processing for {record_id}")
    # TODO: Integrate with tenant notification for alerts