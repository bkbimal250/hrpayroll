"""
Database Connection Manager with retry logic and connection pooling.
This helps manage database connections more efficiently and handle connection limits.
"""

import time
import logging
from django.db import connections
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    """
    Manages database connections with retry logic and connection monitoring.
    """
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.connection_timeout = 30
        
    def get_connection(self, alias='default'):
        """
        Get a database connection with retry logic.
        """
        for attempt in range(self.max_retries):
            try:
                connection = connections[alias]
                # Test the connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                logger.info(f"Database connection successful (attempt {attempt + 1})")
                return connection
                
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"All database connection attempts failed: {e}")
                    raise e
    
    def close_all_connections(self):
        """
        Close all database connections to free up resources.
        """
        try:
            for alias in connections:
                connections[alias].close()
            logger.info("All database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
    
    def get_connection_info(self):
        """
        Get information about current database connections.
        """
        info = {}
        for alias in connections:
            connection = connections[alias]
            info[alias] = {
                'connected': connection.connection is not None,
                'vendor': connection.vendor,
                'settings': {
                    'host': connection.settings_dict.get('HOST', 'N/A'),
                    'port': connection.settings_dict.get('PORT', 'N/A'),
                    'name': connection.settings_dict.get('NAME', 'N/A'),
                }
            }
        return info

# Global instance
db_manager = DatabaseConnectionManager()

def reset_database_connections():
    """
    Reset all database connections.
    Call this function when you encounter connection limit issues.
    """
    logger.info("Resetting database connections...")
    db_manager.close_all_connections()
    time.sleep(2)  # Wait a bit before reconnecting
    logger.info("Database connections reset complete")

def get_database_status():
    """
    Get the current status of database connections.
    """
    return db_manager.get_connection_info()
