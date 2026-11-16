from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from inventario.forms import (
    WarehouseForm,
    ProductCreateForm,
    ProductPriceForm,
    MovementForm,
)
from inventario.models import Movement


class Command(BaseCommand):
    help = 'Puebla la base de datos principal validando los datos mediante los formularios de la app.'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando carga de datos en la base de datos principal...\n')

        with transaction.atomic():
            usuario_admin = self._obtener_usuario_admin()
            bodegas = self._crear_bodegas()
            productos = self._crear_productos()
            self._asignar_precios(productos)
            self._crear_movimientos(productos, bodegas, usuario_admin)

        self.stdout.write(self.style.SUCCESS('\nCarga de datos completada exitosamente.'))

    def _obtener_usuario_admin(self):
        User = get_user_model()
        usuario, creado = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@ejemplo.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if creado:
            usuario.set_password('1234')
            usuario.save()
            self.stdout.write('  [OK] Superusuario "admin" creado.')
        else:
            self.stdout.write('  [OK] Superusuario "admin" encontrado.')
        return usuario

    def _crear_bodegas(self):
        datos_bodegas = [
            {'codigo': 'BOD01', 'nombre': 'Bodega Central', 'activa': True},
            {'codigo': 'BOD02', 'nombre': 'Bodega Sucursal Norte', 'activa': True},
            {'codigo': 'BOD99', 'nombre': 'Bodega Mantenimiento (Inactiva)', 'activa': False},
        ]
        creadas = {}
        for data in datos_bodegas:
            form = WarehouseForm(data=data)
            if form.is_valid():
                bodega = form.save()
                creadas[bodega.codigo] = bodega
                self.stdout.write(f'  [OK] Bodega creada: {bodega.codigo} - {bodega.nombre}')
            else:
                self.stdout.write(self.style.ERROR(f'  [ERROR] Bodega {data["codigo"]}: {form.errors}'))
        return creadas

    def _crear_productos(self):
        datos_productos = [
            {
                'codigo': 'PROD001',
                'nombre': 'Teclado Mecánico RGB',
                'descripcion': 'Switches lineales, formato TKL',
                'grupo': 'Computación',
                'subgrupo': 'Periféricos',
                'codigo_barras': '7801111111111',
                'fotografia': 'https://ejemplo.com/teclado.jpg',
                'ficha_tecnica': 'Interfaz USB-C desmontable',
                'impuesto': '19.00',
                'nivel_optimo': 15,
            },
            {
                'codigo': 'PROD002',
                'nombre': 'Mouse Inalámbrico Ergónomico',
                'descripcion': 'Sensor óptico 16000 DPI',
                'grupo': 'Computación',
                'subgrupo': 'Periféricos',
                'codigo_barras': '7802222222222',
                'fotografia': 'https://ejemplo.com/mouse.jpg',
                'ficha_tecnica': 'Batería recargable 70h',
                'impuesto': '19.00',
                'nivel_optimo': 20,
            },
            {
                'codigo': 'PROD003',
                'nombre': 'Cable HDMI 2.1 (2m)',
                'descripcion': '',
                'grupo': 'Accesorios',
                'subgrupo': '',
                'codigo_barras': '7803333333333',
                'fotografia': '',
                'impuesto': '',
                'nivel_optimo': '',
            },
        ]
        creados = {}
        for data in datos_productos:
            form = ProductCreateForm(data=data)
            if form.is_valid():
                producto = form.save()
                creados[producto.codigo] = producto
                self.stdout.write(f'  [OK] Producto creado: {producto.codigo} - {producto.nombre}')
            else:
                self.stdout.write(self.style.ERROR(f'  [ERROR] Producto {data["codigo"]}: {form.errors}'))
        return creados

    def _asignar_precios(self, productos):
        precios = {
            'PROD001': '45990.00',
            'PROD002': '29990.00',
            'PROD003': '8500.00',
        }
        for codigo, precio in precios.items():
            producto = productos.get(codigo)
            if not producto:
                continue
            form = ProductPriceForm(data={'precio': precio}, instance=producto)
            if form.is_valid():
                form.save()
                self.stdout.write(f'  [OK] Precio asignado a {codigo}: ${precio}')
            else:
                self.stdout.write(self.style.ERROR(f'  [ERROR] Precio {codigo}: {form.errors}'))

    def _crear_movimientos(self, productos, bodegas, usuario):
        if not productos or not bodegas:
            return

        tipo_field = Movement._meta.get_field('tipo')
        tipo_valido = tipo_field.choices[0][0] if tipo_field.choices else 'IN'

        campos_modelo = {f.name for f in Movement._meta.get_fields()}

        datos_movimientos = [
            {
                'producto': productos['PROD001'].pk,
                'bodega': bodegas['BOD01'].pk,
                'tipo': tipo_valido,
                'cantidad': 30,
                'concepto': 'Compra inicial proveedor',
            },
            {
                'producto': productos['PROD002'].pk,
                'bodega': bodegas['BOD01'].pk,
                'tipo': tipo_valido,
                'cantidad': 50,
                'concepto': 'Abastecimiento bodega central',
            },
            {
                'producto': productos['PROD003'].pk,
                'bodega': bodegas['BOD02'].pk,
                'tipo': tipo_valido,
                'cantidad': 100,
                'concepto': 'Stock inicial sucursal norte',
            },
        ]

        for data in datos_movimientos:
            form = MovementForm(data=data)
            if form.is_valid():
                mov = form.save(commit=False)
                producto = mov.producto

                # Asignación dinámica del campo usuario en Movement
                for nombre_campo_usuario in ('usuario', 'user', 'creado_por'):
                    if nombre_campo_usuario in campos_modelo:
                        setattr(mov, nombre_campo_usuario, usuario)

                # Cálculo de stock_anterior y stock_posterior/stock_nuevo
                stock_actual = getattr(producto, 'stock', 0) or 0
                nuevo_stock = stock_actual + mov.cantidad

                if 'stock_anterior' in campos_modelo:
                    mov.stock_anterior = stock_actual
                if 'stock_posterior' in campos_modelo:
                    mov.stock_posterior = nuevo_stock
                elif 'stock_nuevo' in campos_modelo:
                    mov.stock_nuevo = nuevo_stock

                mov.save()

                if hasattr(producto, 'stock'):
                    producto.stock = nuevo_stock
                    producto.save(update_fields=['stock'])

                self.stdout.write(
                    f'  [OK] Movimiento registrado: {mov.cantidad} un. de {producto.codigo} '
                    f'(Stock: {stock_actual} -> {nuevo_stock})'
                )
            else:
                self.stdout.write(self.style.ERROR(f'  [ERROR] Movimiento: {form.errors}'))