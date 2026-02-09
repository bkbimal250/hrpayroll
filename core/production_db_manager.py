"""
Production-safe database connection manager.
This handles connection limits without affecting live data.
"""

import time
import logging
from django.db import connections
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

logger = logging.getLogger(__name__)

class ProductionDBManager:
    """
    Production-safe database connection manager.
    Handles connection limits without affecting live data.
    """
    
    def __init__(self):
        self.max_retries = 2  # Reduced for production
        self.retry_delay = 10  # Longer delay for production
        self.connection_timeout = 30
        
    def safe_connection_test(self):
        """
        Safely test database connection without affecting production data.
        """
        try:
            connection = connections['default']
            with connection.cursor() as cursor:
                # Simple test query that doesn't affect data
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                if result and result[0] == 1:
                    logger.info(" Database connection test successful")
                    return True
                else:
                    logger.error(" Database connection test failed")
                    return False
        except Exception as e:
            logger.error(f" Database connection test error: {e}")
            return False
    
    def get_connection_status(self):
        """
        Get current connection status without making new connections.
        """
        try:
            connection = connections['default']
            return {
                'connected': connection.connection is not None,
                'vendor': connection.vendor,
                'host': connection.settings_dict.get('HOST', 'N/A'),
                'port': connection.settings_dict.get('PORT', 'N/A'),
                'database': connection.settings_dict.get('NAME', 'N/A'),
            }
        except Exception as e:
            logger.error(f"Error getting connection status: {e}")
            return {'connected': False, 'error': str(e)}
    
    def wait_for_connection_reset(self, max_wait_minutes=60):
        """
        Wait for connection limit to reset (production-safe).
        """
        logger.info("⏳ Waiting for database connection limit to reset...")
        
        for minute in range(max_wait_minutes):
            if self.safe_connection_test():
                logger.info(f" Connection available after {minute} minutes")
                return True
            
            if minute < max_wait_minutes - 1:
                logger.info(f"⏳ Still waiting... ({minute + 1}/{max_wait_minutes} minutes)")
                time.sleep(60)  # Wait 1 minute
        
        logger.error(" Connection limit not reset within timeout period")
        return False

# Global instance
production_db_manager = ProductionDBManager()

def check_production_db_health():
    """
    Check production database health without affecting data.
    """
    return production_db_manager.safe_connection_test()

def get_production_db_status():
    """
    Get production database status.
    """
    return production_db_manager.get_connection_status()
