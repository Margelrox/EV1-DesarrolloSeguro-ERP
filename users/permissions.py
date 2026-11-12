"""Permisos básicos reutilizando Role y UserRole de la base de Juan."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Role, User, UserRole

DEMO_PREFIX = 'demo_'


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
        'manage_warehouses': any(role.inventory >= 1 and role.can_manage_warehouses for role in roles),
        'register_movements': any(role.inventory >= 1 and role.can_register_movements for role in roles),
    }


def _inventory_access_label(role):
    """Resumen legible de lo que el rol puede hacer en Inventario."""
    if role.inventory <= 0:
        return 'Sin acceso al inventario'
    partes = ['Solo consultar' if role.inventory == 1 else 'Consultar, crear y editar fichas']
    if role.can_change_prices:
        partes.append('cambiar precios')
    if role.can_manage_roles:
        partes.append('asignar roles')
    return ', '.join(partes)


def get_login_role_hints(demo_prefix=DEMO_PREFIX):
    """Roles existentes para la ayuda del login, con las cuentas demo asociadas.

    En un login sin autenticación solo se publican usuarios con el prefijo demo_
    para no permitir la enumeración de cuentas reales.
    """
    demo_users = {}
    asignaciones = (UserRole.objects
                    .filter(user_id__username__startswith=demo_prefix)
                    .values_list('user_id__username', 'role')
                    .order_by('user_id__username'))
    for username, role_name in asignaciones:
        demo_users.setdefault(role_name, []).append(username)

    pistas = [
        {'role': role.role_name,
         'users': demo_users.get(role.role_name, []),
         'access': _inventory_access_label(role)}
        for role in Role.objects.order_by('role_name')
    ]

    con_rol = {username for usuarios in demo_users.values() for username in usuarios}
    sin_rol = list(
        User.objects.filter(username__startswith=demo_prefix)
        .exclude(username__in=con_rol)
        .order_by('username')
        .values_list('username', flat=True)
    )
    if sin_rol:
        pistas.append({'role': 'Sin rol', 'users': sin_rol,
                       'access': 'Sin acceso al inventario'})
    return pistas


def inventory_permission_required(permission):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not get_user_access(request.user).get(permission, False):
                from inventario.services import record_audit
                record_audit(request, 'acceso_denegado', request.path,
                             nuevo={'permiso': permission, 'metodo': request.method})
                raise PermissionDenied('No tienes permiso para realizar esta operación.')
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
