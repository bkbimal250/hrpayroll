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
    """Lightweight API auth logging without sensitive headers."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/api/') and response.status_code == 401:
            logger.info("API auth rejected: %s %s", request.method, request.path)
        
        return response

class GlobalCSPMiddleware:
    """Middleware to set Content Security Policy (CSP) headers globally.
    
    This includes:
    - wss: and ws: in connect-src for WebSockets (Channels).
    - permissive CSP for admin panel to allow Alpine.js (unsafe-eval).
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Base CSP for general application
        # Includes ws: and wss: in connect-src for WebSockets
        csp_policy = (
            "default-src 'self' https: http: data: blob:; "
            "script-src 'self' https: http: 'unsafe-inline'; "
            "style-src 'self' https: http: 'unsafe-inline'; "
            "img-src 'self' data: https: http: blob:; "
            "font-src 'self' data: https: http:; "
            "connect-src 'self' https: http: ws: wss:; "
            "frame-ancestors 'self';"
        )
        
        # Override for admin panel to allow Alpine.js (needs unsafe-eval)
        if request.path.startswith('/admin/'):
            csp_policy = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https: http:; "
                "style-src 'self' 'unsafe-inline' https: http:; "
                "img-src 'self' data: https: http: blob:; "
                "font-src 'self' data: https: http:; "
                "connect-src 'self' https: http: ws: wss:; "
                "frame-ancestors 'self';"
            )
            
        response['Content-Security-Policy'] = csp_policy
        return response
