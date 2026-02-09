"""
Custom exception handlers for the Employee Attendance System
"""

import logging
import traceback
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)


class AttendanceSystemException(APIException):
    """Base exception for Attendance System"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'An error occurred in the attendance system.'
    default_code = 'attendance_system_error'


class DatabaseConnectionException(AttendanceSystemException):
    """Exception for database connection issues"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Database connection failed. Please try again later.'
    default_code = 'database_connection_error'


class DeviceConnectionException(AttendanceSystemException):
    """Exception for device connection issues"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Device connection failed. Please check device status.'
    default_code = 'device_connection_error'


class AttendanceFetchException(AttendanceSystemException):
    """Exception for attendance fetching issues"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'Failed to fetch attendance data.'
    default_code = 'attendance_fetch_error'


class ValidationException(AttendanceSystemException):
    """Exception for validation errors"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Validation error occurred.'
    default_code = 'validation_error'


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # Get the request and view info
    request = context.get('request')
    view = context.get('view')
    
    # Log the exception
    logger.error(f"Exception in {view.__class__.__name__ if view else 'Unknown'}: {str(exc)}")
    logger.error(f"Request: {request.method} {request.path if request else 'Unknown'}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    if response is not None:
        # Customize the error response
        message = 'An error occurred'
        if isinstance(response.data, dict):
            message = response.data.get('detail', 'An error occurred')
        elif isinstance(response.data, list) and response.data and isinstance(response.data[0], str):
             message = response.data[0]
            
        custom_response_data = {
            'error': True,
            'message': message,
            'status_code': response.status_code,
            'timestamp': timezone.now().isoformat(),
        }
        
        # Add field-specific errors if available
        if isinstance(response.data, dict):
            if 'detail' not in response.data:
                custom_response_data['errors'] = response.data
            else:
                custom_response_data['detail'] = response.data['detail']
        elif isinstance(response.data, list):
            # Handle list of errors (e.g. from validators)
            if response.data:
                if isinstance(response.data[0], str):
                    custom_response_data['detail'] = response.data[0]
                else:
                    custom_response_data['errors'] = response.data
            else:
                custom_response_data['detail'] = "Validation error"
        else:
            # Handle string or other types
            custom_response_data['detail'] = str(response.data)
        
        response.data = custom_response_data
    
    return response


def handle_database_error(func):
    """
    Decorator to handle database errors
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except IntegrityError as e:
            logger.error(f"Database integrity error in {func.__name__}: {str(e)}")
            raise ValidationException(f"Data integrity error: {str(e)}")
        except Exception as e:
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            raise DatabaseConnectionException(f"Database error: {str(e)}")
    return wrapper


def handle_device_error(func):
    """
    Decorator to handle device connection errors
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Device error in {func.__name__}: {str(e)}")
            raise DeviceConnectionException(f"Device error: {str(e)}")
    return wrapper


def safe_api_call(func):
    """
    Decorator for safe API calls with proper error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.error(f"Validation error in {func.__name__}: {str(e)}")
            raise ValidationException(f"Validation error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise AttendanceSystemException(f"Unexpected error: {str(e)}")
    return wrapper
