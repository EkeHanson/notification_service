import uuid
from django.core.management.base import BaseCommand, CommandError
from notifications.models import NotificationTemplate, ChannelType

class Command(BaseCommand):
    help = 'Set up default notification templates for a tenant'

    def add_arguments(self, parser):
        parser.add_argument(
            'tenant_id',
            type=str,
            help='UUID of the tenant'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing templates'
        )

    def handle(self, *args, **options):
        tenant_id = options['tenant_id']
        overwrite = options['overwrite']

        # Validate tenant_id format
        try:
            uuid.UUID(tenant_id)
        except ValueError:
            raise CommandError(f'Invalid tenant_id format: {tenant_id}')

        self.stdout.write(
            self.style.SUCCESS(f'Setting up notification templates for tenant: {tenant_id}')
        )

        templates_created = 0
        templates_updated = 0

        # Authentication templates
        templates_created += self._create_auth_templates(tenant_id, overwrite)
        templates_updated += self._update_auth_templates(tenant_id, overwrite)

        # Application templates
        templates_created += self._create_app_templates(tenant_id, overwrite)
        templates_updated += self._update_app_templates(tenant_id, overwrite)

        # Security templates
        templates_created += self._create_security_templates(tenant_id, overwrite)
        templates_updated += self._update_security_templates(tenant_id, overwrite)

        self.stdout.write(
            self.style.SUCCESS(
                f'Template setup complete. Created: {templates_created}, Updated: {templates_updated}'
            )
        )

    def _create_auth_templates(self, tenant_id: str, overwrite: bool) -> int:
        """Create authentication-related templates"""
        templates = [
            {
                'name': 'User Registration Welcome',
                'channel': ChannelType.EMAIL,
                'content': {
                    'subject': 'Welcome to {{tenant_name}}!',
                    'body': '''
                    Hi {{first_name}},

                    Welcome to {{tenant_name}}! Your account has been successfully created.

                    You can now log in and start exploring our platform.

                    If you have any questions, please don't hesitate to contact our support team.

                    Best regards,
                    The {{tenant_name}} Team
                    '''
                },
                'placeholders': ['first_name', 'tenant_name']
            },
            {
                'name': 'Password Reset',
                'channel': ChannelType.EMAIL,
                'content': {
                    'subject': 'Password Reset Request',
                    'body': '''
                    Hi,

                    We received a request to reset your password for your {{tenant_name}} account.

                    If you made this request, click the link below to reset your password:

                    [Reset Password]({{reset_link}})

                    This link will expire in 1 hour for security reasons.

                    If you didn't request this reset, please ignore this email.

                    Best regards,
                    {{tenant_name}} Security Team
                    '''
                },
                'placeholders': ['tenant_name', 'reset_link']
            },
            {
                'name': 'Login Notification',
                'channel': ChannelType.EMAIL,
                'content': {
                    'subject': 'New Login to Your Account',
                    'body': '''
                    Hi,

                    We noticed a new login to your {{tenant_name}} account.

                    Login Details:
                    - Time: {{login_time}}
                    - Location: {{location}}

                    If this wasn't you, please change your password immediately and contact support.

                    Best regards,
                    {{tenant_name}} Security Team
                    '''
                },
                'placeholders': ['tenant_name', 'login_time', 'location']
            }
        ]

        return self._create_templates(tenant_id, templates, overwrite)

    def _create_app_templates(self, tenant_id: str, overwrite: bool) -> int:
        """Create application-related templates"""
        templates = [
            {
                'name': 'Payment Failed',
                'channel': ChannelType.EMAIL,
                'content': {
                    'subject': 'Payment Failed - Invoice {{invoice_id}}',
                    'body': '''
                    Dear Customer,

                    We're sorry to inform you that your payment for invoice {{invoice_id}} has failed.

                    Amount: {{currency}} {{amount}}
                    Reason: {{failure_reason}}

                    Please update your payment method or contact our billing team to resolve this issue.

                    You can update your payment information in your account settings.

                    Best regards,
                    {{tenant_name}} Billing Team
                    '''
                },
                'placeholders': ['invoice_id', 'currency', 'amount', 'failure_reason', 'tenant_name']
            },
            {
                'name': 'Task Assigned',
                'channel': ChannelType.EMAIL,
                'content': {
                    'subject': 'New Task Assigned: {{task_title}}',
                    'body': '''
                    Hi,

                    A new task has been assigned to you:

                    Task: {{task_title}}
                    Description: {{task_description}}
                    Assigned by: {{assigned_by}}
                    Due Date: {{due_date}}
                    Priority: {{priority}}

                    Please review and complete this task by the due date.

                    [View Task Details]({{task_link}})

                    Best regards,
                    {{tenant_name}} Task Management
                    '''
                },
                'placeholders': ['task_title', 'task_description', 'assigned_by', 'due_date', 'priority', 'task_link', 'tenant_name']
            },
            {
                'name': 'Comment Mention',
                'channel': ChannelType.EMAIL,
                'content': {
                    'subject': 'You were mentioned in a comment',
                    'body': '''
                    Hi,

                    {{author_name}} mentioned you in a comment on {{entity_type}} "{{entity_title}}":

                    "{{comment_text}}"

                    [View Comment]({{comment_link}})

                    Best regards,
                    {{tenant_name}} Team
                    '''
                },
                'placeholders': ['author_name', 'entity_type', 'entity_title', 'comment_text', 'comment_link', 'tenant_name']
            }
        ]

        return self._create_templates(tenant_id, templates, overwrite)

    def _create_security_templates(self, tenant_id: str, overwrite: bool) -> int:
        """Create security-related templates"""
        templates = [
            {
                'name': '2FA Code',
                'channel': ChannelType.EMAIL,
                'content': {
                    'subject': 'Your Login Verification Code - {{tenant_name}}',
                    'body': '''
                    Hi,

                    You requested to log in{{login_domain_text}} with your {{tenant_name}} account.

                    Your verification code is: {{2fa_code}}

                    This code will expire in {{expires_in_seconds}} seconds.

                    If you didn't request this login, please ignore this email.

                    For security reasons, this request was made from IP: {{ip_address}}

                    Best regards,
                    The {{tenant_name}} Security Team
                    '''
                },
                'placeholders': ['tenant_name', 'login_domain_text', '2fa_code', 'expires_in_seconds', 'ip_address']
            },
            {
                'name': '2FA Code',
                'channel': ChannelType.SMS,
                'content': {
                    'body': 'Your {{tenant_name}} verification code is: {{code}}. Expires in 5 minutes.'
                },
                'placeholders': ['tenant_name', 'code']
            },
            {
                'name': 'Security Alert',
                'channel': ChannelType.EMAIL,
                'content': {
                    'subject': 'Security Alert: Suspicious Activity',
                    'body': '''
                    Security Alert!

                    We detected suspicious activity on your {{tenant_name}} account.

                    Details:
                    - Time: {{alert_time}}
                    - Type: {{alert_type}}
                    - Location: {{location}}

                    If this wasn't you, please change your password immediately and enable two-factor authentication.

                    Best regards,
                    {{tenant_name}} Security Team
                    '''
                },
                'placeholders': ['tenant_name', 'alert_time', 'alert_type', 'location']
            }
        ]

        return self._create_templates(tenant_id, templates, overwrite)

    def _create_templates(self, tenant_id: str, templates: list, overwrite: bool) -> int:
        """Create templates in database"""
        created_count = 0

        for template_data in templates:
            # Check if template already exists
            existing = NotificationTemplate.objects.filter(
                tenant_id=tenant_id,
                name=template_data['name'],
                channel=template_data['channel']
            ).first()

            if existing and not overwrite:
                continue

            # Create or update template
            template, created = NotificationTemplate.objects.update_or_create(
                tenant_id=tenant_id,
                name=template_data['name'],
                channel=template_data['channel'],
                defaults={
                    'content': template_data['content'],
                    'placeholders': template_data['placeholders'],
                    'is_active': True,
                    'version': 1
                }
            )

            if created:
                created_count += 1
                self.stdout.write(f'Created template: {template_data["name"]}')

        return created_count

    def _update_auth_templates(self, tenant_id: str, overwrite: bool) -> int:
        """Update existing auth templates if needed"""
        return 0  # No updates needed for now

    def _update_app_templates(self, tenant_id: str, overwrite: bool) -> int:
        """Update existing app templates if needed"""
        return 0  # No updates needed for now

    def _update_security_templates(self, tenant_id: str, overwrite: bool) -> int:
        """Update existing security templates if needed"""
        updated_count = 0

        # Update 2FA Code template to fix login domain text for all tenants
        all_templates = NotificationTemplate.objects.filter(
            name='2FA Code',
            channel=ChannelType.EMAIL
        )

        for template in all_templates:
            try:
                # Check if the template has the old incorrect format
                current_body = template.content.get('body', '')
                if 'log in to login' in current_body:
                    # Fix the template body
                    corrected_body = current_body.replace(
                        'You requested to log in to login{{login_domain_text}} with your {{tenant_name}} account.',
                        'You requested to log in{{login_domain_text}} with your {{tenant_name}} account.'
                    )

                    if corrected_body != current_body:
                        template.content['body'] = corrected_body
                        template.version += 1
                        template.save()
                        updated_count += 1
                        self.stdout.write(f'Updated 2FA Code template for tenant: {template.tenant_id}')

            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error updating 2FA template for tenant {template.tenant_id}: {str(e)}'))

        return updated_count