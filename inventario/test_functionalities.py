from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from django.urls import reverse

from users.models import Role, User, UserRole
from .models import AuditEntry, Movement, Product, Warehouse, WarehouseStock
from .services import register_movement


class InventoryFunctionalityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.accounts = {}
        for name, level, warehouses, movements in [
            ('Administrador', 2, True, True), ('Jefe de bodega', 2, False, True),
            ('Operador de bodega', 1, False, True), ('Vendedor', 1, False, False),
            ('Sin rol', 0, False, False),
        ]:
            user = User.objects.create_user(username=name)
            cls.accounts[name] = user
            if level:
                role = Role.objects.create(role_name=name, inventory=level,
                    can_manage_warehouses=warehouses, can_register_movements=movements)
                UserRole.objects.create(user_id=user, role=role)
        cls.product = Product.objects.create(codigo='P001', nombre='Producto')
        cls.warehouse = Warehouse.objects.create(codigo='B01', nombre='Principal')
        cls.other = Warehouse.objects.create(codigo='B02', nombre='Secundaria')
        cls.inactive = Warehouse.objects.create(codigo='B03', nombre='Cerrada', activa=False)

    def login(self, role='Administrador'):
        self.client.force_login(self.accounts[role])

    def movement(self, **overrides):
        data = {'producto': self.product.pk, 'bodega': self.warehouse.pk,
                'tipo': 'entrada', 'cantidad': 10, 'concepto': 'Recepción'}
        data.update(overrides)
        return self.client.post(reverse('inventario:movement_create'), data, REMOTE_ADDR='127.0.0.1')

    def test_ficha_completa_se_guarda_y_consulta(self):
        self.login('Jefe de bodega')
        response = self.client.post(reverse('inventario:product_create'), {
            'codigo': 'ABC123', 'nombre': 'Monitor', 'grupo': 'Equipos', 'subgrupo': 'Pantallas',
            'codigo_barras': '78012345', 'fotografia': 'https://example.com/foto.jpg',
            'ficha_tecnica': '27 pulgadas', 'impuesto': '19', 'nivel_optimo': '12',
        }, REMOTE_ADDR='127.0.0.1')
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(pk='ABC123')
        self.assertEqual(product.subgrupo, 'Pantallas')
        self.assertEqual(product.nivel_optimo, 12)
        self.assertEqual(product.impuesto, 19)
        self.assertEqual(product.stock, 0)
        detail = self.client.get(response.url)
        for text in ('Equipos', 'Pantallas', '78012345', '27 pulgadas', 'Ver fotografía'):
            self.assertContains(detail, text)
        entry = AuditEntry.objects.get(accion='producto_creado')
        self.assertEqual(entry.usuario, self.accounts['Jefe de bodega'])
        self.assertEqual(entry.ip, '127.0.0.1')
        self.assertEqual(entry.nuevo['grupo'], 'Equipos')

    def test_codigos_invalidos_duplicados_y_limite_20(self):
        self.login('Jefe de bodega')
        for code in ('', 'A' * 21, 'A-1', 'A_1', 'A/B', 'P001', 'Ñ01'):
            with self.subTest(code=code):
                self.assertEqual(self.client.post(reverse('inventario:product_create'),
                    {'codigo': code, 'nombre': 'Nuevo'}).status_code, 200)
        self.assertEqual(Product.objects.count(), 1)
        self.assertFalse(AuditEntry.objects.exists())
        self.assertEqual(self.client.post(reverse('inventario:product_create'),
            {'codigo': 'A' * 20, 'nombre': 'Límite'}).status_code, 302)

    def test_codigos_anteriores_con_guiones_se_pueden_seguir_editando(self):
        product = Product.objects.create(codigo='ANT-01', nombre='Anterior')
        self.login('Jefe de bodega')
        self.assertEqual(self.client.post(reverse('inventario:product_edit', args=[product.pk]),
            {'nombre': 'Conservado', 'descripcion': 'Edición'}).status_code, 302)
        entry = AuditEntry.objects.get(accion='producto_editado')
        self.assertEqual(entry.anterior['nombre'], 'Anterior')
        self.assertEqual(entry.nuevo['nombre'], 'Conservado')
        self.assertEqual(entry.nuevo['codigo'], 'ANT-01')

    def test_ficha_rechaza_url_e_impuesto_invalido_y_escapa_texto(self):
        self.login('Jefe de bodega')
        for extra in ({'fotografia': 'javascript:alert(1)'}, {'impuesto': '-1'},
                      {'impuesto': '101'}, {'nivel_optimo': '-1'}, {'subgrupo': 'Sin grupo'}):
            response = self.client.post(reverse('inventario:product_create'),
                {'codigo': 'NUEVO', 'nombre': 'Nombre', **extra})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(Product.objects.filter(pk='NUEVO').exists())
        self.product.nombre = '<script>alert(1)</script>'
        self.product.save()
        response = self.client.get(reverse('inventario:product_detail', args=[self.product.pk]))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>')

    def test_matriz_bodegas_y_movimientos_y_auditoria(self):
        for role in self.accounts:
            self.login(role)
            can_view = role != 'Sin rol'
            can_manage = role == 'Administrador'
            can_move = role in ('Administrador', 'Jefe de bodega', 'Operador de bodega')
            for name, allowed in [('warehouse_list', can_view), ('warehouse_create', can_manage),
                ('movement_list', can_view), ('movement_create', can_move), ('audit_list', can_manage)]:
                with self.subTest(role=role, route=name):
                    self.assertEqual(self.client.get(reverse(f'inventario:{name}')).status_code,
                                     200 if allowed else 403)
            if not can_manage:
                before = list(Warehouse.objects.values())
                self.assertEqual(self.client.post(reverse('inventario:warehouse_create'),
                    {'codigo': 'NUEVA', 'nombre': 'No permitida', 'activa': 'on'}).status_code, 403)
                self.assertEqual(self.client.post(reverse('inventario:warehouse_edit', args=[self.warehouse.pk]),
                    {'codigo': 'B01', 'nombre': 'Manipulada'}).status_code, 403)
                self.assertEqual(list(Warehouse.objects.values()), before)
            if not can_move:
                self.assertEqual(self.movement().status_code, 403)
        self.assertEqual(Movement.objects.count(), 0)
        self.assertTrue(AuditEntry.objects.filter(accion='acceso_denegado').exists())

    def test_visitante_redirigido_y_metodos_seguros(self):
        for name in ('warehouse_list', 'warehouse_create', 'movement_list', 'movement_create', 'audit_list'):
            self.assertEqual(self.client.get(reverse(f'inventario:{name}')).status_code, 302)
        self.login()
        for name in ('warehouse_list', 'movement_list', 'audit_list'):
            self.assertEqual(self.client.post(reverse(f'inventario:{name}')).status_code, 405)
        self.assertEqual(self.client.delete(reverse('inventario:warehouse_edit', args=[self.warehouse.pk])).status_code, 405)

    def test_administrador_crea_edita_desactiva_y_no_acepta_duplicado(self):
        self.login()
        data = {'codigo': 'B04', 'nombre': 'Nueva', 'activa': 'on'}
        self.assertEqual(self.client.post(reverse('inventario:warehouse_create'), data).status_code, 302)
        self.assertEqual(self.client.post(reverse('inventario:warehouse_create'), data).status_code, 200)
        warehouse = Warehouse.objects.get(codigo='B04')
        self.assertEqual(self.client.post(reverse('inventario:warehouse_edit', args=[warehouse.pk]),
                         {'codigo': 'B04', 'nombre': 'Renombrada'}).status_code, 302)
        warehouse.refresh_from_db()
        self.assertFalse(warehouse.activa)
        entry = AuditEntry.objects.get(accion='bodega_desactivada')
        self.assertTrue(entry.anterior['activa'])
        self.assertFalse(entry.nuevo['activa'])
        self.login('Operador de bodega')
        page = self.client.get(reverse('inventario:warehouse_list'))
        self.assertContains(page, 'Principal')
        self.assertNotContains(page, 'Renombrada')

    def test_entradas_salidas_totales_separados_y_detalle(self):
        self.login('Operador de bodega')
        response = self.movement()
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get(response.url), 'Recepción')
        self.assertEqual(self.movement(bodega=self.other.pk, cantidad=4).status_code, 302)
        self.assertEqual(self.movement(tipo='salida', cantidad=3, concepto='Despacho').status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 11)
        self.assertEqual(WarehouseStock.objects.get(producto=self.product, bodega=self.warehouse).cantidad, 7)
        self.assertEqual(WarehouseStock.objects.get(producto=self.product, bodega=self.other).cantidad, 4)
        movement = Movement.objects.first()
        self.assertEqual((movement.stock_anterior, movement.stock_nuevo), (10, 7))
        self.assertEqual(movement.usuario, self.accounts['Operador de bodega'])
        entry = AuditEntry.objects.filter(accion='movimiento_creado').first()
        self.assertEqual(entry.anterior['stock_total'], 14)
        self.assertEqual(entry.nuevo['stock_total'], 11)
        self.assertContains(self.client.get(reverse('inventario:movement_list')), 'Salida')
        self.assertContains(self.client.get(reverse('inventario:movement_detail', args=[movement.pk])), 'Despacho')

    def test_salidas_invalidas_no_crean_historial_ni_alteran_stock(self):
        self.login('Operador de bodega')
        self.movement(cantidad=5)
        for extra in ({'tipo': 'salida', 'cantidad': 6}, {'tipo': 'salida', 'bodega': self.other.pk, 'cantidad': 1},
            {'cantidad': 0}, {'cantidad': -1}, {'cantidad': '1.5'}, {'cantidad': 2147483648},
            {'cantidad': 'texto'}, {'tipo': 'ajuste'}, {'concepto': ''}, {'bodega': self.inactive.pk}):
            with self.subTest(extra=extra):
                before = list(WarehouseStock.objects.values())
                self.assertEqual(self.movement(**extra).status_code, 200)
                self.product.refresh_from_db()
                self.assertEqual(self.product.stock, 5)
                self.assertEqual(list(WarehouseStock.objects.values()), before)
                self.assertEqual(Movement.objects.count(), 1)
                self.assertEqual(AuditEntry.objects.count(), 1)

    def test_desactivar_conserva_stock_e_historial_y_rechaza_movimientos(self):
        self.login()
        self.movement()
        self.client.post(reverse('inventario:warehouse_edit', args=[self.warehouse.pk]),
                         {'codigo': 'B01', 'nombre': 'Principal'})
        self.assertEqual(self.movement().status_code, 200)
        self.assertEqual(Movement.objects.count(), 1)
        self.assertEqual(WarehouseStock.objects.get(bodega=self.warehouse).cantidad, 10)
        self.assertContains(self.client.get(reverse('inventario:movement_detail', args=[Movement.objects.get().pk])), 'inactiva')

    def test_servicio_revalida_bodega_desactivada_despues_de_validar_formulario(self):
        self.inactive.activa = True  # instancia desactualizada como la que podría tener un formulario abierto
        request = SimpleNamespace(user=self.accounts['Operador de bodega'], META={})
        with self.assertRaises(ValidationError):
            register_movement(request, producto=self.product, bodega=self.inactive,
                              tipo='entrada', cantidad=1, concepto='No guardar')
        self.assertFalse(Movement.objects.exists())
        self.assertFalse(WarehouseStock.objects.exists())

    def test_auditoria_fallida_revierte_stock_y_movimiento(self):
        self.login('Operador de bodega')
        with patch('inventario.services.record_audit', side_effect=RuntimeError('fallo de prueba')):
            with self.assertRaises(RuntimeError):
                self.movement()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)
        self.assertFalse(Movement.objects.exists())
        self.assertFalse(WarehouseStock.objects.exists())

    def test_historial_no_se_puede_actualizar_ni_borrar_incluso_con_sql(self):
        self.login('Operador de bodega')
        self.movement()
        for model in (Movement, AuditEntry):
            obj = model.objects.get()
            for action in ('update', 'delete'):
                with self.subTest(model=model, action=action):
                    with self.assertRaises(DatabaseError), transaction.atomic():
                        with connection.cursor() as cursor:
                            table = model._meta.db_table
                            if action == 'update':
                                cursor.execute(f'UPDATE {table} SET id = id WHERE id = %s', [obj.pk])
                            else:
                                cursor.execute(f'DELETE FROM {table} WHERE id = %s', [obj.pk])
            self.assertEqual(model.objects.count(), 1)

    def test_stock_anterior_se_preserva_en_bodega_inicial(self):
        self.product.stock = 8
        self.product.save()
        migration = import_module('inventario.migrations.0003_stock_inicial_y_historial')
        migration.initialize_stock(apps, SimpleNamespace(connection=connection))
        self.assertEqual(WarehouseStock.objects.get(bodega__codigo='INICIAL', producto=self.product).cantidad, 8)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

    def test_revocar_movimientos_se_aplica_a_siguiente_peticion(self):
        self.login('Operador de bodega')
        self.assertEqual(self.client.get(reverse('inventario:movement_create')).status_code, 200)
        Role.objects.filter(pk='Operador de bodega').update(can_register_movements=False)
        self.assertEqual(self.movement().status_code, 403)
        self.assertFalse(Movement.objects.exists())
