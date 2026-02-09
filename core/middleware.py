#!/usr/bin/env python3
"""
Custom Middleware for the Attendance System
"""

import logging
import time
from django.db import close_old_connections
from core.db_manager import db_manager
from django.http import HttpResponsePermanentRedirect
from django.conf import settings

logger = logging.getLogger(__name__)

class DatabaseConnectionMiddleware:
    """Database connection management middleware"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Close old connections before processing request
        close_old_connections()
        
        start_time = time.time()
        
        # Process the request
        response = self.get_response(request)
        
        # Close connections after processing request
        close_old_connections()
        
        # Log slow requests
        duration = time.time() - start_time
        if duration > 5:  # Log requests taking more than 5 seconds
            logger.warning(f"Slow request: {request.path} took {duration:.2f}s")
        
        return response
    
    def process_exception(self, request, exception):
        """Handle exceptions and ensure connections are closed"""
        logger.error(f"Exception in request {request.path}: {str(exception)}")
        
        # Check for MySQL connection errors
        if hasattr(exception, 'args') and len(exception.args) > 0:
            error_code = exception.args[0] if isinstance(exception.args[0], int) else None
            
            # MySQL connection errors (2006: MySQL server has gone away, 2013: Lost connection)
            if error_code in [2006, 2013, 2003]:
                logger.warning(f"MySQL connection error {error_code}: {exception}")
                try:
                    from django.db import connection
                    connection.close()
                    logger.info("Closed stale MySQL connection")
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
        
        close_old_connections()
        return None

class DisableTrailingSlashMiddleware:
    """Middleware to handle trailing slashes in URLs"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Check if the URL ends with a slash (except for root URL)
        if request.path != '/' and request.path.endswith('/'):
            # Remove trailing slash and redirect
            new_path = request.path.rstrip('/')
            # Preserve query parameters
            if request.GET:
                query_string = request.GET.urlencode()
                new_path = f"{new_path}?{query_string}"
            
            logger.info(f"Redirecting from {request.path} to {new_path}")
            return HttpResponsePermanentRedirect(new_path)
        
        response = self.get_response(request)
        return response

class APIAuthenticationDebugMiddleware:
    """Middleware to debug API authentication issues"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip authentication debug for login/register endpoints
        if request.path.startswith('/api/') and not request.path in ['/api/auth/login/', '/api/auth/register/']:
            logger.debug(f"API Request: {request.method} {request.path}")
            logger.debug(f"Authorization Header: {request.headers.get('Authorization', 'Not present')}")
            logger.debug(f"HTTP_AUTHORIZATION: {request.META.get('HTTP_AUTHORIZATION', 'Not present')}")
            logger.debug(f"All Headers: {dict(request.headers)}")
        
        response = self.get_response(request)
        
        # Debug response for API requests (except login/register)
        if request.path.startswith('/api/') and not request.path in ['/api/auth/login/', '/api/auth/register/']:
            logger.debug(f"API Response: {response.status_code} for {request.path}")
        
        return response

class AdminCSPMiddleware:
    """Middleware to set permissive CSP headers for Django admin panel
    
    This allows Alpine.js (used by django-unfold) to work properly by
    allowing 'unsafe-eval' for the admin panel only.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Only apply CSP override for admin URLs
        if request.path.startswith('/admin/'):
            # Set permissive CSP for admin panel to allow Alpine.js
            # This allows 'unsafe-eval' which Alpine.js needs for dynamic evaluation
            csp_policy = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https: http:; "
                "style-src 'self' 'unsafe-inline' https: http:; "
                "img-src 'self' data: https: http: blob:; "
                "font-src 'self' data: https: http:; "
                "connect-src 'self' https: http:; "
                "frame-ancestors 'self';"
            )
            response['Content-Security-Policy'] = csp_policy
        
        return response