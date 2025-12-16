#!/usr/bin/env python
"""
Simple test runner for notification service tests
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    # Prefer test settings if present to avoid external DB dependencies
    os.environ['DJANGO_SETTINGS_MODULE'] = os.environ.get('DJANGO_TEST_SETTINGS_MODULE', 'notification_service.test_settings')
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True, keepdb=False)
    
    # Run all tests in the notifications app
    failures = test_runner.run_tests(["notifications.tests"])
    sys.exit(bool(failures))
