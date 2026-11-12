from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group

from .models import Role, User, UserRole
from .permissions import get_user_access


class SuperuserOnlyMixin:
    # Evita que un administrador de roles se otorgue is_superuser o cambie la matriz.
    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)


@admin.register(User)
class CustomerAdmin(SuperuserOnlyMixin, UserAdmin):
    list_display = ('user_id', 'username')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')


@admin.register(Role)
class RoleAdmin(SuperuserOnlyMixin, admin.ModelAdmin):
    list_display = ('role_name', 'inventory', 'can_change_prices', 'can_manage_roles',
                    'can_manage_warehouses', 'can_register_movements')
    list_filter = ('inventory', 'can_change_prices', 'can_manage_roles')
    search_fields = ('role_name',)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'role')
    list_filter = ('role',)
    search_fields = ('user_id__username', 'role__role_name')

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_staff and (
            request.user.is_superuser or get_user_access(request.user)['manage_roles']
        )

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)


# Los permisos nativos de Group no deben abrir una segunda vía de escalada.
admin.site.unregister(Group)


@admin.register(Group)
class RestrictedGroupAdmin(SuperuserOnlyMixin, GroupAdmin):
    pass
