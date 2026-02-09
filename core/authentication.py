"""
Custom authentication classes for the Attendance System
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that skips authentication for login/register endpoints
    """
    
    def authenticate(self, request):
        # Skip JWT authentication for login and register endpoints
        if request.path in ['/api/auth/login/', '/api/auth/register/']:
            return None
        
        # For all other endpoints, use the standard JWT authentication
        try:
            return super().authenticate(request)
        except InvalidToken:
            # Log the invalid token error but don't raise it for login/register
            if request.path in ['/api/auth/login/', '/api/auth/register/']:
                return None
            raise
