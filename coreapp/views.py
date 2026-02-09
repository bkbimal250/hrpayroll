from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import SalaryIncrement, SalaryIncrementHistory, Holiday
from .serializers import (
    SalaryIncrementSerializer,
    SalaryIncrementHistorySerializer,
    HolidaySerializer,  
)
from .permissions import IsAdminManagerOrSuperuser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .filters import SalaryIncrementFilter, SalaryIncrementHistoryFilter, HolidayFilter


class SalaryIncrementViewSet(viewsets.ModelViewSet):
    """
    Create / Update / Approve Salary Increments.

    Supports filtering by:
    - office_id: UUID of employee.office
    - department_id: UUID of employee.department
    - employee_id: UUID of employee
    - status: pending / approved / rejected
    - increment_type: annual / promotion / performance / adjustment / other
    - effective_from (exact), from_date, to_date (date range on effective_from)
    """

    queryset = SalaryIncrement.objects.select_related(
        'employee',
        'approved_by',
        'employee__office',
        'employee__department',
        'employee__designation',
    )
    serializer_class = SalaryIncrementSerializer
    permission_classes = [IsAuthenticated, IsAdminManagerOrSuperuser]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SalaryIncrementFilter
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email', 'reason']
    ordering_fields = ['effective_from', 'created_at', 'increment_amount']

    def get_queryset(self):
        return super().get_queryset()

    def perform_create(self, serializer):
        """
        When an admin/manager creates an increment, approve it
        immediately so the base salary is updated right away
        via the salary increment signal.
        """
        increment = serializer.save()

        user = self.request.user

        # Auto-approve only for admin/manager/superuser
        if user.is_superuser or getattr(user, 'role', None) in ['admin', 'manager']:
            if increment.status != 'approved':
                increment.status = 'approved'
                increment.approved_by = user
                # Saving with status=approved will trigger the post_save
                # signal in coreapp.signals to update the base salary
                # and create history, and mark applied_at.
                increment.save()

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Explicit approval endpoint (kept for compatibility),
        will also immediately update the base salary via signal.
        """
        increment = self.get_object()

        if increment.status == 'approved':
            return Response(
                {"detail": "Increment already approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        increment.status = 'approved'
        increment.approved_by = request.user
        increment.save()

        return Response(
            {"detail": "Increment approved successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject increment.
        """
        increment = self.get_object()

        if increment.status == 'approved':
            return Response(
                {"detail": "Approved increment cannot be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        increment.status = 'rejected'
        increment.save()

        return Response(
            {"detail": "Increment rejected."},
            status=status.HTTP_200_OK,
        )


class SalaryIncrementHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only salary increment history.

    Supports filtering by:
    - office_id: UUID of employee.office
    - department_id: UUID of employee.department
    - employee_id: UUID of employee
    - from_date / to_date: date range on changed_at
    """

    queryset = SalaryIncrementHistory.objects.select_related(
        'employee',
        'increment',
        'employee__office',
        'employee__department',
    )
    serializer_class = SalaryIncrementHistorySerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SalaryIncrementHistoryFilter
    search_fields = ['employee__first_name', 'employee__last_name', 'remarks']
    ordering_fields = ['changed_at']

    def get_queryset(self):
        return super().get_queryset()


class HolidayViewSet(viewsets.ModelViewSet):
    """
    Create / Update / Delete holidays.
    """

    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = HolidayFilter
    search_fields = ['name']
    ordering_fields = ['date', 'name']
    
    def get_permissions(self):
        """
        Allow all authenticated users to view holidays.
        Only Admins/Managers/Superusers can create/update/delete.
        """
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminManagerOrSuperuser()]

    def get_queryset(self):
        return super().get_queryset()
