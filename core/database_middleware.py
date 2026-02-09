"""
Database connection middleware to handle connection issues
"""
import logging
from django.db import connection, transaction
from django.http import JsonResponse
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

class DatabaseConnectionMiddleware:
    """
    Middleware to handle database connection issues
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process request
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """
        Handle database connection exceptions
        """
        # Check if it's a database connection error
        if hasattr(exception, 'args') and len(exception.args) > 0:
            error_code = exception.args[0] if isinstance(exception.args[0], int) else None
            
            # MySQL connection errors
            if error_code in [2006, 2013, 2003]:  # MySQL server has gone away, Lost connection, Can't connect
                logger.warning(f"Database connection error {error_code}: {exception}")
                
                try:
                    # Close the connection
                    connection.close()
                    logger.info("Closed stale database connection")
                    
                    # Return a retry response for API requests
                    if request.path.startswith('/api/'):
                        return JsonResponse({
                            'error': 'Database connection lost. Please retry.',
                            'retry': True,
                            'error_code': error_code
                        }, status=503)
                    
                except Exception as e:
                    logger.error(f"Error handling database connection: {e}")
        
        return None

class DatabaseHealthCheckMiddleware:
    """
    Middleware to perform database health checks
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Perform health check for API requests
        if request.path.startswith('/api/'):
            try:
                # Quick health check
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            except Exception as e:
                logger.warning(f"Database health check failed: {e}")
                # Close and retry connection
                try:
                    connection.close()
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                    logger.info("Database connection recovered")
                except Exception as e2:
                    logger.error(f"Database connection recovery failed: {e2}")
                    if request.path.startswith('/api/'):
                        return JsonResponse({
                            'error': 'Database temporarily unavailable',
                            'retry': True
                        }, status=503)
        
        response = self.get_response(request)
        return response
