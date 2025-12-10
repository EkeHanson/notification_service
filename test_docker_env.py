#!/usr/bin/env python
"""
Test script to verify Docker environment variables and credential loading
Run this inside the Docker container to verify configuration
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')
django.setup()

from django.conf import settings

def test_environment_variables():
    """Test that environment variables are loaded correctly"""
    print("🔍 Testing Docker Environment Variables")
    print("=" * 50)

    # Test email configuration
    print("\n📧 Email Configuration:")
    email_vars = [
        ('EMAIL_BACKEND', getattr(settings, 'EMAIL_BACKEND', 'Not set')),
        ('EMAIL_HOST', getattr(settings, 'EMAIL_HOST', 'Not set')),
        ('EMAIL_PORT', getattr(settings, 'EMAIL_PORT', 'Not set')),
        ('EMAIL_USE_SSL', getattr(settings, 'EMAIL_USE_SSL', 'Not set')),
        ('EMAIL_HOST_USER', getattr(settings, 'EMAIL_HOST_USER', 'Not set')),
        ('DEFAULT_FROM_EMAIL', getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')),
    ]

    for var_name, var_value in email_vars:
        status = "✅" if var_value != 'Not set' else "❌"
        print(f"  {status} {var_name}: {var_value}")

    # Test default credentials
    print("\n🔐 Default Notification Credentials:")
    default_creds = [
        ('DEFAULT_EMAIL_CREDENTIALS', getattr(settings, 'DEFAULT_EMAIL_CREDENTIALS', {})),
        ('DEFAULT_SMS_CREDENTIALS', getattr(settings, 'DEFAULT_SMS_CREDENTIALS', {})),
        ('DEFAULT_PUSH_CREDENTIALS', getattr(settings, 'DEFAULT_PUSH_CREDENTIALS', {})),
    ]

    for cred_name, cred_dict in default_creds:
        status = "✅" if cred_dict else "❌"
        print(f"  {status} {cred_name}: {len(cred_dict)} fields configured")

    # Test encryption key
    print("\n🔒 Encryption:")
    encryption_key = getattr(settings, 'ENCRYPTION_KEY', None)
    status = "✅" if encryption_key else "❌"
    print(f"  {status} ENCRYPTION_KEY: {'Set' if encryption_key else 'Not set'}")

    print("\n" + "=" * 50)
    print("🎉 Docker environment test completed!")
    print("\n💡 To configure real credentials:")
    print("   1. Edit the .env file with your actual credentials")
    print("   2. Uncomment the appropriate environment variables")
    print("   3. Restart the Docker containers")

if __name__ == '__main__':
    test_environment_variables()