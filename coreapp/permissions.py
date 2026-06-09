from rest_framework.permissions import BasePermission


class IsAdminManagerOrSuperuser(BasePermission):
    """
    Allows access only to superuser, admin, or manager
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return user.role in ['admin', 'manager']


class IsAdminManagerHRNoDeleteOrSuperuser(BasePermission):
    """
    Allows superuser/admin/manager full access and HR create/read/update access.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if request.method == 'DELETE' and user.role == 'hr':
            return False

        return user.role in ['admin', 'manager', 'hr']
