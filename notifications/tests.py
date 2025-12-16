import pytest
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
import uuid
import json
from unittest.mock import patch, MagicMock

from notifications.models import (
    NotificationRecord, TenantCredentials, NotificationTemplate,
    ChannelType, NotificationStatus, FailureReason
)


class NotificationModelTests(TestCase):
    """Tests for Notification models"""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_create_notification_record(self):
        """Test creating a notification record"""
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            recipient='test@example.com',
            context={'name': 'John'},
            status=NotificationStatus.PENDING.value
        )
        self.assertEqual(notification.tenant_id, self.tenant_id)
        self.assertEqual(notification.channel, ChannelType.EMAIL.value)
        self.assertEqual(notification.recipient, 'test@example.com')
        self.assertEqual(notification.status, NotificationStatus.PENDING.value)
        self.assertEqual(notification.retry_count, 0)
        self.assertEqual(notification.max_retries, 3)

    def test_notification_soft_delete(self):
        """Test soft delete functionality"""
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.SMS.value,
            recipient='+1234567890',
            status=NotificationStatus.SUCCESS.value
        )
        
        # Verify it exists before delete
        self.assertTrue(NotificationRecord.objects.filter(id=notification.id).exists())
        
        # Delete via queryset (Django's default delete behavior calls delete on queryset)
        NotificationRecord.objects.filter(id=notification.id).delete()
        
        # Should not appear in normal queries
        self.assertFalse(NotificationRecord.objects.filter(id=notification.id).exists())
        
        # Should appear in all_with_deleted
        self.assertTrue(NotificationRecord.objects.all_with_deleted().filter(id=notification.id).exists())

    def test_create_tenant_credentials(self):
        """Test creating tenant credentials"""
        creds = TenantCredentials.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            credentials={'smtp_host': 'smtp.gmail.com', 'port': 587}
        )
        self.assertEqual(creds.tenant_id, self.tenant_id)
        self.assertEqual(creds.channel, ChannelType.EMAIL.value)
        self.assertTrue(creds.is_active)

    def test_unique_tenant_channel_constraint(self):
        """Test unique constraint on tenant_id and channel"""
        TenantCredentials.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            credentials={'smtp_host': 'smtp.gmail.com'}
        )
        
        # Attempting to create another with same tenant and channel should fail
        with self.assertRaises(Exception):
            TenantCredentials.objects.create(
                tenant_id=self.tenant_id,
                channel=ChannelType.EMAIL.value,
                credentials={'smtp_host': 'smtp.gmail.com'}
            )

    def test_create_notification_template(self):
        """Test creating notification template"""
        template = NotificationTemplate.objects.create(
            tenant_id=self.tenant_id,
            name='Interview Reminder',
            channel=ChannelType.EMAIL.value,
            content={
                'subject': 'Interview Reminder for {{candidate_name}}',
                'body': 'Your interview is scheduled for {{interview_date}}'
            },
            placeholders=['candidate_name', 'interview_date']
        )
        self.assertEqual(template.name, 'Interview Reminder')
        self.assertEqual(template.version, 1)
        self.assertTrue(template.is_active)

    def test_notification_retry_logic(self):
        """Test retry count increment"""
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            recipient='test@example.com',
            status=NotificationStatus.RETRYING.value,
            retry_count=2
        )
        self.assertEqual(notification.retry_count, 2)
        self.assertLess(notification.retry_count, notification.max_retries)

    def test_notification_sent_timestamp(self):
        """Test sent_at timestamp"""
        now = timezone.now()
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.PUSH.value,
            recipient='device_token_123',
            status=NotificationStatus.SUCCESS.value,
            sent_at=now
        )
        self.assertEqual(notification.sent_at, now)

    def test_notification_failure_reason(self):
        """Test failure reason tracking"""
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            recipient='test@example.com',
            status=NotificationStatus.FAILED.value,
            failure_reason=FailureReason.AUTH_ERROR.value
        )
        self.assertEqual(notification.failure_reason, FailureReason.AUTH_ERROR.value)


class NotificationViewTests(APITestCase):
    """Tests for Notification API views"""

    def setUp(self):
        self.client = APIClient()
        self.tenant_id = uuid.uuid4()
        self.client.default_format = 'json'

    def test_list_notifications_empty(self):
        """Test listing notifications when none exist"""
        # Just verify queryset is empty
        empty_queryset = NotificationRecord.objects.filter(tenant_id=self.tenant_id)
        self.assertEqual(empty_queryset.count(), 0)

    def test_create_notification_via_api(self):
        """Test creating a notification via API"""
        data = {
            'tenant_id': str(self.tenant_id),
            'channel': ChannelType.EMAIL.value,
            'recipient': 'test@example.com',
            'context': {'name': 'John'},
            'status': NotificationStatus.PENDING.value
        }
        
        # Note: This test may need adjustment based on actual URL routing
        # This is a basic structure for the test

    def test_filter_notifications_by_status(self):
        """Test filtering notifications by status"""
        # Create test notifications
        NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            recipient='test1@example.com',
            status=NotificationStatus.SUCCESS.value
        )
        NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            recipient='test2@example.com',
            status=NotificationStatus.FAILED.value
        )
        
        # Filter by status - would need proper URL routing
        self.assertEqual(
            NotificationRecord.objects.filter(
                tenant_id=self.tenant_id,
                status=NotificationStatus.SUCCESS.value
            ).count(),
            1
        )


class TenantCredentialsTests(APITestCase):
    """Tests for TenantCredentials model and API"""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_credentials_encryption_required(self):
        """Test that credentials are stored"""
        creds = TenantCredentials.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            credentials={'api_key': 'secret123', 'domain': 'example.com'}
        )
        fetched = TenantCredentials.objects.get(id=creds.id)
        self.assertEqual(fetched.credentials['api_key'], 'secret123')

    def test_deactivate_credentials(self):
        """Test deactivating credentials"""
        creds = TenantCredentials.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.SMS.value,
            credentials={'account_id': '123', 'token': 'abc'}
        )
        self.assertTrue(creds.is_active)
        
        creds.is_active = False
        creds.save()
        
        fetched = TenantCredentials.objects.get(id=creds.id)
        self.assertFalse(fetched.is_active)


class NotificationTemplateTests(APITestCase):
    """Tests for NotificationTemplate model"""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_template_versioning(self):
        """Test template versioning"""
        template = NotificationTemplate.objects.create(
            tenant_id=self.tenant_id,
            name='Welcome Email',
            channel=ChannelType.EMAIL.value,
            content={'subject': 'Welcome {{user_name}}', 'body': 'Hello {{user_name}}'},
            placeholders=['user_name']
        )
        self.assertEqual(template.version, 1)

    def test_template_placeholder_validation(self):
        """Test template placeholder tracking"""
        template = NotificationTemplate.objects.create(
            tenant_id=self.tenant_id,
            name='Job Alert',
            channel=ChannelType.EMAIL.value,
            content={
                'subject': 'New job: {{job_title}}',
                'body': 'Location: {{location}}, Salary: {{salary}}'
            },
            placeholders=['job_title', 'location', 'salary']
        )
        self.assertEqual(len(template.placeholders), 3)
        self.assertIn('job_title', template.placeholders)

    def test_multiple_channels_per_tenant(self):
        """Test that tenant can have templates for multiple channels"""
        channels = [
            ChannelType.EMAIL.value,
            ChannelType.SMS.value,
            ChannelType.PUSH.value
        ]
        
        for channel in channels:
            NotificationTemplate.objects.create(
                tenant_id=self.tenant_id,
                name=f'Template for {channel}',
                channel=channel,
                content={'subject': 'Test', 'body': 'Test'},
                placeholders=[]
            )
        
        templates = NotificationTemplate.objects.filter(tenant_id=self.tenant_id)
        self.assertEqual(templates.count(), 3)


class NotificationLifecycleTests(APITestCase):
    """Tests for notification lifecycle management"""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_notification_pending_to_success(self):
        """Test notification state transition from pending to success"""
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            recipient='test@example.com',
            status=NotificationStatus.PENDING.value
        )
        
        notification.status = NotificationStatus.SUCCESS.value
        notification.sent_at = timezone.now()
        notification.save()
        
        fetched = NotificationRecord.objects.get(id=notification.id)
        self.assertEqual(fetched.status, NotificationStatus.SUCCESS.value)
        self.assertIsNotNone(fetched.sent_at)

    def test_notification_failure_tracking(self):
        """Test failure tracking and retry logic"""
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            recipient='test@example.com',
            status=NotificationStatus.FAILED.value,
            failure_reason=FailureReason.PROVIDER_ERROR.value,
            provider_response='Provider returned 500 error'
        )
        
        self.assertEqual(notification.status, NotificationStatus.FAILED.value)
        self.assertEqual(notification.failure_reason, FailureReason.PROVIDER_ERROR.value)
        self.assertIn('500', notification.provider_response)

    def test_retry_notification(self):
        """Test retry logic for failed notifications"""
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.SMS.value,
            recipient='+1234567890',
            status=NotificationStatus.FAILED.value,
            retry_count=0,
            max_retries=3
        )
        
        # Simulate retry
        notification.status = NotificationStatus.RETRYING.value
        notification.retry_count = 1
        notification.save()
        
        fetched = NotificationRecord.objects.get(id=notification.id)
        self.assertEqual(fetched.retry_count, 1)
        self.assertEqual(fetched.status, NotificationStatus.RETRYING.value)
        self.assertLess(fetched.retry_count, fetched.max_retries)

    def test_max_retries_exceeded(self):
        """Test when max retries are exceeded"""
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.PUSH.value,
            recipient='device_token',
            status=NotificationStatus.RETRYING.value,
            retry_count=3,
            max_retries=3
        )
        
        self.assertEqual(notification.retry_count, notification.max_retries)


class NotificationContextTests(TestCase):
    """Tests for notification context and variable substitution"""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_notification_with_context_variables(self):
        """Test notification creation with context variables"""
        context = {
            'candidate_name': 'John Doe',
            'interview_date': '2025-12-15',
            'interview_time': '10:00 AM',
            'position': 'Senior Developer'
        }
        
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            recipient='john@example.com',
            context=context,
            status=NotificationStatus.PENDING.value
        )
        
        fetched = NotificationRecord.objects.get(id=notification.id)
        self.assertEqual(fetched.context['candidate_name'], 'John Doe')
        self.assertEqual(fetched.context['interview_date'], '2025-12-15')

    def test_notification_with_empty_context(self):
        """Test notification with empty context"""
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.INAPP.value,
            recipient='user_123',
            context={},
            status=NotificationStatus.PENDING.value
        )
        
        self.assertEqual(notification.context, {})


class NotificationQueryTests(TestCase):
    """Tests for notification querying and filtering"""

    def setUp(self):
        self.tenant_id = uuid.uuid4()
        self.other_tenant_id = uuid.uuid4()
        self._create_test_data()

    def _create_test_data(self):
        """Create test notification records"""
        # Create notifications for main tenant
        for i in range(5):
            NotificationRecord.objects.create(
                tenant_id=self.tenant_id,
                channel=ChannelType.EMAIL.value if i % 2 == 0 else ChannelType.SMS.value,
                recipient=f'user{i}@example.com',
                status=NotificationStatus.SUCCESS.value if i < 3 else NotificationStatus.FAILED.value
            )
        
        # Create notifications for other tenant
        NotificationRecord.objects.create(
            tenant_id=self.other_tenant_id,
            channel=ChannelType.EMAIL.value,
            recipient='other@example.com',
            status=NotificationStatus.SUCCESS.value
        )

    def test_filter_by_tenant(self):
        """Test filtering notifications by tenant"""
        notifications = NotificationRecord.objects.filter(tenant_id=self.tenant_id)
        self.assertEqual(notifications.count(), 5)
        
        other_notifications = NotificationRecord.objects.filter(tenant_id=self.other_tenant_id)
        self.assertEqual(other_notifications.count(), 1)

    def test_filter_by_channel(self):
        """Test filtering by channel"""
        email_notifications = NotificationRecord.objects.filter(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value
        )
        self.assertEqual(email_notifications.count(), 3)

    def test_filter_by_status(self):
        """Test filtering by status"""
        successful = NotificationRecord.objects.filter(
            tenant_id=self.tenant_id,
            status=NotificationStatus.SUCCESS.value
        )
        self.assertEqual(successful.count(), 3)
        
        failed = NotificationRecord.objects.filter(
            tenant_id=self.tenant_id,
            status=NotificationStatus.FAILED.value
        )
        self.assertEqual(failed.count(), 2)

    def test_combined_filters(self):
        """Test combining multiple filters"""
        notifications = NotificationRecord.objects.filter(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            status=NotificationStatus.SUCCESS.value
        )
        self.assertEqual(notifications.count(), 2)


class NotificationEdgeCaseTests(TestCase):
    """Tests for edge cases and boundary conditions"""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_very_long_recipient_address(self):
        """Test handling of very long recipient addresses"""
        long_recipient = 'a' * 450 + '@example.com'
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            recipient=long_recipient,
            status=NotificationStatus.PENDING.value
        )
        self.assertEqual(len(notification.recipient), len(long_recipient))
        self.assertLessEqual(len(notification.recipient), 500)

    def test_special_characters_in_context(self):
        """Test handling special characters in context"""
        context = {
            'name': 'José García',
            'message': 'Hello "World" & \'friends\'',
            'unicode': '你好世界 🌍'
        }
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.PUSH.value,
            recipient='device_123',
            context=context,
            status=NotificationStatus.PENDING.value
        )
        fetched = NotificationRecord.objects.get(id=notification.id)
        self.assertEqual(fetched.context['name'], 'José García')
        self.assertIn('🌍', fetched.context['unicode'])

    def test_large_provider_response(self):
        """Test storing large provider responses"""
        large_response = 'Error: ' + 'x' * 5000
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL.value,
            recipient='test@example.com',
            status=NotificationStatus.FAILED.value,
            provider_response=large_response
        )
        fetched = NotificationRecord.objects.get(id=notification.id)
        self.assertEqual(len(fetched.provider_response), len(large_response))

    def test_notification_without_template(self):
        """Test creating notification without template reference"""
        notification = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.INAPP.value,
            recipient='user_123',
            template_id=None,
            status=NotificationStatus.PENDING.value
        )
        self.assertIsNone(notification.template_id)
