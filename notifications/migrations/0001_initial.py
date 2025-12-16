# Generated initial migration for notification models

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db.models import JSONField


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TenantCredentials',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('channel', models.CharField(choices=[('email', 'EMAIL'), ('sms', 'SMS'), ('push', 'PUSH'), ('inapp', 'INAPP')], max_length=10)),
                ('credentials', JSONField()),
                ('is_active', models.BooleanField(default=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='NotificationTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('name', models.CharField(max_length=255)),
                ('channel', models.CharField(choices=[('email', 'EMAIL'), ('sms', 'SMS'), ('push', 'PUSH'), ('inapp', 'INAPP')], max_length=10)),
                ('content', JSONField()),
                ('placeholders', JSONField(default=list)),
                ('version', models.PositiveIntegerField(default=1)),
                ('is_active', models.BooleanField(default=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='NotificationRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('channel', models.CharField(choices=[('email', 'EMAIL'), ('sms', 'SMS'), ('push', 'PUSH'), ('inapp', 'INAPP')], max_length=10)),
                ('recipient', models.CharField(max_length=500)),
                ('template_id', models.UUIDField(blank=True, null=True)),
                ('context', JSONField(default=dict)),
                ('status', models.CharField(choices=[('pending', 'PENDING'), ('success', 'SUCCESS'), ('failed', 'FAILED'), ('retrying', 'RETRYING')], default='pending', max_length=10)),
                ('failure_reason', models.CharField(blank=True, choices=[('auth_error', 'AUTH_ERROR'), ('network_error', 'NETWORK_ERROR'), ('provider_error', 'PROVIDER_ERROR'), ('content_error', 'CONTENT_ERROR'), ('unknown_error', 'UNKNOWN_ERROR')], max_length=20, null=True)),
                ('provider_response', models.TextField(blank=True)),
                ('retry_count', models.PositiveIntegerField(default=0)),
                ('max_retries', models.PositiveIntegerField(default=3)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('notification_id', models.UUIDField()),
                ('event', models.CharField(max_length=100)),
                ('details', JSONField(default=dict)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('user_id', models.UUIDField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='Campaign',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('name', models.CharField(max_length=255)),
                ('channel', models.CharField(choices=[('email', 'EMAIL'), ('sms', 'SMS'), ('push', 'PUSH'), ('inapp', 'INAPP')], max_length=10)),
                ('template_id', models.UUIDField(blank=True, null=True)),
                ('content', JSONField(blank=True, null=True)),
                ('recipients', JSONField(default=list)),
                ('total_recipients', models.PositiveIntegerField(default=0)),
                ('sent_count', models.PositiveIntegerField(default=0)),
                ('status', models.CharField(choices=[('draft', 'DRAFT'), ('scheduled', 'SCHEDULED'), ('sending', 'SENDING'), ('completed', 'COMPLETED'), ('failed', 'FAILED')], default='draft', max_length=10)),
                ('schedule_time', models.DateTimeField(blank=True, null=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddIndex(
            model_name='tenantcredentials',
            index=models.Index(fields=['tenant_id', 'channel'], name='notifications_ten_tenant__idx'),
        ),
        migrations.AddIndex(
            model_name='notificationtemplate',
            index=models.Index(fields=['tenant_id', 'name', 'channel'], name='notifications_not_tenant__idx'),
        ),
        migrations.AddIndex(
            model_name='notificationrecord',
            index=models.Index(fields=['tenant_id', 'status'], name='notifications_notif_tenant__idx'),
        ),
        migrations.AddIndex(
            model_name='notificationrecord',
            index=models.Index(fields=['tenant_id', 'created_at'], name='notifications_notif_tenant_2idx'),
        ),
        migrations.AddIndex(
            model_name='notificationrecord',
            index=models.Index(fields=['status', 'retry_count'], name='notifications_notif_status_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['tenant_id', 'timestamp'], name='notifications_audit_tenant__idx'),
        ),
        migrations.AddIndex(
            model_name='campaign',
            index=models.Index(fields=['tenant_id', 'status'], name='notifications_campaign_tenant__idx'),
        ),
        migrations.AlterUniqueTogether(
            name='tenantcredentials',
            unique_together={('tenant_id', 'channel')},
        ),
    ]
