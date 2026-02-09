"""
Custom permissions for the Employee Attendance System
"""

from rest_framework import permissions


class IsAdminOrManager(permissions.BasePermission):
    """
    Custom permission to only allow admins and managers to access.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'manager']
        )


class IsAdminOrManagerOrAccountant(permissions.BasePermission):
    """
    Custom permission to only allow admins, managers, and accountants to access.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'manager', 'accountant']
        )


class IsAdminOrManagerOrEmployee(permissions.BasePermission):
    """
    Custom permission to allow admins, managers, and employees to access.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'manager', 'employee']
        )


class IsAdminOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to access.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )


class IsManagerOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow managers and admins to access.
    Managers can only access data for their office.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'manager']
        )
    
    def has_object_permission(self, request, view, obj):
        # Admin can access all objects
        if request.user.role == 'admin':
            return True
        
        # Manager can only access objects for their office
        if request.user.role == 'manager':
            if hasattr(obj, 'office') and obj.office:
                return obj.office == request.user.office
            elif hasattr(obj, 'employee') and obj.employee.office:
                return obj.employee.office == request.user.office
            elif hasattr(obj, 'user') and obj.user.office:
                return obj.user.office == request.user.office
        
        return False


class IsEmployeeOrManagerOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow employees, managers, and admins to access.
    Employees can only access their own data.
    Managers can access data for their office.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'manager', 'employee']
        )
    
    def has_object_permission(self, request, view, obj):
        # Admin can access all objects
        if request.user.role == 'admin':
            return True
        
        # Manager can access objects for their office
        if request.user.role == 'manager':
            if hasattr(obj, 'office') and obj.office:
                return obj.office == request.user.office
            elif hasattr(obj, 'employee') and obj.employee.office:
                return obj.employee.office == request.user.office
            elif hasattr(obj, 'user') and obj.user.office:
                return obj.user.office == request.user.office
        
        # Employee can only access their own data
        if request.user.role == 'employee':
            if hasattr(obj, 'employee') and obj.employee:
                return obj.employee == request.user
            elif hasattr(obj, 'user') and obj.user:
                return obj.user == request.user
            elif hasattr(obj, 'id'):
                return obj.id == request.user.id
        
        return False


class IsEmployeeSalaryAccess(permissions.BasePermission):
    """
    Custom permission for salary-related views.
    Allows employees to view their own salary, managers to view office salaries,
    accountants to view all salaries, and admins to view all salaries.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'manager', 'employee', 'accountant']
        )
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Admin can access all salaries
        if user.role == 'admin':
            return True
            
        # Accountant can access all salaries
        if user.role == 'accountant':
            return True
        
        # Manager can access salaries for their office
        if user.role == 'manager':
            if hasattr(obj, 'employee') and obj.employee:
                return obj.employee.office == user.office
        
        # Employee can only access their own salary
        if user.role == 'employee':
            if hasattr(obj, 'employee') and obj.employee:
                return obj.employee == user
            elif hasattr(obj, 'id'):
                return obj.id == user.id
        
        return False


class IsOfficeManagerOrAdmin(permissions.BasePermission):
    """
    Custom permission for office-specific access.
    Managers can only access data for their office.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'manager']
        )
    
    def has_object_permission(self, request, view, obj):
        # Admin can access all objects
        if request.user.role == 'admin':
            return True
        
        # Manager can only access objects for their office
        if request.user.role == 'manager' and request.user.office:
            if hasattr(obj, 'office') and obj.office:
                return obj.office == request.user.office
            elif hasattr(obj, 'employee') and obj.employee.office:
                return obj.employee.office == request.user.office
            elif hasattr(obj, 'user') and obj.user.office:
                return obj.user.office == request.user.office
        
        return False
