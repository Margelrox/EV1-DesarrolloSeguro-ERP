from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class DashboardSummaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from inventario.models import Product, Warehouse
        from users.models import Role, UserRole
        cls.viewer = get_user_model().objects.create_user(username='consulta_dashboard')
        role = Role.objects.create(role_name='Consulta', inventory=1)
        UserRole.objects.create(user_id=cls.viewer, role=role)
        cls.no_role = get_user_model().objects.create_user(username='dashboard_sin_rol')
        Product.objects.create(codigo='P01', nombre='Producto visible', stock=3, nivel_optimo=5)
        Product.objects.create(codigo='P02', nombre='Otro producto', stock=7, nivel_optimo=0)
        Warehouse.objects.create(codigo='B01', nombre='Activa')
        Warehouse.objects.create(codigo='B02', nombre='Inactiva', activa=False)

    def test_resumen_usa_datos_reales_y_bodegas_activas(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse('inicio:dashboard'))
        self.assertEqual(response.context['summary'], {
            'products': 2, 'warehouses': 1, 'units': 10, 'low_stock': 1,
        })
        self.assertContains(response, 'Aún no hay movimientos')
        self.assertNotContains(response, reverse('inventario:movement_create'))
        self.assertNotContains(response, reverse('inventario:warehouse_create'))
        self.assertNotContains(response, reverse('inventario:audit_list'))

    def test_sin_rol_no_expone_datos_de_inventario(self):
        self.client.force_login(self.no_role)
        response = self.client.get(reverse('inicio:dashboard'))
        self.assertNotIn('summary', response.context)
        self.assertNotIn('recent_movements', response.context)
        self.assertNotContains(response, 'Producto visible')
        self.assertNotContains(response, reverse('inventario:product_list'))
        self.assertContains(response, 'Tu cuenta no tiene acceso a Inventario.')

    def test_revocacion_de_rol_oculta_datos_y_navegacion(self):
        from users.models import UserRole
        self.client.force_login(self.viewer)
        self.assertContains(self.client.get(reverse('inicio:dashboard')), 'Unidades en stock')
        UserRole.objects.filter(user_id=self.viewer).delete()
        response = self.client.get(reverse('inicio:dashboard'))
        self.assertNotContains(response, 'Unidades en stock')
        self.assertNotContains(response, reverse('inventario:movement_list'))
