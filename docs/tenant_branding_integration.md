# Tenant Branding Integration

This document explains how the Notification Service integrates with the Auth Service to fetch tenant branding information and apply it to email templates.

## Overview

The notification service authenticates with the Auth Service to retrieve tenant-specific branding information including:
- Tenant name
- Logo URL
- Primary and secondary colors
- Email configuration
- Company information

This branding is automatically applied to all email templates for a professional, branded experience.

## Architecture

```
Notification Service                    Auth Service
        │                                   │
        │  1. Event Received                 │
        │  ────────────────────────────────▶ │
        │                                   │
        │  2. Fetch Tenant Branding         │
        │  ◀─────────────────────────────── │
        │                                   │
        │  3. Apply Branding to Template    │
        │  ────────────────────────────────▶ │
        │                                   │
        │  4. Send Branded Email            │
        └─────────────────┬─────────────────┘
                          │
                          ▼
                    Email Recipient
```

## Auth Service Integration

### Service Client
Located in `notifications/services/auth_service.py`

```python
class AuthServiceClient:
    def get_tenant_branding(self, tenant_id: str, token: Optional[str] = None) -> Dict[str, Any]:
        # Fetches tenant details from auth service
        # Returns branding information
```

### Configuration
Add to your `.env` file:
```env
AUTH_SERVICE_URL=http://auth-service:8001
AUTH_SERVICE_TIMEOUT=10
```

## Branding Data Structure

The auth service returns the following branding information:

```json
{
  "name": "Acme Corporation",
  "logo_url": "https://cdn.example.com/logos/acme.png",
  "primary_color": "#FF0000",
  "secondary_color": "#FADBD8",
  "email_from": "noreply@acme.com",
  "about_us": "Leading provider of business solutions...",
  "status": "active"
}
```

## Email Template Branding

### HTML Email Structure
All emails now include:
- Tenant logo in header
- Primary color for headings and accents
- Secondary color for highlights
- Professional footer with tenant information
- Responsive design

### Template Variables
The following variables are automatically added to email contexts:
- `{{tenant_name}}` - Company name
- `{{tenant_logo}}` - Logo URL
- `{{primary_color}}` - Primary brand color
- `{{secondary_color}}` - Secondary brand color
- `{{company_name}}` - Alias for tenant_name

## Implementation Details

### Email Handler Updates
The `EmailHandler` class has been enhanced with:

```python
class EmailHandler(BaseHandler):
    def _get_tenant_branding(self):
        # Fetches and caches tenant branding

    def _render_html_template(self, content: dict, context: dict):
        # Creates branded HTML email with tenant colors and logo
```

### Event Handler Updates
All event handlers now include tenant branding in their templates:

```python
def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'subject': 'Welcome to {{tenant_name}}, {{first_name}}!',
        'body': 'Welcome to {{tenant_name}}! ...'
    }
```

## Setup Instructions

### 1. Environment Configuration
```env
# Auth Service Connection
AUTH_SERVICE_URL=http://auth-service:8001
AUTH_SERVICE_TIMEOUT=10

# Optional SSL Configuration
KAFKA_SSL_CA=/path/to/ca.pem
KAFKA_SSL_CERT=/path/to/client.pem
KAFKA_SSL_KEY=/path/to/client.key
```

### 2. Service Dependencies
Ensure the notification service can reach the auth service:
```yaml
# docker-compose.yml
services:
  notifications-service:
    depends_on:
      - auth-service
    environment:
      - AUTH_SERVICE_URL=http://auth-service:8001
```

### 3. Test Branding Integration
```python
# Test from Django shell
from notifications.services.auth_service import auth_service_client

branding = auth_service_client.get_tenant_branding('your-tenant-uuid')
print(branding)
```

## Email Template Examples

### Welcome Email (Branded)
```html
<!DOCTYPE html>
<html>
<head>
    <style>
        .header { border-bottom: 3px solid #FF0000; }
        h1 { color: #FF0000; }
        .button { background-color: #FF0000; }
    </style>
</head>
<body>
    <div class="header">
        <img src="https://cdn.example.com/logos/acme.png" alt="Acme Corporation">
        <h1>Acme Corporation</h1>
    </div>

    <p>Welcome to Acme Corporation, John!</p>

    <a href="#" class="button">Get Started</a>

    <div class="footer">
        <p>This email was sent by Acme Corporation</p>
        <p>Leading provider of business solutions since 1995</p>
    </div>
</body>
</html>
```

## Error Handling

### Network Failures
- Automatic retry with exponential backoff
- Fallback to default branding if auth service unavailable
- Logging of branding fetch failures

### Invalid Branding Data
- Validation of hex color codes
- Fallback to default colors
- Graceful handling of missing logo URLs

## Caching Strategy

### Branding Cache
- Tenant branding is cached per handler instance
- Reduces API calls to auth service
- Cache invalidation on service restart

### Performance Considerations
- HTTP connection pooling
- Request timeouts
- Circuit breaker pattern for auth service failures

## Security Considerations

### Authentication
- JWT token validation for tenant access
- Secure communication with auth service
- Encrypted credential storage

### Data Privacy
- Tenant branding data cached temporarily
- No sensitive information stored in notifications
- Compliant with data protection regulations

## Monitoring & Analytics

### Branding Metrics
- Branding fetch success/failure rates
- Template rendering performance
- Email delivery analytics by tenant

### Logging
```python
# Branding fetch logs
logger.info(f"Fetched branding for tenant {tenant_id}")

# Template rendering logs
logger.debug(f"Rendered branded email for {event_type}")
```

## Troubleshooting

### Common Issues

**Branding Not Applied**
```bash
# Check auth service connectivity
curl http://auth-service:8001/api/tenants/{tenant_id}/

# Verify tenant has branding data
# Check notification service logs
```

**Invalid Colors**
```bash
# Validate hex color format in auth service
# Check for leading # in color codes
```

**Logo Not Displaying**
```bash
# Verify logo URL is accessible
# Check CORS settings for logo domain
# Ensure HTTPS URLs for production
```

## Future Enhancements

### Advanced Branding
- Custom email templates per tenant
- Multiple logo variants (header, footer)
- Brand-specific fonts and typography
- Dynamic color schemes

### Performance Optimizations
- Redis caching for branding data
- CDN integration for logo assets
- Background branding updates

### Analytics Integration
- Brand performance metrics
- A/B testing for email designs
- User engagement tracking

## API Reference

### Get Tenant Branding
```python
branding = auth_service_client.get_tenant_branding(tenant_id, token)
```

**Parameters:**
- `tenant_id` (str): UUID of the tenant
- `token` (str, optional): JWT token for authentication

**Returns:**
```python
{
    'name': str,
    'logo_url': str,
    'primary_color': str,  # Hex color
    'secondary_color': str,  # Hex color
    'email_from': str,
    'about_us': str,
    'status': str
}
```

This integration ensures all tenant communications maintain brand consistency and professional appearance across all notification channels.