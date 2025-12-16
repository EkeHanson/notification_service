from django.core.management.base import BaseCommand
from notifications.models import NotificationTemplate, ChannelType
from notifications.events.registry import event_registry
import logging

logger = logging.getLogger('notifications.management')

class Command(BaseCommand):
    help = 'Seed default notification templates for all supported event types'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-id',
            required=True,
            help='Tenant ID to create templates for',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing templates',
        )

    def handle(self, *args, **options):
        tenant_id = options['tenant_id']
        overwrite = options['overwrite']

        self.stdout.write(
            self.style.SUCCESS(f'Seeding event templates for tenant {tenant_id}...')
        )

        templates_created = 0
        templates_skipped = 0

        # Get all supported events and their handlers
        for event_type in event_registry.get_supported_events():
            handler = event_registry.get_handler(event_type)

            # Create templates for each channel
            for channel in handler.get_default_channels(event_type):
                template_name = f"{event_type.replace('.', '_')}_{channel.value}"

                # Check if template exists
                existing = NotificationTemplate.objects.filter(
                    tenant_id=tenant_id,
                    name=template_name,
                    channel=channel
                ).first()

                if existing and not overwrite:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping existing template: {template_name}')
                    )
                    templates_skipped += 1
                    continue

                # Get content from handler
                content_map = handler.get_channel_content(event_type, {
                    # Sample payload for template creation
                    'first_name': '{{first_name}}',
                    'email': '{{email}}',
                    'code': '{{code}}',
                    'task_title': '{{task_title}}',
                    'author_name': '{{author_name}}',
                    'amount': '{{amount}}',
                    'invoice_id': '{{invoice_id}}'
                })

                content = content_map.get(channel.value, {})

                if content:
                    if existing and overwrite:
                        existing.content = content
                        existing.save()
                        self.stdout.write(
                            self.style.SUCCESS(f'Updated template: {template_name}')
                        )
                    else:
                        NotificationTemplate.objects.create(
                            tenant_id=tenant_id,
                            name=template_name,
                            channel=channel,
                            content=content,
                            placeholders=self._extract_placeholders(content),
                            is_active=True
                        )
                        self.stdout.write(
                            self.style.SUCCESS(f'Created template: {template_name}')
                        )
                    templates_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Seeding complete: {templates_created} created, {templates_skipped} skipped'
            )
        )

    def _extract_placeholders(self, content: dict) -> list:
        """Extract placeholder variables from template content"""
        placeholders = set()

        def find_placeholders(obj):
            if isinstance(obj, str):
                import re
                matches = re.findall(r'\{\{(\w+)\}\}', obj)
                placeholders.update(matches)
            elif isinstance(obj, dict):
                for value in obj.values():
                    find_placeholders(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_placeholders(item)

        find_placeholders(content)
        return list(placeholders)