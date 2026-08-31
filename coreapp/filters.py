from django_filters import rest_framework as django_filters
from .models import SalaryIncrement, SalaryIncrementHistory, Holiday, HappyBirthday

class SalaryIncrementFilter(django_filters.FilterSet):
    office_id = django_filters.CharFilter(field_name='employee__office__id')
    department_id = django_filters.CharFilter(field_name='employee__department__id')
    employee_id = django_filters.CharFilter(field_name='employee__id')
    status = django_filters.CharFilter(field_name='status')
    increment_type = django_filters.CharFilter(field_name='increment_type')
    effective_from = django_filters.DateFilter(field_name='effective_from')
    from_date = django_filters.DateFilter(field_name='effective_from', lookup_expr='gte')
    to_date = django_filters.DateFilter(field_name='effective_from', lookup_expr='lte')

    class Meta:
        model = SalaryIncrement
        fields = ['status', 'increment_type', 'effective_from']

class SalaryIncrementHistoryFilter(django_filters.FilterSet):
    office_id = django_filters.CharFilter(field_name='employee__office__id')
    department_id = django_filters.CharFilter(field_name='employee__department__id')
    employee_id = django_filters.CharFilter(field_name='employee__id')
    from_date = django_filters.DateFilter(field_name='changed_at', lookup_expr='date__gte')
    to_date = django_filters.DateFilter(field_name='changed_at', lookup_expr='date__lte')

    class Meta:
        model = SalaryIncrementHistory
        fields = []

class HolidayFilter(django_filters.FilterSet):
    type = django_filters.CharFilter(field_name='type')
    from_date = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    to_date = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    is_paid = django_filters.BooleanFilter(field_name='is_paid')

    class Meta:
        model = Holiday
        fields = ['type', 'is_paid']


class HappyBirthdayFilter(django_filters.FilterSet):
    office_id = django_filters.CharFilter(field_name='employee__office__id')
    department_id = django_filters.CharFilter(field_name='employee__department__id')
    employee_id = django_filters.CharFilter(field_name='employee__id')
    month = django_filters.NumberFilter(field_name='birthday_date', lookup_expr='month')

    class Meta:
        model = HappyBirthday
        fields = ['office_id', 'department_id', 'employee_id', 'month']
