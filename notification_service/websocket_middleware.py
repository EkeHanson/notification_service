import jwt
import requests
import logging
import urllib.parse
from django.conf import settings
from channels.db import database_sync_to_async

logger = logging.getLogger('notifications.websocket')

class WebSocketJWTMiddleware:
    """
    WebSocket JWT authentication middleware for Notification microservice
    Extracts tenant_id and user_id from JWT token in query string
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Extract token from query string
        query_string = scope.get("query_string", b"").decode()
        token = None

        # Parse query parameters
        for param in query_string.split('&'):
            if param.startswith('token='):
                token = urllib.parse.unquote(param.split('=', 1)[1])
                break

        if token:
            try:
                # Validate token and extract user info
                auth_data = await self.authenticate_token(token)
                scope['user'] = auth_data['user']
                scope['tenant_id'] = auth_data['tenant_id']
                scope['user_id'] = auth_data['user_id']
                scope['jwt_payload'] = auth_data['jwt_payload']
            except Exception as e:
                logger.warning(f"WebSocket authentication failed: {str(e)}")
                from django.contrib.auth.models import AnonymousUser
                scope['user'] = AnonymousUser()
                scope['tenant_id'] = None
                scope['user_id'] = None
                scope['jwt_payload'] = None
        else:
            logger.warning("No token provided in WebSocket connection")
            from django.contrib.auth.models import AnonymousUser
            scope['user'] = AnonymousUser()
            scope['tenant_id'] = None
            scope['user_id'] = None
            scope['jwt_payload'] = None

        return await self.app(scope, receive, send)

    @database_sync_to_async
    def authenticate_token(self, token):
        """
        Validate JWT token and extract user/tenant information
        """
        try:
            # Decode header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            alg = unverified_header.get("alg")

            if not kid:
                raise ValueError("No 'kid' in token header")

            if alg != "RS256":
                raise ValueError(f"Unsupported algorithm: {alg}")

            # Get unverified payload for tenant info
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            tenant_id = unverified_payload.get("tenant_id")
            tenant_unique_id = unverified_payload.get("tenant_unique_id")

            # Fetch public key from auth service
            resp = requests.get(
                f"{settings.AUTH_SERVICE_URL}/api/public-key/{kid}/?tenant_id={tenant_id}",
                headers={'Authorization': f'Bearer {token}'},
                timeout=5
            )

            if resp.status_code != 200:
                raise ValueError(f"Could not fetch public key: {resp.status_code}")

            public_key_data = resp.json()
            public_key = public_key_data.get("public_key")
            if not public_key:
                raise ValueError("No public key in response")

            # Verify and decode token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={"verify_aud": False}
            )

            # Create user object
            from notification_service.middleware import SimpleUser
            user = SimpleUser(payload)

            return {
                'user': user,
                'tenant_id': tenant_unique_id,  # UUID for tenant identification
                'user_id': payload.get('user', {}).get('id'),  # User UUID
                'jwt_payload': payload
            }

        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
        except requests.RequestException as e:
            raise ValueError(f"Auth service unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"WebSocket token validation error: {str(e)}")
            raise ValueError(f"Authentication failed: {str(e)}")