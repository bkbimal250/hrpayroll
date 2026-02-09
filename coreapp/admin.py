from django.contrib import admin
from .models import SalaryIncrement, SalaryIncrementHistory
from unfold.admin import ModelAdmin as UnfoldModelAdmin


@admin.register(SalaryIncrement)
class SalaryIncrementAdmin(UnfoldModelAdmin):
    list_display = (
        'employee',
        'increment_type',
        'old_salary',
        'increment_percentage',
        'increment_amount',
        'new_salary',
        'status',
        'effective_from',
        'approved_by',
    )

    list_filter = (
        'status',
        'increment_type',
        'effective_from',
    )

    search_fields = (
        'employee__username',
        'employee__first_name',
        'employee__last_name',
    )

    ordering = ('-effective_from',)

    readonly_fields = (
        'old_salary',
        'increment_amount',
        'new_salary',
        'applied_at',
        'created_at',
        'updated_at',
    )

    fieldsets = (
        ("Employee Info", {
            "fields": ('employee',)
        }),
        ("Increment Details", {
            "fields": (
                'increment_type',
                'increment_percentage',
                'increment_amount',
                'old_salary',
                'new_salary',
                'effective_from',
                'reason',
            )
        }),
        ("Approval", {
            "fields": (
                'status',
                'approved_by',
                'applied_at',
            )
        }),
        ("System Info", {
            "fields": (
                'created_at',
                'updated_at',
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Auto-assign approver when approving from admin
        """
        if obj.status == 'approved' and not obj.approved_by:
            obj.approved_by = request.user
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        """
        Prevent deleting approved increments
        """
        if obj and obj.status == 'approved':
            return False
        return super().has_delete_permission(request, obj)

@admin.register(SalaryIncrementHistory)
class SalaryIncrementHistoryAdmin(UnfoldModelAdmin):
    list_display = (
        'employee',
        'old_salary',
        'new_salary',
        'changed_by',
        'changed_at',
    )

    list_filter = ('changed_at',)

    search_fields = (
        'employee__username',
        'employee__first_name',
        'employee__last_name',
    )

    readonly_fields = (
        'employee',
        'increment',
        'old_salary',
        'new_salary',
        'changed_by',
        'changed_at',
        'remarks',
    )

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.role in ['admin', 'manager']

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.role in ['admin', 'manager']

    def has_delete_permission(self, request, obj=None):
        return False

