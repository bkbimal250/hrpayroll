#!/usr/bin/env python3
"""
Database Connection Manager
Manages database connections efficiently to prevent max_connections_per_hour errors
"""

import logging
import time
import threading
from contextlib import contextmanager
from django.db import connection, connections, close_old_connections
from django.conf import settings

logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    """Manages database connections efficiently"""
    
    def __init__(self):
        self.connection_count = 0
        self.max_connections = 30  # Conservative limit for shared hosting
        self.connection_times = []
        self._lock = threading.Lock()
        
    def get_connection_status(self):
        """Get current connection status"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
                result = cursor.fetchone()
                return int(result[1]) if result else 0
        except Exception as e:
            logger.error(f"Error getting connection status: {e}")
            return 0
    
    def check_connection_health(self):
        """Check if database connection is healthy"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database connection health check failed: {e}")
            return False
    
    def close_idle_connections(self):
        """Close idle database connections"""
        try:
            with self._lock:
                # Use Django's built-in function to close old connections
                close_old_connections()
                
                # Also close Django's default connection if it's been open too long
                if hasattr(connection, 'connection') and connection.connection:
                    connection.close()
                    
            logger.info("Closed idle database connections")
        except Exception as e:
            logger.error(f"Error closing idle connections: {e}")
    
    @contextmanager
    def managed_connection(self):
        """Context manager for database connections"""
        start_time = time.time()
        try:
            # Close old connections before starting
            close_old_connections()
            
            # Check connection health before use
            if not self.check_connection_health():
                self.close_idle_connections()
                close_old_connections()
            
            yield connection
            
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            # Close connections after use
            close_old_connections()
            
            # Log connection usage
            duration = time.time() - start_time
            if duration > 5:  # Log slow queries
                logger.warning(f"Slow database operation: {duration:.2f}s")
    
    def optimize_connections(self):
        """Optimize database connections"""
        try:
            current_connections = self.get_connection_status()
            logger.info(f"Current database connections: {current_connections}")
            
            if current_connections > self.max_connections * 0.7:  # 70% threshold
                logger.warning(f"High connection count detected: {current_connections}")
                self.close_idle_connections()
        except Exception as e:
            logger.error(f"Error optimizing connections: {e}")
    
    def reset_connections(self):
        """Reset all database connections"""
        try:
            with self._lock:
                close_old_connections()
                
                # Close all connections
                for conn_name in connections.databases:
                    conn = connections[conn_name]
                    if hasattr(conn, 'connection') and conn.connection:
                        conn.close()
                        
            logger.info("Reset all database connections")
        except Exception as e:
            logger.error(f"Error resetting connections: {e}")

# Global instance
db_manager = DatabaseConnectionManager()

def get_db_manager():
    """Get the global database manager instance"""
    return db_manager

# Decorator for database operations
def with_db_connection(func):
    """Decorator to manage database connections"""
    def wrapper(*args, **kwargs):
        with db_manager.managed_connection():
            return func(*args, **kwargs)
    return wrapper

# Utility function to close connections
def close_db_connections():
    """Close all database connections"""
    db_manager.close_idle_connections()
