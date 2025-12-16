#!/usr/bin/env python
"""
Tenant Setup Script for Notification Service

This script sets up a new tenant with all necessary notification credentials
and default templates for production use.

Usage:
    python setup_tenant.py <tenant_id> [--interactive]

Example:
    python setup_tenant.py 550e8400-e29b-41d4-a716-446655440000 --interactive
"""

import os
import sys
import django
import argparse
import uuid
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')
django.setup()

from django.core.management import call_command
from notifications.models import TenantCredentials, NotificationTemplate, ChannelType

def main():
    parser = argparse.ArgumentParser(description='Set up notification service for a tenant')
    parser.add_argument('tenant_id', help='UUID of the tenant')
    parser.add_argument('--interactive', action='store_true',
                       help='Prompt for credentials interactively')
    parser.add_argument('--skip-credentials', action='store_true',
                       help='Skip credential setup')
    parser.add_argument('--skip-templates', action='store_true',
                       help='Skip template setup')

    args = parser.parse_args()

    # Validate tenant_id
    try:
        tenant_uuid = uuid.UUID(args.tenant_id)
    except ValueError:
        print(f"❌ Error: Invalid tenant_id format: {args.tenant_id}")
        sys.exit(1)

    tenant_id = str(tenant_uuid)
    print(f"🚀 Setting up notification service for tenant: {tenant_id}")

    # Step 1: Set up credentials
    if not args.skip_credentials:
        print("\n📧 Step 1: Setting up notification credentials...")
        setup_credentials(tenant_id, args.interactive)
    else:
        print("\n⏭️  Skipping credential setup")

    # Step 2: Set up templates
    if not args.skip_templates:
        print("\n📝 Step 2: Setting up notification templates...")
        setup_templates(tenant_id)
    else:
        print("\n⏭️  Skipping template setup")

    # Step 3: Verification
    print("\n✅ Step 3: Verifying setup...")
    verify_setup(tenant_id)

    print("\n🎉 Tenant setup complete!")
    print(f"📋 Summary for tenant {tenant_id}:")
    print(f"   - Credentials configured: {count_credentials(tenant_id)}")
    print(f"   - Templates created: {count_templates(tenant_id)}")
    print("\n🚀 Next steps:")
    print("   1. Start the notification service: docker-compose up -d")
    print("   2. Start event processing: python manage.py process_events")
    print("   3. Test with sample events")

def setup_credentials(tenant_id: str, interactive: bool):
    """Set up notification credentials for all channels"""
    channels = [
        ('email', 'Email notifications'),
        ('sms', 'SMS notifications'),
        ('push', 'Push notifications')
    ]

    for channel, description in channels:
        print(f"   Setting up {description}...")

        try:
            # Use management command
            call_command('setup_tenant_credentials', tenant_id, **{channel: True, 'interactive': interactive})
            print(f"   ✅ {channel} credentials configured")

        except Exception as e:
            print(f"   ❌ Failed to set up {channel}: {str(e)}")

def setup_templates(tenant_id: str):
    """Set up default notification templates"""
    try:
        call_command('setup_notification_templates', tenant_id)
        print("   ✅ Templates created successfully")
    except Exception as e:
        print(f"   ❌ Failed to create templates: {str(e)}")

def verify_setup(tenant_id: str):
    """Verify that setup was successful"""
    issues = []

    # Check credentials
    email_creds = TenantCredentials.objects.filter(
        tenant_id=tenant_id, channel='email', is_active=True
    ).exists()

    sms_creds = TenantCredentials.objects.filter(
        tenant_id=tenant_id, channel='sms', is_active=True
    ).exists()

    push_creds = TenantCredentials.objects.filter(
        tenant_id=tenant_id, channel='push', is_active=True
    ).exists()

    # Check templates
    templates_count = NotificationTemplate.objects.filter(
        tenant_id=tenant_id, is_active=True
    ).count()

    if not email_creds:
        issues.append("Email credentials not configured")
    if not sms_creds:
        issues.append("SMS credentials not configured")
    if not push_creds:
        issues.append("Push credentials not configured")
    if templates_count == 0:
        issues.append("No templates created")

    if issues:
        print("   ⚠️  Setup verification found issues:")
        for issue in issues:
            print(f"      - {issue}")
    else:
        print("   ✅ Setup verification passed")
        print(f"      - Email: {'✅' if email_creds else '❌'}")
        print(f"      - SMS: {'✅' if sms_creds else '❌'}")
        print(f"      - Push: {'✅' if push_creds else '❌'}")
        print(f"      - Templates: {templates_count} created")

def count_credentials(tenant_id: str) -> int:
    """Count active credentials for tenant"""
    return TenantCredentials.objects.filter(
        tenant_id=tenant_id, is_active=True
    ).count()

def count_templates(tenant_id: str) -> int:
    """Count active templates for tenant"""
    return NotificationTemplate.objects.filter(
        tenant_id=tenant_id, is_active=True
    ).count()

if __name__ == '__main__':
    main()