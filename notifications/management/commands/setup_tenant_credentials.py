import json
import uuid
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from notifications.models import TenantCredentials, ChannelType
from notifications.utils.encryption import encrypt_data

class Command(BaseCommand):
    help = 'Set up notification credentials for a tenant'

    def add_arguments(self, parser):
        parser.add_argument(
            'tenant_id',
            type=str,
            help='UUID of the tenant'
        )
        parser.add_argument(
            '--email',
            action='store_true',
            help='Set up email credentials'
        )
        parser.add_argument(
            '--sms',
            action='store_true',
            help='Set up SMS credentials'
        )
        parser.add_argument(
            '--push',
            action='store_true',
            help='Set up push notification credentials'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Set up all channel credentials'
        )
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='Prompt for credentials interactively'
        )

    def handle(self, *args, **options):
        tenant_id = options['tenant_id']

        # Validate tenant_id format
        try:
            uuid.UUID(tenant_id)
        except ValueError:
            raise CommandError(f'Invalid tenant_id format: {tenant_id}')

        # Determine which channels to set up
        channels = []
        if options['all']:
            channels = [ChannelType.EMAIL, ChannelType.SMS, ChannelType.PUSH]
        else:
            if options['email']:
                channels.append(ChannelType.EMAIL)
            if options['sms']:
                channels.append(ChannelType.SMS)
            if options['push']:
                channels.append(ChannelType.PUSH)

        if not channels:
            self.stdout.write(
                self.style.WARNING('No channels specified. Use --email, --sms, --push, or --all')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Setting up credentials for tenant: {tenant_id}')
        )

        for channel in channels:
            try:
                self._setup_channel_credentials(tenant_id, channel, options['interactive'])
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f'Failed to set up {channel} credentials: {str(e)}')
                )

    def _setup_channel_credentials(self, tenant_id: str, channel: str, interactive: bool):
        """Set up credentials for a specific channel"""

        # Check if credentials already exist
        existing = TenantCredentials.objects.filter(
            tenant_id=tenant_id,
            channel=channel
        ).first()

        if existing:
            if not self._confirm_overwrite(channel):
                self.stdout.write(f'Skipping {channel} (credentials already exist)')
                return

        credentials = {}

        if interactive:
            credentials = self._get_credentials_interactive(channel)
        else:
            credentials = self._get_default_credentials(channel)

        if not credentials:
            self.stdout.write(f'Skipping {channel} (no credentials provided)')
            return

        # Encrypt sensitive fields
        encrypted_creds = self._encrypt_credentials(credentials, channel)

        # Create or update credentials
        creds_obj, created = TenantCredentials.objects.update_or_create(
            tenant_id=tenant_id,
            channel=channel,
            defaults={
                'credentials': encrypted_creds,
                'is_active': True
            }
        )

        action = 'Created' if created else 'Updated'
        self.stdout.write(
            self.style.SUCCESS(f'{action} {channel} credentials for tenant {tenant_id}')
        )

    def _get_credentials_interactive(self, channel: str) -> dict:
        """Get credentials interactively from user input"""
        self.stdout.write(f'\nSetting up {channel} credentials:')

        if channel == ChannelType.EMAIL:
            return {
                'smtp_host': input('SMTP Host (e.g., smtp.gmail.com): ').strip(),
                'smtp_port': int(input('SMTP Port (e.g., 587): ').strip()),
                'username': input('SMTP Username: ').strip(),
                'password': input('SMTP Password: ').strip(),
                'from_email': input('From Email Address: ').strip(),
                'use_tls': input('Use TLS? (y/n): ').strip().lower() == 'y'
            }

        elif channel == ChannelType.SMS:
            return {
                'account_sid': input('Twilio Account SID: ').strip(),
                'auth_token': input('Twilio Auth Token: ').strip(),
                'from_number': input('Twilio From Number (+1234567890): ').strip()
            }

        elif channel == ChannelType.PUSH:
            self.stdout.write('Firebase service account JSON required.')
            json_path = input('Path to Firebase service account JSON file: ').strip()
            try:
                with open(json_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.stderr.write(f'Error reading Firebase credentials: {e}')
                return {}

        return {}

    def _get_default_credentials(self, channel: str) -> dict:
        """Get default/test credentials for development"""
        self.stdout.write(
            self.style.WARNING(f'Using default/test credentials for {channel}. '
                             'Use --interactive for real credentials.')
        )

        if channel == ChannelType.EMAIL:
            return {
                'smtp_host': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': 'test@example.com',
                'password': 'test_password',
                'from_email': 'noreply@example.com',
                'use_tls': True
            }

        elif channel == ChannelType.SMS:
            return {
                'account_sid': 'ACtest1234567890',
                'auth_token': 'test_auth_token',
                'from_number': '+1234567890'
            }

        elif channel == ChannelType.PUSH:
            return {
                'type': 'service_account',
                'project_id': 'test-project',
                'private_key_id': 'test_key_id',
                'private_key': 'test_private_key',
                'client_email': 'test@test-project.iam.gserviceaccount.com',
                'client_id': '123456789',
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
                'client_x509_cert_url': 'https://www.googleapis.com/robot/v1/metadata/x509/test@test-project.iam.gserviceaccount.com'
            }

        return {}

    def _encrypt_credentials(self, credentials: dict, channel: str) -> dict:
        """Encrypt sensitive fields in credentials"""
        encrypted = credentials.copy()

        # Fields that need encryption
        sensitive_fields = {
            ChannelType.EMAIL: ['password'],
            ChannelType.SMS: ['auth_token'],
            ChannelType.PUSH: ['private_key']
        }

        for field in sensitive_fields.get(channel, []):
            if field in encrypted:
                encrypted[field] = encrypt_data(encrypted[field])

        return encrypted

    def _confirm_overwrite(self, channel: str) -> bool:
        """Ask user to confirm overwriting existing credentials"""
        response = input(f'{channel} credentials already exist. Overwrite? (y/n): ')
        return response.strip().lower() == 'y'