"""
Custom permissions for the Employee Attendance System
"""

from rest_framework import permissions


PRIVILEGED_HR_ROLES = {'admin', 'hr'}
PAYROLL_ROLES = {'admin', 'accountant'}
MANAGEMENT_ROLES = {'admin', 'hr', 'manager'}


def is_admin(user):
    return bool(user and user.is_authenticated and getattr(user, 'role', None) == 'admin')


def is_hr_or_admin(user):
    return bool(user and user.is_authenticated and getattr(user, 'role', None) in PRIVILEGED_HR_ROLES)


def is_payroll_user(user):
    return bool(user and user.is_authenticated and getattr(user, 'role', None) in PAYROLL_ROLES)


def user_can_access_employee(actor, employee):
    if not actor or not actor.is_authenticated or not employee:
        return False
    if actor.role in ['admin', 'hr']:
        return True
    if actor.role == 'manager':
        return bool(actor.office_id and employee.office_id == actor.office_id)
    return actor.id == employee.id


class IsAdminOnlyPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_admin(request.user)


class IsHRAdminOrReadOnlyManager(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role in ['admin', 'hr']:
            return True
        return user.role == 'manager' and request.method in permissions.SAFE_METHODS


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
