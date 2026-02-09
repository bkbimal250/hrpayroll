from rest_framework import serializers
from .models import SalaryIncrement, SalaryIncrementHistory, Holiday


class SalaryIncrementSerializer(serializers.ModelSerializer):
    """
    Serializer for salary increments.
    Includes extra read-only fields so the frontend can
    filter and display by office, department and other
    employee attributes.
    """

    employee_name = serializers.CharField(
        source='employee.get_full_name',
        read_only=True,
    )
    employee_email = serializers.CharField(
        source='employee.email',
        read_only=True,
    )
    employee_employee_id = serializers.CharField(
        source='employee.employee_id',
        read_only=True,
    )
    # Using SerializerMethodField for safe traversal of optional relationships
    employee_office_name = serializers.SerializerMethodField()
    employee_department_name = serializers.SerializerMethodField()
    employee_designation_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SalaryIncrement
        fields = [
            'id',
            'employee',
            'employee_name',
            'employee_email',
            'employee_employee_id',
            'employee_office_name',
            'employee_department_name',
            'employee_designation_name',
            'increment_type',
            'old_salary',
            'increment_percentage',
            'increment_amount',
            'new_salary',
            'effective_from',
            'reason',
            'status',
            'approved_by',
            'approved_by_name',
            'applied_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = (
            'old_salary',
            'new_salary',
            'applied_at',
            'created_at',
            'updated_at',
        )

    def get_employee_office_name(self, obj):
        try:
            return obj.employee.office.name if obj.employee.office else None
        except AttributeError:
            return None

    def get_employee_department_name(self, obj):
        try:
            return obj.employee.department.name if obj.employee.department else None
        except AttributeError:
            return None

    def get_employee_designation_name(self, obj):
        try:
            return obj.employee.designation.name if obj.employee.designation else None
        except AttributeError:
            return None

    def get_approved_by_name(self, obj):
        try:
            return obj.approved_by.get_full_name() if obj.approved_by else None
        except AttributeError:
            return None

    def create(self, validated_data):
        """
        Auto set old_salary from employee at creation time.
        """
        employee = validated_data['employee']
        validated_data['old_salary'] = getattr(employee, 'salary', 0) or 0
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Prevent editing salary values after approval.
        """
        if instance.status == 'approved':
            raise serializers.ValidationError(
                "Approved increments cannot be modified."
            )
        return super().update(instance, validated_data)


class SalaryIncrementHistorySerializer(serializers.ModelSerializer):
    """
    Read-only serializer for increment history.
    Includes office / department to support reporting.
    """

    employee_name = serializers.CharField(
        source='employee.get_full_name',
        read_only=True,
    )
    employee_office_name = serializers.SerializerMethodField()
    employee_department_name = serializers.SerializerMethodField()

    class Meta:
        model = SalaryIncrementHistory
        fields = [
            'id',
            'employee',
            'employee_name',
            'employee_office_name',
            'employee_department_name',
            'increment',
            'old_salary',
            'new_salary',
            'changed_by',
            'changed_at',
            'remarks',
        ]
        read_only_fields = fields

    def get_employee_office_name(self, obj):
        try:
            return obj.employee.office.name if obj.employee.office else None
        except AttributeError:
            return None

    def get_employee_department_name(self, obj):
        try:
            return obj.employee.department.name if obj.employee.department else None
        except AttributeError:
            return None


class HolidaySerializer(serializers.ModelSerializer):
    """
    Serializer for holidays.
    """

    class Meta:
        model = Holiday
        fields = [
            'id',
            'name',
            'date',
            'type',
            'is_paid',
            'double_pay_if_worked',
            'created_at',
            'updated_at',
        ]
        read_only_fields = (
            'created_at',
            'updated_at',
        )
