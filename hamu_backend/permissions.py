"""
Custom authentication helpers for hamu_backend.
"""

from rest_framework import permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
import logging

# Set up logger
logger = logging.getLogger(__name__)

class IsDirector(permissions.BasePermission):
    """
    Custom permission to allow only directors to access an object.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_class == 'Director'


class IsShopAgentOrDirector(permissions.BasePermission):
    """
    Custom permission to only allow shop agents or directors to access the view.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Directors have full access
        if request.user.user_class == 'Director':
            return True
        
        # Shop agents can only access their own shop's data
        return request.user.user_class == 'Agent'
        
    def has_object_permission(self, request, view, obj):
        # Directors have full access
        if request.user.user_class == 'Director':
            return True
            
        # Shop agents can only access their own shop's data
        if hasattr(obj, 'shop'):
            return obj.shop == request.user.shop
        elif hasattr(obj, 'shop_id'):
            return obj.shop_id == request.user.shop_id
        
        # If we can't determine shop association, deny access
        return False


class FlexibleJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication class that handles multiple header formats:
    - Bearer token
    - Token token
    - JWT token
    - Raw token
    """
    
    def get_header(self, request):
        """
        Extracts the header containing the JWT from the given request.
        This method is more flexible than the default implementation,
        supporting multiple token prefix formats.
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        logger.debug(f"Original Authorization header: {auth_header}")
        
        if not auth_header:
            logger.warning("No Authorization header found in request")
            return None
            
        # Convert header to string if needed
        if isinstance(auth_header, bytes):
            auth_header = auth_header.decode('utf-8')
        
        # Handle different token formats
        if auth_header.startswith('Bearer '):
            logger.debug("Found Bearer token format")
            return auth_header.encode()
        elif auth_header.startswith('Token '):
            # Convert 'Token xxx' to 'Bearer xxx'
            logger.debug("Converting Token format to Bearer format")
            raw_token = auth_header[6:]
            return f'Bearer {raw_token}'.encode()
        elif auth_header.startswith('JWT '):
            # Convert 'JWT xxx' to 'Bearer xxx'
            logger.debug("Converting JWT format to Bearer format")
            raw_token = auth_header[4:]
            return f'Bearer {raw_token}'.encode()
        elif ' ' not in auth_header:
            # Assume it's a raw token without prefix
            logger.debug("Found raw token without prefix, adding Bearer prefix")
            return f'Bearer {auth_header}'.encode()
            
        logger.debug(f"Using header as is: {auth_header}")
        return auth_header.encode()
            
    def authenticate(self, request):
        try:
            result = super().authenticate(request)
            if result:
                user, token = result
                # Using string formatting with user object which will call __str__ method
                logger.debug(f"Successfully authenticated user: {user}")
            else:
                logger.warning("Authentication returned None")
            return result
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None