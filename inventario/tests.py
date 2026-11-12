from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from users.models import Role, User, UserRole
from .models import Product


class InventoryRBACTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(codigo='PR-01', nombre='Producto de prueba',
                                             precio=1000, stock=5)
        cls.accounts = {}
        for name, level, prices in (
            ('Administrador', 2, True), ('Jefe de bodega', 2, False),
            ('Operador de bodega', 1, False), ('Vendedor', 1, False),
        ):
            role = Role.objects.create(role_name=name, inventory=level, can_change_prices=prices)
            user = User.objects.create_user(username=f'usuario_{level}_{name}')
            UserRole.objects.create(user_id=user, role=role)
            cls.accounts[name] = user
        cls.accounts['Sin rol'] = User.objects.create_user(username='sin_rol')

    def urls(self):
        return {
            'list': reverse('inventario:product_list'),
            'create': reverse('inventario:product_create'),
            'edit': reverse('inventario:product_edit', args=[self.product.pk]),
            'price': reverse('inventario:product_price', args=[self.product.pk]),
        }

    def test_visitante_exige_login_en_todas_las_rutas(self):
        for url in self.urls().values():
            for method in ('get', 'post'):
                with self.subTest(url=url, method=method):
                    response = getattr(self.client, method)(url)
                    self.assertRedirects(response, f"{reverse('inicio:login')}?next={url}",
                                         fetch_redirect_response=False)

    def test_matriz_get_para_cada_rol_y_botones_coherentes(self):
        expected = {
            'Administrador': (200, 200, 200, 200),
            'Jefe de bodega': (200, 200, 200, 403),
            'Operador de bodega': (200, 403, 403, 403),
            'Vendedor': (200, 403, 403, 403),
            'Sin rol': (403, 403, 403, 403),
        }
        for role, codes in expected.items():
            self.client.force_login(self.accounts[role])
            for (action, url), code in zip(self.urls().items(), codes):
                with self.subTest(role=role, action=action):
                    self.assertEqual(self.client.get(url).status_code, code)
            dashboard = self.client.get(reverse('inicio:dashboard'))
            self.assertEqual(self.urls()['list'] in dashboard.content.decode(), role != 'Sin rol')
            if role != 'Sin rol':
                page = self.client.get(self.urls()['list'])
                self.assertEqual(self.urls()['create'] in page.content.decode(), codes[1] == 200)
                self.assertEqual(self.urls()['price'] in page.content.decode(), codes[3] == 200)

    def test_escrituras_rechazadas_no_modifican_productos(self):
        cases = (
            ('Sin rol', 'create'), ('Sin rol', 'edit'), ('Sin rol', 'price'),
            ('Vendedor', 'create'), ('Vendedor', 'edit'), ('Vendedor', 'price'),
            ('Operador de bodega', 'create'), ('Operador de bodega', 'edit'),
            ('Operador de bodega', 'price'), ('Jefe de bodega', 'price'),
        )
        for role, action in cases:
            self.client.force_login(self.accounts[role])
            before = list(Product.objects.values())
            with self.subTest(role=role, action=action):
                response = self.client.post(self.urls()[action], {
                    'codigo': 'NUEVO', 'nombre': 'Manipulado', 'precio': '1', 'stock': 999,
                })
                self.assertEqual(response.status_code, 403)
                self.assertEqual(list(Product.objects.values()), before)

    def test_jefe_crea_y_edita_sin_modificar_precio_stock_o_codigo(self):
        self.client.force_login(self.accounts['Jefe de bodega'])
        response = self.client.post(self.urls()['create'], {
            'codigo': 'NUEVO', 'nombre': 'Nuevo producto', 'descripcion': 'Ficha', 'stock': 999,
            'role': 'Administrador', 'is_superuser': True,
        })
        self.assertEqual(response.status_code, 302)
        created = Product.objects.get(pk='NUEVO')
        self.assertEqual(created.stock, 0)
        self.assertEqual(created.precio, Decimal('0'))
        response = self.client.post(self.urls()['edit'], {
            'nombre': 'Nombre actualizado', 'descripcion': 'Ficha editada',
            'codigo': 'CODIGO-MANIPULADO', 'stock': 999, 'role': 'Administrador',
        })
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.nombre, 'Nombre actualizado')
        self.assertEqual(self.product.precio, Decimal('1000'))
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(self.product.pk, 'PR-01')
        self.assertFalse(self.accounts['Jefe de bodega'].is_superuser)
        self.assertEqual(UserRole.objects.filter(user_id=self.accounts['Jefe de bodega']).count(), 1)

    def test_precio_no_puede_colarse_por_creacion_o_edicion_general(self):
        self.client.force_login(self.accounts['Jefe de bodega'])
        for action in ('create', 'edit'):
            before = list(Product.objects.values())
            response = self.client.post(self.urls()[action], {
                'codigo': 'NUEVO', 'nombre': 'Manipulado', 'precio': '1',
            })
            self.assertEqual(response.status_code, 403)
            self.assertEqual(list(Product.objects.values()), before)

    def test_administrador_normal_cambia_precio_sin_alterar_otros_campos(self):
        user = self.accounts['Administrador']
        self.assertFalse(user.is_superuser)
        self.client.force_login(user)
        response = self.client.post(self.urls()['price'], {
            'precio': '1500.50', 'nombre': 'Manipulado', 'stock': 999,
        })
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.precio, Decimal('1500.50'))
        self.assertEqual(self.product.nombre, 'Producto de prueba')
        self.assertEqual(self.product.stock, 5)

    def test_retirar_permiso_precio_se_aplica_sin_cerrar_sesion(self):
        user = self.accounts['Administrador']
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.urls()['price']).status_code, 200)
        role = Role.objects.get(pk='Administrador')
        role.can_change_prices = False
        role.save()
        self.assertEqual(self.client.post(self.urls()['price'], {'precio': '10'}).status_code, 403)
        self.product.refresh_from_db()
        self.assertEqual(self.product.precio, Decimal('1000'))
        self.assertNotContains(self.client.get(self.urls()['list']), self.urls()['price'])

    def test_post_con_csrf_valido_es_rechazado_por_rbac_y_admin_puede_guardar(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('inicio:login'))
        csrf_token = client.cookies['csrftoken'].value
        client.force_login(self.accounts['Vendedor'])
        self.assertEqual(client.post(self.urls()['price'], {'precio': '2'},
                                     HTTP_X_CSRFTOKEN=csrf_token).status_code, 403)
        self.product.refresh_from_db()
        self.assertEqual(self.product.precio, Decimal('1000'))
        client.force_login(self.accounts['Administrador'])
        self.assertEqual(client.post(self.urls()['price'], {'precio': '2'},
                                     HTTP_X_CSRFTOKEN=csrf_token).status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.precio, Decimal('2'))

    def test_validacion_basica_de_formularios_y_metodos_http(self):
        self.client.force_login(self.accounts['Administrador'])
        for value in ('-1', 'texto', '9999999999999999999'):
            self.assertEqual(self.client.post(self.urls()['price'], {'precio': value}).status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.precio, Decimal('1000'))
        self.assertEqual(self.client.post(self.urls()['create'], {'codigo': '', 'nombre': ''}).status_code, 200)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(self.client.post(self.urls()['list']).status_code, 405)
        self.assertEqual(self.client.delete(self.urls()['edit']).status_code, 405)
        self.assertEqual(self.client.get(reverse('inventario:product_edit', args=['NO-EXISTE'])).status_code, 404)
