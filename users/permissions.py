"""Permisos básicos reutilizando Role y UserRole de la base de Juan."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import UserRole


def get_user_access(user):
    modules = dict.fromkeys(
        ('customers', 'suppliers', 'materials', 'purchases', 'sales',
         'inventory', 'accounting', 'reporting'), 0
    )
    roles = []
    if user.is_authenticated and user.is_active:
        roles = [assignment.role for assignment in
                 UserRole.objects.filter(user_id=user).select_related('role')]

    for role in roles:
        for module in modules:
            modules[module] = max(modules[module], getattr(role, module))

    return {
        'roles': [role.role_name for role in roles],
        'modules': modules,
        'view_products': modules['inventory'] >= 1,
        'edit_products': modules['inventory'] >= 2,
        'change_prices': any(role.inventory >= 2 and role.can_change_prices for role in roles),
        'manage_roles': any(role.can_manage_roles for role in roles),
    }


def inventory_permission_required(permission):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not get_user_access(request.user).get(permission, False):
                raise PermissionDenied('No tienes permiso para realizar esta operación.')
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
