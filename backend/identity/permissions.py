from rest_framework.permissions import BasePermission
from rest_framework.exceptions import NotAuthenticated

from .rbac import has_permission


class HasAegisPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise NotAuthenticated()
        get_required_permission = getattr(
            view,
            "get_required_aegis_permission",
            None,
        )
        permission_code = (
            get_required_permission(request)
            if callable(get_required_permission)
            else getattr(view, "required_aegis_permission", None)
        )
        return bool(
            permission_code
            and has_permission(request.user, permission_code)
        )
