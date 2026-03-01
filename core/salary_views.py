"""
Salary Management Views
Comprehensive salary management system with auto-calculation from attendance
"""

from rest_framework import status, generics, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Sum, Count, Avg, Max, Min
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from .models import (
    Salary, SalaryTemplate, CustomUser, Office, Department, Designation, Attendance
)
from .serializers import (
    SalarySerializer, SalaryCreateSerializer, SalaryUpdateSerializer,
    SalaryApprovalSerializer, SalaryPaymentSerializer, SalaryTemplateSerializer,
    SalaryTemplateCreateSerializer, SalaryBulkCreateSerializer, SalaryReportSerializer,
    SalarySummarySerializer, SalaryAutoCalculateSerializer
)
from .permissions import IsAdminOrManager, IsAdminOrManagerOrAccountant, IsAdminOrManagerOrEmployee, IsEmployeeSalaryAccess


class SalaryListView(generics.ListCreateAPIView):
    """
    List all salaries or create a new salary
    - GET: List salaries with filtering (Admin/Manager/Accountant can view all, Employee can view their own)
    - POST: Create new salary (Admin/Manager/Accountant only)
    """
    serializer_class = SalarySerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployeeSalaryAccess]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'employee__first_name', 'employee__last_name', 'employee__email',
        'employee__employee_id', 'status', 'salary_month'
    ]
    ordering_fields = ['salary_month', 'created_at', 'status', 'net_salary']
    ordering = ['-salary_month', '-created_at']
    # pagination_class = None  # Use default pagination

    def get_queryset(self):
        """Filter salaries based on user role and permissions"""
        user = self.request.user
        queryset = Salary.objects.select_related(
            'employee', 'employee__office', 'employee__department', 
            'employee__designation', 'approved_by', 'created_by'
        ).all()

        # Role-based filtering
        if user.role == 'admin':
            # Admin can see all salaries
            pass
        elif user.role == 'manager':
            # Manager can see salaries of employees in their office
            if user.office:
                queryset = queryset.filter(employee__office=user.office)
        elif user.role == 'accountant':
            # Accountant can see all salaries
            pass
        elif user.role == 'employee':
            # Employee can only see their own salaries
            queryset = queryset.filter(employee=user)

        # Additional filters
        office_id = self.request.query_params.get('office_id')
        department_id = self.request.query_params.get('department_id')
        status_filter = self.request.query_params.get('status')
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')

        if office_id:
            queryset = queryset.filter(employee__office_id=office_id)
        if department_id:
            queryset = queryset.filter(employee__department_id=department_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if year:
            queryset = queryset.filter(salary_month__year=year)
        if month:
            queryset = queryset.filter(salary_month__month=month)

        return queryset

    def perform_create(self, serializer):
        """Create salary with current user as creator (Admin/Manager/Accountant only)"""
        if self.request.user.role not in ['admin', 'manager', 'accountant']:
            raise PermissionError("Only admin, manager, or accountant can create salary records")
        serializer.save(created_by=self.request.user)


class SalaryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a salary
    - GET: Get salary details (Admin/Manager/Accountant can view all, Employee can view their own)
    - PUT/PATCH: Update salary (Admin/Manager/Accountant only)
    - DELETE: Delete salary (Admin/Manager/Accountant only)
    """
    serializer_class = SalarySerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployeeSalaryAccess]

    def get_queryset(self):
        """Filter salaries based on user role"""
        user = self.request.user
        queryset = Salary.objects.select_related(
            'employee', 'employee__office', 'employee__department',
            'employee__designation', 'approved_by', 'created_by'
        ).all()

        # Role-based filtering
        if user.role == 'admin':
            # Admin can see all salaries
            pass
        elif user.role == 'manager':
            # Manager can see salaries of employees in their office
            if user.office:
                queryset = queryset.filter(employee__office=user.office)
        elif user.role == 'accountant':
            # Accountant can see all salaries
            pass
        elif user.role == 'employee':
            # Employee can only see their own salaries
            queryset = queryset.filter(employee=user)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.request.method in ['PUT', 'PATCH']:
            return SalaryUpdateSerializer
        return SalarySerializer

    def update(self, request, *args, **kwargs):
        """Update salary (Admin/Manager/Accountant only)"""
        if request.user.role not in ['admin', 'manager', 'accountant']:
            return Response(
                {'error': 'Only admin, manager, or accountant can update salary records'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete salary (Admin/Manager/Accountant only)"""
        if request.user.role not in ['admin', 'manager', 'accountant']:
            return Response(
                {'error': 'Only admin, manager, or accountant can delete salary records'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # For managers, ensure they can only delete salaries from their office
        if request.user.role == 'manager':
            salary = self.get_object()
            if not request.user.office or salary.employee.office != request.user.office:
                return Response(
                    {'error': 'Manager can only delete salaries from their own office'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return super().destroy(request, *args, **kwargs)


class SalaryApprovalView(generics.UpdateAPIView):
    """
    Approve or reject salary
    - PUT/PATCH: Approve/reject salary (Admin/Manager only)
    """
    serializer_class = SalaryApprovalSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrManagerOrAccountant]

    def get_queryset(self):
        """Filter salaries for approval"""
        user = self.request.user
        queryset = Salary.objects.select_related('employee', 'employee__office').all()

        if user.role == 'manager' and user.office:
            # Manager can only approve salaries of employees in their office
            queryset = queryset.filter(employee__office=user.office)

        return queryset

    def perform_update(self, serializer):
        """Handle salary status changes (pending, paid, hold)"""
        salary = self.get_object()
        status = serializer.validated_data.get('status')

        # Check permissions - admin, manager, and accountant can change status
        if self.request.user.role not in ['admin', 'manager', 'accountant']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only admin, manager, and accountant can change salary status.')

        # Update status (pending, paid, or hold)
        salary.status = status
        
        # If marking as paid, set paid_date
        if status == 'paid' and not salary.paid_date:
            from django.utils import timezone
            salary.paid_date = timezone.now().date()
            
        salary.save()
        serializer.save()


class SalaryPaymentView(generics.UpdateAPIView):
    """
    Mark salary as paid
    - PUT/PATCH: Mark salary as paid (Admin/Manager/Accountant only)
    """
    serializer_class = SalaryPaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrManagerOrAccountant]

    def get_queryset(self):
        """Filter salaries for payment"""
        user = self.request.user
        # Allow payment for approved salaries, but also allow direct status changes
        queryset = Salary.objects.all()

        if user.role == 'manager' and user.office:
            # Manager can only mark salaries as paid for employees in their office
            queryset = queryset.filter(employee__office=user.office)

        return queryset

    def perform_update(self, serializer):
        """Mark salary as paid"""
        salary = self.get_object()
        paid_date = serializer.validated_data.get('paid_date')
        payment_method = serializer.validated_data.get('payment_method')

        # Update status to paid
        salary.status = 'paid'
        salary.paid_date = paid_date or timezone.now().date()
        
        if payment_method:
            salary.payment_method = payment_method
            
        salary.save()

        serializer.save()


class SalaryBulkCreateView(APIView):
    """
    Bulk create salaries for multiple employees
    - POST: Create salaries for multiple employees (Admin/Manager/Accountant only)
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminOrManagerOrAccountant]

    def post(self, request):
        """Create salaries for multiple employees"""
        serializer = SalaryBulkCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        employee_ids = data['employee_ids']
        salary_month = data['salary_month']
        template_id = data.get('template_id')
        basic_pay = data.get('basic_pay')
        increment = data.get('increment', 0)
        attendance_based = data.get('attendance_based', True)

        created_salaries = []
        errors = []

        for employee_id in employee_ids:
            try:
                employee = CustomUser.objects.get(id=employee_id)
                
                # Check for existing salary for this employee and month
                if Salary.objects.filter(employee=employee, salary_month=salary_month).exists():
                    errors.append(f"Salary already exists for {employee.get_full_name()} for {salary_month.strftime('%B %Y')}")
                    continue

                # Get salary data from template or use provided basic_pay
                if template_id:
                    template = SalaryTemplate.objects.get(id=template_id)
                    if employee.designation.name != template.designation_name or employee.office.name != template.office_name:
                        errors.append(f"Template doesn't match employee {employee.get_full_name()}")
                        continue
                    
                    salary_data = {
                        'employee': employee,
                        'basic_pay': template.basic_pay,
                        'salary_month': salary_month,
                        'attendance_based': attendance_based,
                        'is_auto_calculated': True,
                        'created_by': request.user
                    }
                else:
                    salary_data = {
                        'employee': employee,
                        'basic_pay': basic_pay,
                        'increment': increment,
                        'salary_month': salary_month,
                        'attendance_based': attendance_based,
                        'is_auto_calculated': True,
                        'created_by': request.user
                    }
                
                # Use employee's pay_bank_name if available
                if employee.pay_bank_name:
                    salary_data['Bank_name'] = employee.pay_bank_name

                salary = Salary.objects.create(**salary_data)
                created_salaries.append(SalarySerializer(salary).data)

            except CustomUser.DoesNotExist:
                errors.append(f"Employee with ID {employee_id} not found")
            except SalaryTemplate.DoesNotExist:
                errors.append(f"Template with ID {template_id} not found")
            except Exception as e:
                errors.append(f"Error creating salary for employee {employee_id}: {str(e)}")

        response_data = {
            'created_salaries': created_salaries,
            'total_created': len(created_salaries),
            'errors': errors
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


class SalaryAutoCalculateView(APIView):
    """
    Auto-calculate salaries from attendance data
    - POST: Calculate salaries based on attendance (Admin/Manager/Accountant only)
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminOrManagerOrAccountant]

    def post(self, request):
        """Auto-calculate salaries from attendance"""
        serializer = SalaryAutoCalculateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        salary_month = data['salary_month']
        employee_ids = data.get('employee_ids')
        office_id = data.get('office_id')
        department_id = data.get('department_id')
        template_id = data.get('template_id')
        basic_pay = data.get('basic_pay')

        # Get users to process (all users for admin panel)
        employees = CustomUser.objects.all()
        
        if employee_ids:
            employees = employees.filter(id__in=employee_ids)
        if office_id:
            employees = employees.filter(office_id=office_id)
        if department_id:
            employees = employees.filter(department_id=department_id)

        created_salaries = []
        updated_salaries = []
        errors = []

        for employee in employees:
            try:
                # Check if salary already exists
                salary, created = Salary.objects.get_or_create(
                    employee=employee,
                    salary_month=salary_month,
                    defaults={
                        'created_by': request.user,
                        'attendance_based': True,
                        'is_auto_calculated': True
                    }
                )

                # Set salary data
                if template_id:
                    template = SalaryTemplate.objects.get(id=template_id)
                    if employee.designation.name == template.designation_name and employee.office.name == template.office_name:
                        salary.basic_pay = template.basic_pay
                        # Template fields are already set in salary_data
                else:
                    salary.basic_pay = basic_pay

                # Use employee's pay_bank_name if available and Bank_name is not set
                if employee.pay_bank_name and not salary.Bank_name:
                    salary.Bank_name = employee.pay_bank_name

                # Auto-calculate worked days from attendance
                salary.calculate_worked_days_from_attendance()
                salary.save()

                if created:
                    created_salaries.append(SalarySerializer(salary).data)
                else:
                    updated_salaries.append(SalarySerializer(salary).data)

            except SalaryTemplate.DoesNotExist:
                errors.append(f"Template with ID {template_id} not found for employee {employee.get_full_name()}")
            except Exception as e:
                errors.append(f"Error processing employee {employee.get_full_name()}: {str(e)}")

        response_data = {
            'created_salaries': created_salaries,
            'updated_salaries': updated_salaries,
            'total_created': len(created_salaries),
            'total_updated': len(updated_salaries),
            'errors': errors
        }

        return Response(response_data, status=status.HTTP_200_OK)


class SalaryTemplateListView(generics.ListCreateAPIView):
    """
    List all salary templates or create a new template
    - GET: List templates with filtering
    - POST: Create new template (Admin/Manager/Accountant only)
    """
    serializer_class = SalaryTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrManagerOrAccountant]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'designation_name', 'office_name']
    ordering_fields = ['name', 'created_at', 'basic_pay', 'designation_name', 'office_name']
    ordering = ['designation_name', 'office_name']

    def get_queryset(self):
        """Filter templates based on user role"""
        user = self.request.user
        queryset = SalaryTemplate.objects.select_related(
            'created_by'
        ).filter(is_active=True)

        if user.role == 'manager' and user.office:
            # Manager can only see templates for their office
            queryset = queryset.filter(office_name=user.office.name)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.request.method == 'POST':
            return SalaryTemplateCreateSerializer
        return SalaryTemplateSerializer

    def perform_create(self, serializer):
        """Create template with current user as creator"""
        serializer.save(created_by=self.request.user)


class SalaryTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a salary template
    - GET: Get template details
    - PUT/PATCH: Update template (Admin/Manager/Accountant only)
    - DELETE: Delete template (Admin only)
    """
    serializer_class = SalaryTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrManagerOrAccountant]

    def get_queryset(self):
        """Filter templates based on user role"""
        user = self.request.user
        queryset = SalaryTemplate.objects.select_related(
            'designation', 'office', 'created_by'
        ).all()

        if user.role == 'manager' and user.office:
            # Manager can only see templates for their office
            queryset = queryset.filter(office=user.office)

        return queryset


class SalaryReportView(APIView):
    """
    Generate salary reports
    - GET: Get salary report data (Admin/Manager/Accountant only)
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminOrManagerOrAccountant]

    def get(self, request):
        """Generate salary report"""
        serializer = SalaryReportSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        office_id = data.get('office_id')
        department_id = data.get('department_id')
        year = data['year']
        month = data['month']
        status_filter = data.get('status')

        # Build queryset
        from datetime import date
        used_month = date(year, month, 1)
        queryset = Salary.objects.filter(
            salary_month__year=year,
            salary_month__month=month
        ).select_related('employee', 'employee__office', 'employee__department')

        # Apply filters
        if office_id:
            queryset = queryset.filter(employee__office_id=office_id)
        if department_id:
            queryset = queryset.filter(employee__department_id=department_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Role-based filtering
        user = request.user
        
        # Get all users based on role permissions (not just those with salaries)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if user.role == 'manager' and user.office:
            all_users = User.objects.filter(office=user.office)
            queryset = queryset.filter(employee__office=user.office)
        else:
            all_users = User.objects.all()
        
        # Calculate statistics
        total_salaries = queryset.count()
        total_amount = queryset.aggregate(total=Sum('net_salary'))['total'] or 0
        # Total users (all users, not just those with salaries)
        total_users = all_users.count()
        paid_salaries = queryset.filter(status='paid').count()
        paid_amount = queryset.filter(status='paid').aggregate(total=Sum('net_salary'))['total'] or 0
        pending_salaries = queryset.filter(status='pending').count()
        pending_amount = queryset.filter(status='pending').aggregate(total=Sum('net_salary'))['total'] or 0
        hold_salaries = queryset.filter(status='hold').count()
        hold_amount = queryset.filter(status='hold').aggregate(total=Sum('net_salary'))['total'] or 0

        # Get salary details - include all users, even those without salary records
        salary_details = []
        
        # Create a mapping of employee_id to salary data
        salary_map = {}
        for salary in queryset:
            salary_map[salary.employee.id] = {
                'id': str(salary.id),
                'employee_name': salary.employee.get_full_name(),
                'employee_id': salary.employee.employee_id,
                'office': salary.employee.office.name if salary.employee.office else None,
                'department': salary.employee.department.name if salary.employee.department else None,
                'basic_pay': float(salary.basic_pay),
                'net_salary': float(salary.net_salary),
                'status': salary.status,
                'salary_month': salary.salary_month.strftime('%Y-%m-%d')
            }
        
        # Add all users to the details
        for user in all_users:
            if user.id in salary_map:
                # User has salary record
                salary_details.append(salary_map[user.id])
            else:
                # User has no salary record for this month
                salary_details.append({
                    'id': None,
                    'employee_name': user.get_full_name(),
                    'employee_id': user.employee_id,
                    'office': user.office.name if user.office else None,
                    'department': user.department.name if user.department else None,
                    'basic_pay': 0,
                    'net_salary': 0,
                    'status': 'no_salary',
                    'salary_month': used_month.strftime('%Y-%m-%d')
                })

        report_data = {
            'summary': {
                'total_salaries': total_salaries,
                'total_amount': float(total_amount),
                'paid_salaries': paid_salaries,
                'paid_amount': float(paid_amount),
                'pending_salaries': pending_salaries,
                'pending_amount': float(pending_amount),
                'hold_salaries': hold_salaries,
                'hold_amount': float(hold_amount)
            },
            'details': salary_details,
            'filters': {
                'year': year,
                'month': month,
                'office_id': str(office_id) if office_id else None,
                'department_id': str(department_id) if department_id else None,
                'status': status_filter
            }
        }

        return Response(report_data, status=status.HTTP_200_OK)


class SalarySummaryView(APIView):
    """
    Get salary summary statistics
    - GET: Get salary summary (Admin/Manager/Accountant only)
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminOrManagerOrAccountant]

    def get(self, request):
        """Get salary summary statistics"""
        # Get current month or use provided year/month
        current_date = timezone.now().date()
        current_month = current_date.replace(day=1)
        
        # Allow filtering by year/month if provided
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        
        used_month = current_month
        if year and month:
            try:
                filter_date = current_date.replace(year=int(year), month=int(month), day=1)
                queryset = Salary.objects.filter(salary_month=filter_date)
                used_month = filter_date
            except (ValueError, TypeError):
                queryset = Salary.objects.filter(salary_month=current_month)
                used_month = current_month
        else:
            queryset = Salary.objects.filter(salary_month=current_month)
            used_month = current_month

        # If no data for selected/current month, fallback to latest month with data
        if not queryset.exists():
            latest = Salary.objects.order_by('-salary_month').first()
            if latest:
                used_month = latest.salary_month.replace(day=1)
                queryset = Salary.objects.filter(salary_month=used_month)
        
        # Role-based filtering
        user = request.user
        
        # Get all users based on role permissions (not just those with salaries)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if user.role == 'manager' and user.office:
            all_users = User.objects.filter(office=user.office)
            queryset = queryset.filter(employee__office=user.office)
        else:
            all_users = User.objects.all()

        # Calculate statistics
        total_salaries = queryset.count()
        total_amount = queryset.aggregate(total=Sum('net_salary'))['total'] or 0
        # Total users (all users, not just those with salaries)
        total_users = all_users.count()
        paid_salaries = queryset.filter(status='paid').count()
        paid_amount = queryset.filter(status='paid').aggregate(total=Sum('net_salary'))['total'] or 0
        pending_salaries = queryset.filter(status='pending').count()
        pending_amount = queryset.filter(status='pending').aggregate(total=Sum('net_salary'))['total'] or 0
        hold_salaries = queryset.filter(status='hold').count()
        hold_amount = queryset.filter(status='hold').aggregate(total=Sum('net_salary'))['total'] or 0

        # Calculate averages
        if total_salaries > 0:
            average_salary = total_amount / total_salaries
            highest_salary = queryset.aggregate(max=Max('net_salary'))['max'] or 0
            lowest_salary = queryset.aggregate(min=Min('net_salary'))['min'] or 0
        else:
            average_salary = 0
            highest_salary = 0
            lowest_salary = 0

        summary_data = {
            'total_users': total_users,
            'total_salaries': total_salaries,
            'total_amount': float(total_amount),
            'paid_salaries': paid_salaries,
            'paid_amount': float(paid_amount),
            'pending_salaries': pending_salaries,
            'pending_amount': float(pending_amount),
            'hold_salaries': hold_salaries,
            'hold_amount': float(hold_amount),
            'average_salary': float(average_salary),
            'highest_salary': float(highest_salary),
            'lowest_salary': float(lowest_salary),
            'month': used_month.strftime('%B %Y'),
            'month_ym': used_month.strftime('%Y-%m')
        }

        return Response(summary_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsEmployeeSalaryAccess])
def employee_salary_history(request, employee_id):
    """
    Get salary history for a specific employee
    - GET: Get employee's salary history
    """
    try:
        employee = CustomUser.objects.get(id=employee_id)
        
        # Check permissions
        user = request.user
        
        # Employee can only view their own salary history
        if user.role == 'employee' and employee.id != user.id:
            return Response(
                {'error': 'You can only view your own salary history.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Manager can only view employees in their office
        if user.role == 'manager' and user.office and employee.office != user.office:
            return Response(
                {'error': 'You can only view salary history of employees in your office.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Admin and Accountant can view any employee's salary history

        # Get salary history
        salaries = Salary.objects.filter(employee=employee).order_by('-salary_month')
        
        # Apply filters
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        status_filter = request.query_params.get('status')

        if year:
            salaries = salaries.filter(salary_month__year=year)
        if month:
            salaries = salaries.filter(salary_month__month=month)
        if status_filter:
            salaries = salaries.filter(status=status_filter)

        serializer = SalarySerializer(salaries, many=True, context={'request': request})
        
        return Response({
            'employee': {
                'id': str(employee.id),
                'name': employee.get_full_name(),
                'employee_id': employee.employee_id,
                'office': employee.office.name if employee.office else None,
                'department': employee.department.name if employee.department else None
            },
            'salaries': serializer.data,
            'total_salaries': salaries.count()
        }, status=status.HTTP_200_OK)

    except CustomUser.DoesNotExist:
        return Response(
            {'error': 'Employee not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsAdminOrManagerOrAccountant])
def recalculate_salary(request, salary_id):
    """
    Recalculate salary based on attendance
    - POST: Recalculate salary (Admin/Manager/Accountant only)
    """
    try:
        salary = Salary.objects.get(id=salary_id)
        
        # Check permissions
        user = request.user
        if user.role == 'manager' and user.office and salary.employee.office != user.office:
            return Response(
                {'error': 'You can only recalculate salaries of employees in your office.'},
                status=status.HTTP_403_FORBIDDEN
            )
        # Admin and Accountant can recalculate any salary
        # Manager can recalculate salaries of employees in their office (checked above)

        # Recalculate worked days from attendance
        salary.calculate_worked_days_from_attendance()
        salary.save()

        serializer = SalarySerializer(salary, context={'request': request})
        
        return Response({
            'message': 'Salary recalculated successfully.',
            'salary': serializer.data
        }, status=status.HTTP_200_OK)

    except Salary.DoesNotExist:
        return Response(
            {'error': 'Salary not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdminOrManagerOrAccountant])
def salary_creation_status(request):
    """
    Get employees with their salary creation status for a specific month
    - GET: Returns employees with salary status (created/not created) for the month
    Query Parameters:
        - year: Year (e.g., 2025)
        - month: Month (1-12)
        - office_id: Filter by office (optional)
        - department_id: Filter by department (optional)
    """
    from datetime import date
    
    try:
        # Get query parameters
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        office_id = request.query_params.get('office_id')
        department_id = request.query_params.get('department_id')
        
        # Default to current month if not provided
        if not year or not month:
            current_date = timezone.now().date()
            year = current_date.year
            month = current_date.month
        else:
            try:
                year = int(year)
                month = int(month)
                # Validate month range
                if month < 1 or month > 12:
                    return Response(
                        {'error': 'Invalid month. Month must be between 1 and 12.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid year or month format. Must be integers.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create salary month date (first day of the month) for response
        try:
            salary_month = date(year, month, 1)
        except ValueError as e:
            return Response(
                {'error': f'Invalid date: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all users based on role and filters
        user = request.user
        # For admin and accountant: get all users (all roles) to create salary for everyone
        # For manager: get employees and managers in their office
        if user.role == 'admin' or user.role == 'accountant':
            users = CustomUser.objects.filter(is_active=True)
        elif user.role == 'manager':
            # Manager sees employees and managers in their office
            if user.office:
                users = CustomUser.objects.filter(
                    is_active=True,
                    office=user.office,
                    role__in=['employee', 'manager']
                )
            else:
                # If manager has no office, show nothing
                users = CustomUser.objects.none()
        else:
            # Other roles see only employees
            users = CustomUser.objects.filter(role='employee', is_active=True)
        
        # Role-based filtering (additional filters if needed)
        if user.role == 'admin' or user.role == 'accountant':
            # Admin and accountant can see all users (already handled above)
            pass
        
        # Apply additional filters
        if office_id:
            try:
                users = users.filter(office_id=office_id)
            except (ValueError, ValidationError):
                return Response(
                    {'error': 'Invalid office_id format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        if department_id:
            try:
                users = users.filter(department_id=department_id)
            except (ValueError, ValidationError):
                return Response(
                    {'error': 'Invalid department_id format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get all salaries for the month (filter by year and month, not exact date)
        # This ensures we catch all salaries for November 2025 regardless of which day was used
        # Some salaries might be stored as 2025-11-01, others as 2025-11-30, etc.
        salaries = Salary.objects.filter(
            salary_month__year=year,
            salary_month__month=month
        ).select_related('employee')
        
        # Create a dictionary mapping employee UUID to salary for quick lookup
        # Use employee.id (UUID) as the key to match with employee.id later
        salary_dict = {}
        employees_with_salary_ids = set()
        for salary in salaries:
            # Use the employee's UUID as the key (not employee_id field)
            employee_uuid = str(salary.employee.id)
            salary_dict[employee_uuid] = salary
            employees_with_salary_ids.add(employee_uuid)
        
        # Debug logging (only in DEBUG mode)
        if settings.DEBUG:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Salary creation status - Year: {year}, Month: {month}, Found {len(salaries)} salaries, {len(employees_with_salary_ids)} unique users with salary")
            # Log sample salary months to verify filtering
            if salaries.exists():
                sample_dates = [s.salary_month.strftime('%Y-%m-%d') for s in salaries[:5]]
                logger.info(f"Sample salary_month dates found: {sample_dates}")
        
        # Month details for attendance calculations
        from coreapp.models import Holiday
        import calendar
        
        last_day = calendar.monthrange(year, month)[1]
        start_dt = date(year, month, 1)
        end_dt = date(year, month, last_day)
        
        # 1. Fetch all 'present' attendance counts for the month in one query
        attendance_counts = Attendance.objects.filter(
            date__range=[start_dt, end_dt],
            status='present'
        ).values('user_id').annotate(present_count=Count('id'))
        
        present_map = {str(item['user_id']): item['present_count'] for item in attendance_counts}
        
        # 2. Calculate Sundays in the month
        total_sundays = 0
        curr = start_dt
        while curr <= end_dt:
            if curr.weekday() == 6: # Sunday
                total_sundays += 1
            curr += timedelta(days=1)
            
        # 3. Fetch Holidays (excluding Sundays)
        effective_holidays = Holiday.objects.filter(
            date__range=[start_dt, end_dt]
        ).exclude(date__week_day=1).count() # Django week_day: 1=Sunday, 2=Monday...
        
        # 4. Standard days logic (February vs Others)
        standard_total_days = last_day if month == 2 else 30

        # Build response data
        employees_with_salary_list = []
        employees_without_salary_list = []
        
        # Process all users
        for employee in users.select_related('office', 'department', 'designation').order_by('first_name', 'last_name'):
            employee_id_str = str(employee.id)
            
            # Attendance summary for this employee
            p_days = present_map.get(employee_id_str, 0)
            total_worked = p_days + total_sundays + effective_holidays
            
            employee_data = {
                'id': employee_id_str,
                'employee_id': employee.employee_id or '',
                'first_name': employee.first_name or '',
                'last_name': employee.last_name or '',
                'full_name': employee.get_full_name() or '',
                'email': employee.email or '',
                'office': employee.office.name if employee.office else None,
                'office_id': str(employee.office.id) if employee.office else None,
                'department': employee.department.name if employee.department else None,
                'department_id': str(employee.department.id) if employee.department else None,
                'designation': employee.designation.name if employee.designation else None,
                'salary': float(employee.salary) if employee.salary else 0.0,
                'pay_bank_name': employee.pay_bank_name or '',
                # Attendance summary
                'biometric_days': p_days,
                'total_sundays': total_sundays,
                'holiday_count': effective_holidays,
                'total_working_days': total_worked,
                'standard_total_days': standard_total_days
            }
            
            if employee_id_str in employees_with_salary_ids:
                # Employee has salary for this month
                salary = salary_dict[employee_id_str]
                employee_data['salary_id'] = str(salary.id)
                employee_data['salary_status'] = salary.status
                employee_data['net_salary'] = float(salary.net_salary) if salary.net_salary else 0.0
                # Use stored worked_days if available, otherwise calculated
                employee_data['worked_days'] = float(salary.worked_days)
                employee_data['created_at'] = salary.created_at.isoformat() if salary.created_at else None
                employees_with_salary_list.append(employee_data)
            else:
                # Employee does NOT have salary for this month
                employee_data['salary_id'] = None
                employee_data['salary_status'] = 'not_created'
                employee_data['net_salary'] = 0.0
                employee_data['worked_days'] = total_worked
                employee_data['created_at'] = None
                employees_without_salary_list.append(employee_data)
        
        # Calculate statistics
        total_users = users.count()
        active_users = users.filter(is_active=True).count()  # Should be same as total_users since we filter is_active=True
        employees_with_salary_count = len(employees_with_salary_list)
        employees_without_salary_count = len(employees_without_salary_list)
        
        response_data = {
            'salary_month': salary_month.strftime('%Y-%m-%d'),
            'year': year,
            'month': month,
            'statistics': {
                'total_users': total_users,
                'active_users': active_users,
                'total_employees': total_users,  # Keep for backward compatibility
                'employees_with_salary': employees_with_salary_count,
                'employees_without_salary': employees_without_salary_count,
                'completion_percentage': round((employees_with_salary_count / total_users * 100) if total_users > 0 else 0, 2)
            },
            'employees_with_salary': employees_with_salary_list,
            'employees_without_salary': employees_without_salary_list,  # This is the list of remaining users
            'filters': {
                'office_id': str(office_id) if office_id else None,
                'department_id': str(department_id) if department_id else None
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return Response(
            {
                'error': 'An error occurred while fetching salary creation status.',
                'detail': str(e),
                'trace': error_trace if settings.DEBUG else None
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdminOrManagerOrAccountant])
def salary_statistics(request):
    """
    Get detailed salary statistics
    - GET: Get salary statistics (Admin/Manager/Accountant only)
    """
    # Get current month
    current_date = timezone.now().date()
    current_month = current_date.replace(day=1)

    # Build queryset
    queryset = Salary.objects.filter(salary_month=current_month)
    
    # Role-based filtering
    user = request.user
    if user.role == 'manager' and user.office:
        queryset = queryset.filter(employee__office=user.office)
    # Admin and Accountant can see all statistics

    # Calculate detailed statistics
    stats = {
        'by_status': {},
        'by_office': {},
        'by_department': {},
        'monthly_trends': {}
    }

    # Statistics by status
    for status_choice in Salary.SALARY_STATUS_CHOICES:
        status_value = status_choice[0]
        count = queryset.filter(status=status_value).count()
        amount = queryset.filter(status=status_value).aggregate(total=Sum('net_salary'))['total'] or 0
        stats['by_status'][status_value] = {
            'count': count,
            'amount': float(amount)
        }

    # Statistics by office
    offices = Office.objects.all()
    for office in offices:
        office_salaries = queryset.filter(employee__office=office)
        count = office_salaries.count()
        amount = office_salaries.aggregate(total=Sum('net_salary'))['total'] or 0
        if count > 0:
            stats['by_office'][office.name] = {
                'count': count,
                'amount': float(amount)
            }

    # Statistics by department
    departments = Department.objects.all()
    for department in departments:
        dept_salaries = queryset.filter(employee__department=department)
        count = dept_salaries.count()
        amount = dept_salaries.aggregate(total=Sum('net_salary'))['total'] or 0
        if count > 0:
            stats['by_department'][department.name] = {
                'count': count,
                'amount': float(amount)
            }

    # Monthly trends (last 6 months)
    for i in range(6):
        month_date = current_month - timedelta(days=30 * i)
        month_salaries = Salary.objects.filter(salary_month=month_date)
        
        if user.role == 'manager' and user.office:
            month_salaries = month_salaries.filter(employee__office=user.office)
        # Admin and Accountant can see all monthly trends
        
        count = month_salaries.count()
        amount = month_salaries.aggregate(total=Sum('net_salary'))['total'] or 0
        
        stats['monthly_trends'][month_date.strftime('%Y-%m')] = {
            'count': count,
            'amount': float(amount)
        }

    return Response(stats, status=status.HTTP_200_OK)
