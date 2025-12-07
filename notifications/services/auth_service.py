import requests
import logging
from django.conf import settings
from typing import Optional, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger('notifications.auth_service')

class AuthServiceClient:
    """Client for communicating with the Auth Service"""

    def __init__(self):
        self.base_url = settings.AUTH_SERVICE_URL.rstrip('/')
        self.timeout = getattr(settings, 'AUTH_SERVICE_TIMEOUT', 10)

        # Setup retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get_headers(self, tenant_token: Optional[str] = None) -> Dict[str, str]:
        """Get headers for auth service requests"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'NotificationService/1.0'
        }

        if tenant_token:
            headers['Authorization'] = f'Bearer {tenant_token}'

        return headers

    def get_tenant_details(self, tenant_id: str, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch tenant details from auth service

        Args:
            tenant_id: UUID of the tenant
            token: Optional JWT token for authentication

        Returns:
            Tenant details dict or None if not found/error
        """
        try:
            url = f"{self.base_url}/api/tenants/{tenant_id}/"
            headers = self._get_headers(token)

            logger.info(f"Fetching tenant details for {tenant_id}")
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            tenant_data = response.json()
            logger.info(f"Successfully fetched tenant details for {tenant_id}")
            return tenant_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch tenant details for {tenant_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching tenant {tenant_id}: {str(e)}")
            return None

    def validate_tenant_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate JWT token and extract tenant information

        Args:
            token: JWT token to validate

        Returns:
            Token payload with tenant info or None if invalid
        """
        try:
            url = f"{self.base_url}/api/token/verify/"
            headers = self._get_headers()
            data = {'token': token}

            response = self.session.post(url, headers=headers, json=data, timeout=self.timeout)
            response.raise_for_status()

            token_data = response.json()
            logger.debug("Token validated successfully")
            return token_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Token validation failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error validating token: {str(e)}")
            return None

    def get_tenant_branding(self, tenant_id: str, token: Optional[str] = None) -> Dict[str, Any]:
        """
        Get tenant branding information for email templates

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Branding dict with name, logo, colors, etc.
        """
        tenant_details = self.get_tenant_details(tenant_id, token)

        if not tenant_details:
            # Return default branding
            return {
                'name': 'Default Company',
                'logo_url': None,
                'primary_color': '#FF0000',
                'secondary_color': '#FADBD8',
                'email_from': 'noreply@default.com'
            }

        return {
            'name': tenant_details.get('name', 'Company'),
            'logo_url': tenant_details.get('logo'),
            'primary_color': tenant_details.get('primary_color', '#FF0000'),
            'secondary_color': tenant_details.get('secondary_color', '#FADBD8'),
            'email_from': tenant_details.get('default_from_email', f'noreply@{tenant_details.get("name", "company").lower()}.com'),
            'about_us': tenant_details.get('about_us', ''),
            'status': tenant_details.get('status', 'active')
        }


# Global client instance
auth_service_client = AuthServiceClient()