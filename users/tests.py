from io import StringIO
from secrets import token_urlsafe
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Role, User, UserRole
from .permissions import get_user_access


class RoleAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='usuario_prueba')
        self.reader = Role.objects.create(role_name='Lectura', inventory=1)
        self.writer = Role.objects.create(role_name='Escritura', inventory=2)

    def test_anonimo_inactivo_y_sin_rol_no_obtienen_acceso(self):
        for user in (AnonymousUser(), self.user):
            access = get_user_access(user)
            self.assertFalse(access['view_products'])
            self.assertFalse(access['manage_roles'])
        UserRole.objects.create(user_id=self.user, role=self.writer)
        self.user.is_active = False
        self.assertFalse(get_user_access(self.user)['edit_products'])

    def test_varios_roles_conservan_nivel_maximo_y_precio_separado(self):
        UserRole.objects.create(user_id=self.user, role=self.reader)
        UserRole.objects.create(user_id=self.user, role=self.writer)
        access = get_user_access(self.user)
        self.assertEqual(access['modules']['inventory'], 2)
        self.assertTrue(access['edit_products'])
        self.assertFalse(access['change_prices'])
        self.writer.can_change_prices = True
        self.writer.save()
        self.assertTrue(get_user_access(self.user)['change_prices'])

    def test_retirar_asignacion_revoca_acceso_en_siguiente_peticion(self):
        assignment = UserRole.objects.create(user_id=self.user, role=self.reader)
        self.client.force_login(self.user)
        url = reverse('inventario:product_list')
        self.assertEqual(self.client.get(url).status_code, 200)
        assignment.delete()
        self.assertEqual(self.client.get(url).status_code, 403)
        dashboard = self.client.get(reverse('inicio:dashboard'))
        self.assertNotContains(dashboard, url)

    def test_preparacion_es_repetible_y_respeta_roles_existentes(self):
        existing = Role.objects.create(role_name='Administrador', inventory=1)
        for _ in range(2):
            call_command('preparar_rbac', stdout=StringIO())
        existing.refresh_from_db()
        self.assertEqual(existing.inventory, 1)
        self.assertFalse(existing.can_change_prices)
        self.assertEqual(Role.objects.filter(role_name='Jefe de bodega').count(), 1)

    def test_usuarios_demo_normales_sin_sobrescribir_cuentas_existentes(self):
        existing = User.objects.create_user(username='demo_jefe', first_name='Conservar')
        # Clave aleatoria de prueba; no se usa en cuentas reales ni se imprime.
        password = token_urlsafe(24)
        with patch('users.management.commands.preparar_rbac.getpass', return_value=password):
            call_command('preparar_rbac', usuarios_demo=True, stdout=StringIO())
        admin = User.objects.get(username='demo_admin')
        self.assertTrue(admin.is_staff)
        self.assertFalse(admin.is_superuser)
        self.assertTrue(get_user_access(admin)['manage_roles'])
        existing.refresh_from_db()
        self.assertEqual(existing.first_name, 'Conservar')
        self.assertFalse(UserRole.objects.filter(user_id=existing).exists())
        self.assertFalse(get_user_access(User.objects.get(username='demo_sin_rol'))['view_products'])


class RoleAdministrationTests(TestCase):
    def setUp(self):
        self.administrator = User.objects.create_user(username='admin_normal', is_staff=True)
        self.role = Role.objects.create(role_name='Administrador', inventory=2,
                                       can_change_prices=True, can_manage_roles=True)
        UserRole.objects.create(user_id=self.administrator, role=self.role)
        self.target = User.objects.create_user(username='destinatario')
        self.target_role = Role.objects.create(role_name='Vendedor', inventory=1)
        self.url = reverse('admin:users_userrole_add')

    def test_administrador_normal_asigna_y_retira_roles_sin_ser_superusuario(self):
        self.client.force_login(self.administrator)
        self.assertEqual(self.client.get(reverse('admin:users_userrole_changelist')).status_code, 200)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        response = self.client.post(self.url, {'user_id': self.target.pk, 'role': self.target_role.pk,
                                               '_save': 'Guardar'})
        self.assertEqual(response.status_code, 302)
        assignment = UserRole.objects.get(user_id=self.target)
        delete_url = reverse('admin:users_userrole_delete', args=[assignment.pk])
        self.assertEqual(self.client.post(delete_url, {'post': 'yes'}).status_code, 302)
        self.assertFalse(UserRole.objects.filter(user_id=self.target).exists())

    def test_staff_sin_permiso_no_puede_autoasignarse_roles(self):
        self.target.is_staff = True
        self.target.save()
        self.client.force_login(self.target)
        count = UserRole.objects.count()
        response = self.client.post(self.url, {'user_id': self.target.pk, 'role': self.role.pk,
                                               'is_superuser': True, '_save': 'Guardar'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(UserRole.objects.count(), count)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_superuser)

    def test_usuario_comun_no_entra_al_admin_ni_se_asigna_roles(self):
        self.client.force_login(self.target)
        response = self.client.post(self.url, {'user_id': self.target.pk, 'role': self.role.pk})
        self.assertEqual(response.status_code, 302)  # Login de Django Admin (no es staff).
        self.assertFalse(UserRole.objects.filter(user_id=self.target).exists())

    def test_administrador_de_roles_no_puede_editar_usuarios_roles_o_grupos(self):
        # Incluso si tiene permisos nativos de Django: la gestión sensible exige superusuario.
        self.administrator.user_permissions.set(Permission.objects.all())
        self.client.force_login(self.administrator)
        group = Group.objects.create(name='Grupo de prueba')
        for url in (
            reverse('admin:users_user_change', args=[self.administrator.pk]),
            reverse('admin:users_role_change', args=[self.role.pk]),
            reverse('admin:auth_group_change', args=[group.pk]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url, {'is_superuser': True}).status_code, 403)
        self.administrator.refresh_from_db()
        self.assertFalse(self.administrator.is_superuser)

    def test_superusuario_puede_preparar_roles_y_usuarios(self):
        superuser = User.objects.create_superuser(username='preparador')
        self.client.force_login(superuser)
        self.assertEqual(self.client.get(reverse('admin:users_user_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:users_role_changelist')).status_code, 200)
